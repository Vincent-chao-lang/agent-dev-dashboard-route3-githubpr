from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

from .config import ROLE_ALLOWED_PREFIXES
from .git_ops import write_file
from .utils import within_prefix, now_iso
from .text_blocks import upsert_block
from .llm_client import get_llm_client, LLMMessage
from .llm_config import get_effective_config
from .adse import get_quadrants, generate_meta_prompt, save_meta_prompt, ADSEQuadrants

class AgentSafetyError(RuntimeError):
    pass

def _assert_allowed(role: str, rel_paths: Iterable[str]) -> None:
    allowed = ROLE_ALLOWED_PREFIXES.get(role)
    if not allowed:
        raise AgentSafetyError(f"Unknown role: {role}")
    for rp in rel_paths:
        if not within_prefix(rp, allowed):
            raise AgentSafetyError(f"Role '{role}' is not allowed to write: {rp}")


def _get_agent_prompt(
    slice_obj: dict[str, Any],
    role: str,
    ac_list: list[dict[str, Any]],
    user_id: Optional[int] = None,
    project_id: Optional[int] = None,
) -> tuple[str, str]:
    """
    Get the appropriate prompt for an agent based on whether ADSE is enabled.

    Args:
        slice_obj: Slice dictionary
        role: Agent role (pm, architect, dev, qa, ops)
        ac_list: List of acceptance criteria
        user_id: User ID for LLM config
        project_id: Project ID for LLM config

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    # Check if ADSE is enabled for this slice
    adse_enabled = slice_obj.get("adse_enabled", 0)

    if adse_enabled:
        # Get ADSE quadrants
        quadrants = get_quadrants(slice_obj["id"])

        if quadrants and not quadrants.is_empty():
            # Generate ADSE-enhanced meta-prompt
            meta_prompt = generate_meta_prompt(slice_obj, quadrants, role)

            # Save meta-prompt for tracking
            try:
                save_meta_prompt(slice_obj["id"], role, meta_prompt)
            except Exception:
                pass  # Don't fail if we can't save the meta-prompt

            # Return the meta-prompt as user prompt
            system_prompt = _get_adse_system_prompt(role)
            return system_prompt, meta_prompt

    # Fall back to standard prompt
    return _get_standard_prompt(slice_obj, role, ac_list)


def _get_adse_system_prompt(role: str) -> str:
    """Get the system prompt for ADSE-enhanced mode."""
    base_prompt = "你是 ADSE 增强模式下的 AI 助手。你必须严格遵守四象限需求中定义的所有规则，特别是语义契约部分。"
    role_prompts = {
        "pm": "你是一位资深产品经理。基于 ADSE 四象限需求，生成完整的产品需求文档（PRD）。确保功能核心、物理约束、语义契约、异常处理都被完整覆盖。",
        "architect": "你是一位资深架构师。基于 ADSE 四象限需求，生成技术架构设计文档。架构设计必须满足物理约束，必须通过架构设计来保证语义契约中的规则。",
        "dev": "你是一位资深开发工程师。基于 ADSE 四象限需求，生成实现代码。必须严格遵守语义契约中的所有规则，代码结构必须符合物理约束要求。",
        "qa": "你是一位资深测试工程师。基于 ADSE 四象限需求，生成测试用例。测试用例必须覆盖语义契约中提到的所有规则验证，以及异常与边缘情况。",
        "ops": "你是一位资深运维工程师。基于 ADSE 四象限需求，生成运维文档。部署文档必须符合物理约束，监控方案必须覆盖关键指标。",
    }
    return base_prompt + "\n\n" + role_prompts.get(role, "")


def _get_standard_prompt(
    slice_obj: dict[str, Any],
    role: str,
    ac_list: list[dict[str, Any]],
) -> tuple[str, str]:
    """Get the standard prompt for non-ADSE mode."""
    ac_text = "\n".join([f"- {a['code']}: {a['text']}" for a in ac_list])

    if role == "pm":
        system_prompt = "你是一位经验丰富的产品经理，擅长编写清晰、完整的产品需求文档。你的输出应该结构化、专业且易于理解。"
        user_prompt = f"""你是一位资深产品经理。请为以下 Slice 生成完整的产品需求文档（PRD）。

Slice 信息：
- ID: {slice_obj['id']}
- 标题: {slice_obj['title']}
- 范围: {slice_obj['scope']}
- 不包含范围: {slice_obj['out_of_scope']}

验收标准：
{ac_text}

请生成包含以下内容的 PRD（使用 Markdown 格式）：

## Slice {slice_obj['id']}: {slice_obj['title']}

### 背景与目标
- 背景：（说明为什么要做这个功能）
- 目标：（明确的功能目标）

### 用户故事
- US-001 作为 <角色>，我希望 <能力>，以便 <收益>
- （根据验收标准生成 2-5 个用户故事）

### 业务规则 / 边界条件
- 规则：（列出业务规则）
- 边界：（说明功能的边界）
- 异常流程（含错误码期望）：

### 非功能性需求
- 性能要求
- 安全要求
- 可用性要求

请确保内容专业、完整、可执行。"""
    else:
        # For other roles, return empty prompts to be handled by existing code
        system_prompt = ""
        user_prompt = ""

    return system_prompt, user_prompt

@dataclass
class AgentOutput:
    changed_files: list[str]
    summary: str

def run_pm(
    worktree: Path,
    slice_obj: dict[str, Any],
    ac_list: list[dict[str, Any]],
    user_id: Optional[int] = None,
    project_id: Optional[int] = None,
) -> AgentOutput:
    prd_path = "docs/PRD.md"
    acc_path = "docs/ACCEPTANCE.md"
    task_path = f"tasks/{slice_obj['id']:04d}-{slice_obj['branch_name'].replace('/', '_')}.md"
    _assert_allowed("pm", [prd_path, acc_path, task_path])

    start = f"<!-- slice:{slice_obj['id']}:start -->"
    end = f"<!-- slice:{slice_obj['id']}:end -->"

    # Get LLM client with hierarchical config
    llm = get_llm_client(user_id=user_id, project_id=project_id)

    # Get appropriate prompt based on ADSE mode
    system_prompt, user_prompt = _get_agent_prompt(slice_obj, "pm", ac_list, user_id, project_id)

    # If we didn't get a custom prompt, fall back to the old way
    if not user_prompt:
        ac_text = "\n".join([f"- {a['code']}: {a['text']}" for a in ac_list])
        system_prompt = "你是一位经验丰富的产品经理，擅长编写清晰、完整的产品需求文档。你的输出应该结构化、专业且易于理解。"
        user_prompt = f"""你是一位资深产品经理。请为以下 Slice 生成完整的产品需求文档（PRD）。

Slice 信息：
- ID: {slice_obj['id']}
- 标题: {slice_obj['title']}
- 范围: {slice_obj['scope']}
- 不包含范围: {slice_obj['out_of_scope']}

验收标准：
{ac_text}

请生成包含以下内容的 PRD（使用 Markdown 格式）：

## Slice {slice_obj['id']}: {slice_obj['title']}

### 背景与目标
- 背景：（说明为什么要做这个功能）
- 目标：（明确的功能目标）

### 用户故事
- US-001 作为 <角色>，我希望 <能力>，以便 <收益>
- （根据验收标准生成 2-5 个用户故事）

### 业务规则 / 边界条件
- 规则：（列出业务规则）
- 边界：（说明功能的边界）
- 异常流程（含错误码期望）：

### 非功能性需求
- 性能要求
- 安全要求
- 可用性要求

请确保内容专业、完整、可执行。"""

    prd_response = llm.chat_simple(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=4096,
    )

    if prd_response.error:
        # Fallback to template if LLM fails
        prd_block = f"""## Slice {slice_obj['id']}: {slice_obj['title']}

### 背景与目标
- 背景：
- 目标：

### 用户故事
- US-001 作为 <角色>，我希望 <能力>，以便 <收益>

### 业务规则 / 边界条件
- 规则：
- 边界：
- 异常流程（含错误码期望）：

[LLM Error: {prd_response.error}]
"""
    else:
        prd_block = prd_response.content

    upsert_block(worktree / prd_path, start, end, prd_block)

    # 生成验收标准文档
    acc_prompt = f"""你是一位资深产品经理。请为以下 Slice 生成验收标准文档。

Slice 信息：
- ID: {slice_obj['id']}
- 标题: {slice_obj['title']}

验收标准：
{ac_text}

请为每个验收标准生成详细的验收条件和验证方式。格式如下：

## Slice {slice_obj['id']}: {slice_obj['title']}

### AC001 标题
- 验收：
  - (可验证的验收条件)
  - (可验证的验收条件)
- 验证方式：
  - (测试步骤或验证方法)

请确保验收条件具体、可测量、可验证。"""

    acc_response = llm.chat_simple(
        system_prompt="你是一位质量专家，擅长制定清晰、可验证的验收标准。",
        user_prompt=acc_prompt,
        max_tokens=4096,
    )

    if acc_response.error:
        # Fallback to template if LLM fails
        acc_items = []
        for a in ac_list:
            acc_items.append(
                f"""### {a['code']} {a['text']}
- 验收：
  - (填写可验证条件)
- 验证方式：
  - {a['verification']}
"""
            )
        acc_block = f"""## Slice {slice_obj['id']}: {slice_obj['title']}
""" + "\n".join(acc_items)
    else:
        acc_block = acc_response.content

    upsert_block(worktree / acc_path, start, end, acc_block)

    # 生成任务卡片
    task = f"""# Slice: {slice_obj['title']}
Branch: `{slice_obj['branch_name']}`

## AC
""" + "\n".join([f"- {a['code']}: {a['text']}" for a in ac_list]) + f"""

## Scope
{slice_obj['scope']}

## Out of scope
{slice_obj['out_of_scope']}

Generated at {now_iso()}
"""
    write_file(worktree, task_path, task)
    return AgentOutput([prd_path, acc_path, task_path], "Generated PRD, AC docs and task card using GLM-4.7.")

def run_architect(
    worktree: Path,
    slice_obj: dict[str, Any],
    ac_list: list[dict[str, Any]],
    user_id: Optional[int] = None,
    project_id: Optional[int] = None,
) -> AgentOutput:
    design_path = "docs/DESIGN.md"
    test_path = "docs/TEST_STRATEGY.md"
    openapi_path = "contracts/openapi.yaml"
    adr_path = f"docs/adr/ADR-{slice_obj['id']:04d}-slice.md"
    _assert_allowed("architect", [design_path, test_path, openapi_path, adr_path])

    start = f"<!-- slice:{slice_obj['id']}:start -->"
    end = f"<!-- slice:{slice_obj['id']}:end -->"

    llm = get_llm_client(user_id=user_id, project_id=project_id)
    ac_text = "\n".join([f"- {a['code']}: {a['text']}" for a in ac_list])

    # 生成设计文档
    design_prompt = f"""你是一位资深架构师。请为以下 Slice 生成详细的技术设计文档。

Slice 信息：
- ID: {slice_obj['id']}
- 标题: {slice_obj['title']}
- 范围: {slice_obj['scope']}
- 风险级别: {slice_obj['risk_level']}

验收标准：
{ac_text}

请生成包含以下内容的设计文档：

## Slice {slice_obj['id']}: {slice_obj['title']}

### 系统架构
- 整体架构设计
- 模块划分

### API 契约
- RESTful API 设计
- 请求/响应格式
- 错误码定义

### 数据模型
- 数据库设计
- 缓存策略

### 并发协作策略
- 每 slice 一条分支
- 每次运行一个 worktree（隔离 checkout）

### 幂等/超时/重试/限流
- 接口幂等性设计
- 超时处理
- 重试策略
- 限流方案

### 安全设计
- 认证授权
- 数据加密
- SQL/XSS 防护

### 可观测性
- 日志规范
- 监控指标
- 告警规则

请确保设计专业、完整、可落地。"""

    design_response = llm.chat_simple(
        system_prompt="你是一位经验丰富的架构师，擅长设计高可用、高性能、可扩展的系统。你的设计应该清晰、专业且易于实现。",
        user_prompt=design_prompt,
        max_tokens=4096,
    )

    if design_response.error:
        design_block = f"""## Slice {slice_obj['id']}: {slice_obj['title']}

### API 契约
- contracts/openapi.yaml

### 并发协作策略
- 每 slice 一条分支
- 每次运行一个 worktree（隔离 checkout）

### 幂等/超时/重试/限流
- (填)

### 可观测性
- (填)

[LLM Error: {design_response.error}]
"""
    else:
        design_block = design_response.content

    upsert_block(worktree / design_path, start, end, design_block)

    # 生成测试策略
    test_prompt = f"""你是一位资深测试架构师。请为以下 Slice 生成测试策略文档。

Slice 信息：
- ID: {slice_obj['id']}
- 标题: {slice_obj['title']}
- 风险级别: {slice_obj['risk_level']}

验收标准：
{ac_text}

请生成测试策略，包括：

## Slice {slice_obj['id']}: {slice_obj['title']}

### 测试金字塔
- 单元测试：核心路径 + 边界条件
- 集成测试：模块间交互
- 端到端测试：关键业务流程

### 测试工具
- 单元测试框架
- API 测试工具
- 性能测试工具

### 测试命令
```bash
make lint    # 代码规范检查
make type     # 类型检查
make contract # 契约测试
make test     # 运行所有测试
```

### 覆盖率要求
- 代码覆盖率目标
- 关键路径覆盖率

请确保测试策略全面、可执行。"""

    test_response = llm.chat_simple(
        system_prompt="你是一位经验丰富的测试专家，擅长设计全面的测试策略和质量保障体系。",
        user_prompt=test_prompt,
        max_tokens=4096,
    )

    if test_response.error:
        test_block = f"""## Slice {slice_obj['id']}: {slice_obj['title']}
- 单测：核心路径 + 错误分支
- 合同测试：openapi.yaml 对齐
- 集成测：必要时 docker compose

命令：
- make lint
- make type
- make contract
- make test

[LLM Error: {test_response.error}]
"""
    else:
        test_block = test_response.content

    upsert_block(worktree / test_path, start, end, test_block)

    created = []
    if not (worktree / openapi_path).exists():
        # 生成 OpenAPI 契约
        openapi_prompt = f"""你是一位 API 设计专家。请为以下 Slice 生成 OpenAPI 3.0 规范。

Slice 信息：
- ID: {slice_obj['id']}
- 标题: {slice_obj['title']}
- 范围: {slice_obj['scope']}

验收标准：
{ac_text}

请生成完整的 OpenAPI 3.0 YAML 规范，包括：
- API 信息
- 所有端点（GET, POST, PUT, DELETE）
- 请求/响应 schema
- 错误响应定义

直接输出 YAML 内容，不要包含 markdown 代码块标记。"""

        openapi_response = llm.chat_simple(
            system_prompt="你是一位 API 设计专家，精通 OpenAPI 3.0 规范。输出应该是纯 YAML 格式，不要包含任何解释文字。",
            user_prompt=openapi_prompt,
            max_tokens=4096,
        )

        if openapi_response.error:
            openapi = """openapi: 3.0.3
info:
  title: Backend Service
  version: 0.1.0
paths:
  /health:
    get:
      summary: Health check
      responses:
        "200":
          description: OK

[LLM Error: {openapi_response.error}]
"""
        else:
            # Remove markdown code block if present
            content = openapi_response.content
            if content.startswith("```yaml"):
                content = content.split("```yaml")[1].split("```")[0].strip()
            elif content.startswith("```"):
                content = content.split("```")[1].split("```")[0].strip()
            openapi = content

        write_file(worktree, openapi_path, openapi)
        created.append(openapi_path)

    # 生成 ADR
    adr = f"""# ADR-{slice_obj['id']:04d}: Slice Design Notes
- Branch: {slice_obj['branch_name']}
- Decision: Contract-first + per-slice branch + worktree isolation
- Generated at: {now_iso()}
"""
    write_file(worktree, adr_path, adr)
    return AgentOutput([design_path, test_path, adr_path] + created, "Generated design, test strategy, ADR and OpenAPI using GLM-4.7.")

def run_dev(
    worktree: Path,
    slice_obj: dict[str, Any],
    ac_list: list[dict[str, Any]],
    user_id: Optional[int] = None,
    project_id: Optional[int] = None,
) -> AgentOutput:
    p = "reports/dev_report.md"
    _assert_allowed("dev", [p])

    llm = get_llm_client(user_id=user_id, project_id=project_id)
    ac_text = "\n".join([f"- [ ] {a['code']}: {a['text']}" for a in ac_list])

    dev_prompt = f"""你是一位资深开发工程师。请为以下 Slice 生成开发报告和实施计划。

Slice 信息：
- ID: {slice_obj['id']}
- 标题: {slice_obj['title']}
- 分支: {slice_obj['branch_name']}
- 范围: {slice_obj['scope']}
- 风险级别: {slice_obj['risk_level']}

验收标准：
{ac_text}

请生成包含以下内容的开发报告：

# 开发报告

## Slice 概述
- ID: {slice_obj['id']}
- 标题: {slice_obj['title']}
- 分支: {slice_obj['branch_name']}
- 风险级别: {slice_obj['risk_level']}

## 验收标准清单
{ac_text}

## 实施计划
### 1. 技术栈选择
### 2. 目录结构设计
### 3. 核心模块开发
### 4. 接口实现

## 质量门禁
```bash
make lint    # 代码规范检查
make type     # 类型检查
make contract # 契约测试
make test     # 单元测试
```

## 开发注意事项
- 代码风格
- 性能考虑
- 安全要点

请确保实施计划详细、可执行。"""

    dev_response = llm.chat_simple(
        system_prompt="你是一位经验丰富的开发工程师，擅长将需求转化为高质量、可维护的代码。你的输出应该专业、详细且实用。",
        user_prompt=dev_prompt,
        max_tokens=4096,
    )

    if dev_response.error:
        content = f"""# Dev Report
Slice: {slice_obj['id']} - {slice_obj['title']}
Branch: {slice_obj['branch_name']}

AC:
{ac_text}

Gates:
- make lint
- make type
- make contract
- make test

[LLM Error: {dev_response.error}]
"""
    else:
        content = dev_response.content

    write_file(worktree, p, content)
    return AgentOutput([p], "Generated dev report using GLM-4.7.")

def run_qa(
    worktree: Path,
    slice_obj: dict[str, Any],
    ac_list: list[dict[str, Any]],
    user_id: Optional[int] = None,
    project_id: Optional[int] = None,
) -> AgentOutput:
    p = "reports/test_report.md"
    _assert_allowed("qa", [p])

    llm = get_llm_client(user_id=user_id, project_id=project_id)
    ac_text = "\n".join([f"- {a['code']}: {a['text']}" for a in ac_list])

    qa_prompt = f"""你是一位资深 QA 工程师。请为以下 Slice 生成测试计划和测试报告。

Slice 信息：
- ID: {slice_obj['id']}
- 标题: {slice_obj['title']}
- 分支: {slice_obj['branch_name']}
- 风险级别: {slice_obj['risk_level']}

验收标准：
{ac_text}

请生成包含以下内容的测试报告：

# 测试报告

## Slice 概述
- ID: {slice_obj['id']}
- 标题: {slice_obj['title']}
- 分支: {slice_obj['branch_name']}

## 验收标准映射
{ac_text}

## 测试策略
### 1. 单元测试
- 测试框架
- 覆盖率要求

### 2. 集成测试
- API 测试
- 数据库测试

### 3. 端到端测试
- 关键业务流程

## 测试执行
```bash
make test                    # 运行所有测试
pytest tests/unit -q        # 单元测试
pytest tests/integration -q # 集成测试
```

## 测试用例
- 正常场景
- 边界条件
- 异常处理

## 缺陷报告模板

请确保测试计划全面、可执行。"""

    qa_response = llm.chat_simple(
        system_prompt="你是一位经验丰富的 QA 工程师，擅长设计全面的测试策略和执行测试计划。你的输出应该专业、详细且可执行。",
        user_prompt=qa_prompt,
        max_tokens=4096,
    )

    if qa_response.error:
        content = f"""# Test Report
Slice: {slice_obj['id']} - {slice_obj['title']}
Branch: {slice_obj['branch_name']}

AC:
{ac_text}

Run:
- make test
- (optional) pytest tests/integration -q

[LLM Error: {qa_response.error}]
"""
    else:
        content = qa_response.content

    write_file(worktree, p, content)
    return AgentOutput([p], "Generated test report using GLM-4.7.")

def run_ops(
    worktree: Path,
    slice_obj: dict[str, Any],
    ac_list: list[dict[str, Any]],
    user_id: Optional[int] = None,
    project_id: Optional[int] = None,
) -> AgentOutput:
    paths = ["docs/DEPLOY.md", "docs/RUNBOOK.md", "docs/RESOURCES.md", "reports/ops_report.md"]
    _assert_allowed("ops", paths)

    llm = get_llm_client(user_id=user_id, project_id=project_id)

    ops_prompt = f"""你是一位资深运维工程师。请为以下 Slice 生成运维文档。

Slice 信息：
- ID: {slice_obj['id']}
- 标题: {slice_obj['title']}
- 分支: {slice_obj['branch_name']}
- 范围: {slice_obj['scope']}

请生成以下运维文档：

## 1. 部署文档 (DEPLOY.md)
### 部署架构
### 部署步骤
### 环境变量配置
### 数据库迁移
### 回滚方案

## 2. 运维手册 (RUNBOOK.md)
### 服务启动/停止
### 日常巡检
### 日志查看
### 常见问题处理
### 故障排查流程

## 3. 资源清单 (RESOURCES.md)
### 服务器资源
### 依赖服务
### 网络配置
### 存储需求

## 4. 运维报告 (ops_report.md)
### 监控指标
### 告警规则
### 性能基线
### 容量规划

请确保运维文档详细、可执行。"""

    ops_response = llm.chat_simple(
        system_prompt="你是一位经验丰富的运维工程师，擅长编写清晰的运维文档和设计可靠的运维方案。你的输出应该专业、详细且可执行。",
        user_prompt=ops_prompt,
        max_tokens=4096,
    )

    if ops_response.error:
        write_file(worktree, paths[0], f"# Deploy\nSlice {slice_obj['id']}\nBranch {slice_obj['branch_name']}\n\n[LLM Error: {ops_response.error}]\n")
        write_file(worktree, paths[1], f"# Runbook\nSlice {slice_obj['id']}\n\n[LLM Error: {ops_response.error}]\n")
        write_file(worktree, paths[2], f"# Resources\nSlice {slice_obj['id']}\n\n[LLM Error: {ops_response.error}]\n")
        write_file(worktree, paths[3], f"# Ops Report\nSlice {slice_obj['id']}\n\n[LLM Error: {ops_response.error}]\n")
    else:
        # Split the response into separate documents
        content = ops_response.content

        # Extract sections
        deploy_content = f"# Deploy\n\nSlice {slice_obj['id']}\nBranch: {slice_obj['branch_name']}\n\nGenerated at: {now_iso()}\n\n"
        runbook_content = f"# Runbook\n\nSlice {slice_obj['id']}\nBranch: {slice_obj['branch_name']}\n\nGenerated at: {now_iso()}\n\n"
        resources_content = f"# Resources\n\nSlice {slice_obj['id']}\nBranch: {slice_obj['branch_name']}\n\nGenerated at: {now_iso()}\n\n"
        ops_report_content = f"# Ops Report\n\nSlice {slice_obj['id']}\nBranch: {slice_obj['branch_name']}\n\nGenerated at: {now_iso()}\n\n"

        # Add the AI generated content
        current_section = None
        current_content = []
        for line in content.split('\n'):
            if line.startswith('## 1. 部署文档') or line.startswith('# 部署文档'):
                current_section = 'deploy'
            elif line.startswith('## 2. 运维手册') or line.startswith('# 运维手册'):
                current_section = 'runbook'
            elif line.startswith('## 3. 资源清单') or line.startswith('# 资源清单'):
                current_section = 'resources'
            elif line.startswith('## 4. 运维报告') or line.startswith('# 运维报告'):
                current_section = 'ops_report'
            elif current_section:
                current_content.append(line)

            if current_section == 'deploy' and line.startswith('## 2.'):
                deploy_content += '\n'.join(current_content[:-1])
                current_content = []
            elif current_section == 'runbook' and line.startswith('## 3.'):
                runbook_content += '\n'.join(current_content[:-1])
                current_content = []
            elif current_section == 'resources' and line.startswith('## 4.'):
                resources_content += '\n'.join(current_content[:-1])
                current_content = []

        # Add remaining content
        if current_section == 'deploy':
            deploy_content += '\n'.join(current_content)
        elif current_section == 'runbook':
            runbook_content += '\n'.join(current_content)
        elif current_section == 'resources':
            resources_content += '\n'.join(current_content)
        elif current_section == 'ops_report':
            ops_report_content += '\n'.join(current_content)

        write_file(worktree, paths[0], deploy_content)
        write_file(worktree, paths[1], runbook_content)
        write_file(worktree, paths[2], resources_content)
        write_file(worktree, paths[3], ops_report_content)

    return AgentOutput(paths, "Generated ops docs using GLM-4.7.")

ROLE_RUNNERS = {"pm": run_pm, "architect": run_architect, "dev": run_dev, "qa": run_qa, "ops": run_ops}

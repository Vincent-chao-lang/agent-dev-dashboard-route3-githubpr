"""
ADSE (AI-Driven Software Engineering) Module

Implements the ADSE methodology for enhanced AI-generated code quality:
- Four Quadrant Requirements Method
- Meta-Prompt Generation
- Logic Constraints Tracking

Based on the ADSE methodology by @超哥践行
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional

from .db import fetchone, fetchall, execute
from .utils import now_iso


@dataclass
class ADSEQuadrants:
    """Four Quadrant Requirements data class."""
    functional_core: str = ""
    physical_constraints: str = ""
    semantic_contract: str = ""
    exceptions_edges: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "functional_core": self.functional_core,
            "physical_constraints": self.physical_constraints,
            "semantic_contract": self.semantic_contract,
            "exceptions_edges": self.exceptions_edges,
        }

    def is_empty(self) -> bool:
        """Check if all quadrants are empty."""
        return not any([
            self.functional_core,
            self.physical_constraints,
            self.semantic_contract,
            self.exceptions_edges,
        ])


# Four Quadrant Templates for different project types
QUADRANT_TEMPLATES = {
    "web_api": {
        "functional_core": """系统要解决的核心业务问题是什么？

示例：用户通过API完成核心业务流程
- 用户认证和授权
- 资源的CRUD操作
- 业务逻辑处理

请描述这个Slice要实现的核心功能，以及成功后的业务终态。""",
        "physical_constraints": """技术栈和环境约束

示例：
- 框架: FastAPI / Flask
- 数据库: PostgreSQL / MySQL
- 认证方式: JWT / OAuth2
- API文档: OpenAPI / Swagger
- 性能要求: QPS > 1000

请列出必须使用的技术栈、框架、性能要求等硬性约束。""",
        "semantic_contract": """逻辑法则与安全边界（这是最重要的"立法"部分）

示例：
- 所有接口必须包含异常处理，返回标准错误格式
- 数据库查询必须加索引，避免全表扫描
- 敏感数据必须加密存储（密码使用bcrypt）
- 数据一致性由数据库事务保证
- 禁止直接返回数据库异常给客户端
- 所有外部API调用必须设置超时时间

请列出AI生成代码时必须遵守的规则，包括禁止的操作和强制的要求。""",
        "exceptions_edges": """异常处理和边缘情况

示例：
- API超时: 返回504，记录日志，触发告警
- 数据库连接失败: 重试3次，降级到缓存
- 并发冲突: 使用乐观锁，返回409 Conflict
- 参数校验失败: 返回400，详细说明错误字段
- 库存为零: 返回具体错误码，提示用户

请考虑各种异常情况和边缘场景，以及对应的处理策略。""",
    },
    "frontend": {
        "functional_core": """用户通过UI完成核心交互操作

示例：
- 用户登录/注册
- 数据展示和筛选
- 表单提交和反馈

请描述这个Slice要实现的核心交互功能。""",
        "physical_constraints": """前端技术栈约束

示例：
- 框架: React / Vue / Next.js
- UI库: Ant Design / Element Plus
- 状态管理: Redux / Zustand
- 构建工具: Vite / Webpack
- 浏览器兼容: Chrome 90+, Safari 14+

请列出前端技术栈和兼容性要求。""",
        "semantic_contract": """前端代码规范和安全边界

示例：
- 所有用户输入必须校验和转义，防止XSS
- 敏感操作必须二次确认
- API错误必须友好展示给用户
- 加载状态必须有明确提示
- 禁止使用eval()等危险函数
- 所有异步操作必须有错误处理

请列出前端代码必须遵守的规则。""",
        "exceptions_edges": """前端异常和边缘情况

示例：
- 网络请求失败: 展示重试按钮
- 页面加载超时: 显示骨架屏
- 用户权限不足: 跳转到403页面
- 浏览器不支持: 提示升级浏览器

请考虑前端可能遇到的各种异常情况。""",
    },
    "backend_service": {
        "functional_core": """后端服务的核心业务逻辑

示例：
- 数据处理和转换
- 消息队列消费
- 定时任务执行

请描述后端服务的核心功能。""",
        "physical_constraints": """后端服务约束

示例：
- 语言: Python / Go / Java
- 数据库: PostgreSQL / Redis
- 消息队列: RabbitMQ / Kafka
- 容器化: Docker / Kubernetes
- 资源限制: 内存 < 512MB

请列出后端服务的技术栈和资源约束。""",
        "semantic_contract": """后端代码规范

示例：
- 所有数据库操作必须在事务中执行
- 外部服务调用必须设置超时和熔断
- 敏感配置从环境变量读取，禁止硬编码
- 日志必须包含请求ID，便于追踪
- 禁止在循环中执行数据库查询
- 所有异常必须捕获并记录

请列出后端代码必须遵守的规则。""",
        "exceptions_edges": """后端服务异常处理

示例：
- 消息消费失败: 进入死信队列
- 定时任务超时: 发送告警
- 数据库连接池耗尽: 拒绝新请求
- 依赖服务不可用: 降级到本地缓存

请考虑后端服务可能遇到的异常情况。""",
    },
    "data_pipeline": {
        "functional_core": """数据处理流程的核心功能

示例：
- 数据抽取和转换
- 数据质量校验
- 数据聚合和分析

请描述数据管道的核心功能。""",
        "physical_constraints": """数据管道约束

示例：
- 处理框架: Apache Airflow / dbt
- 数据仓库: Snowflake / BigQuery
- 数据湖: S3 / HDFS
- 处理延迟: < 5分钟
- 数据量级: TB级

请列出数据管道的技术栈和性能要求。""",
        "semantic_contract": """数据处理规范

示例：
- 所有数据必须有schema定义
- 数据质量校验必须在转换前完成
- 敏感数据必须脱敏处理
- 数据血缘必须完整记录
- 禁止在数据管道中硬编码密钥
- 所有错误必须记录到监控系统

请列出数据处理必须遵守的规则。""",
        "exceptions_edges": """数据管道异常处理

示例：
- 数据源不可用: 重试3次，发送告警
- 数据格式异常: 记录到错误表，跳过该条数据
- 数据量突增: 触发扩容
- 数据质量不合格: 阻断下游任务

请考虑数据管道可能遇到的异常情况。""",
    },
}


def get_quadrants(slice_id: int) -> Optional[ADSEQuadrants]:
    """
    Get ADSE quadrants for a slice.

    Args:
        slice_id: Slice ID

    Returns:
        ADSEQuadrants if found, None otherwise
    """
    row = fetchone(
        "SELECT * FROM slice_adse_quadrants WHERE slice_id = ?",
        (slice_id,)
    )

    if not row:
        return None

    return ADSEQuadrants(
        functional_core=row["functional_core"] or "",
        physical_constraints=row["physical_constraints"] or "",
        semantic_contract=row["semantic_contract"] or "",
        exceptions_edges=row["exceptions_edges"] or "",
    )


def set_quadrants(
    slice_id: int,
    functional_core: str = "",
    physical_constraints: str = "",
    semantic_contract: str = "",
    exceptions_edges: str = "",
) -> int:
    """
    Set or update ADSE quadrants for a slice.

    Args:
        slice_id: Slice ID
        functional_core: Functional core requirements
        physical_constraints: Physical constraints
        semantic_contract: Semantic contract and rules
        exceptions_edges: Exception and edge cases

    Returns:
        Quadrant ID
    """
    existing = fetchone(
        "SELECT id FROM slice_adse_quadrants WHERE slice_id = ?",
        (slice_id,)
    )

    now = now_iso()

    if existing:
        execute(
            """UPDATE slice_adse_quadrants
               SET functional_core = ?, physical_constraints = ?,
                   semantic_contract = ?, exceptions_edges = ?, updated_at = ?
               WHERE id = ?""",
            (functional_core, physical_constraints, semantic_contract,
             exceptions_edges, now, existing["id"])
        )
        return int(existing["id"])
    else:
        return execute(
            """INSERT INTO slice_adse_quadrants
               (slice_id, functional_core, physical_constraints,
                semantic_contract, exceptions_edges, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (slice_id, functional_core, physical_constraints,
             semantic_contract, exceptions_edges, now, now)
        )


def get_template(template_type: str) -> Optional[dict[str, str]]:
    """
    Get quadrant template for a specific project type.

    Args:
        template_type: Type of template (web_api, frontend, etc.)

    Returns:
        Template dict if found, None otherwise
    """
    return QUADRANT_TEMPLATES.get(template_type)


def list_templates() -> list[dict[str, str]]:
    """
    List all available quadrant templates.

    Returns:
        List of template info dicts with 'type' and 'description' keys
    """
    return [
        {
            "type": "web_api",
            "description": "Web API 后端服务",
        },
        {
            "type": "frontend",
            "description": "前端应用",
        },
        {
            "type": "backend_service",
            "description": "后端服务",
        },
        {
            "type": "data_pipeline",
            "description": "数据管道",
        },
    ]


def generate_meta_prompt(
    slice_obj: dict[str, Any],
    quadrants: ADSEQuadrants,
    agent_role: str,
) -> str:
    """
    Generate enhanced meta-prompt for an agent based on ADSE quadrants.

    This is where the "立法" (Legislation) happens - converting the
    four quadrants into strict logical constraints that AI must follow.

    Args:
        slice_obj: Slice dictionary
        quadrants: ADSEQuadrants object
        agent_role: Agent role (pm, architect, dev, qa, ops)

    Returns:
        Enhanced meta-prompt string
    """
    base_prompt = f"""# ADSE 增强模式 - Meta Prompt

## Slice 信息
- ID: {slice_obj['id']}
- 标题: {slice_obj['title']}

---

## 四象限需求（立法核心）

### 1. 功能核心 (Functional Core)
{quadrants.functional_core or "未指定"}

### 2. 物理约束 (Physical Constraints)
{quadrants.physical_constraints or "未指定"}

### 3. 语义契约 (Semantic Contract) - 这是必须遵守的法律条文
{quadrants.semantic_contract or "未指定"}

### 4. 异常与边缘 (Exceptions & Edges)
{quadrants.exceptions_edges or "未指定"}

---

## Agent 角色特定指令

"""

    # Add role-specific instructions
    role_instructions = {
        "pm": """你是一位资深产品经理。基于以上四象限需求，生成产品需求文档（PRD）。

关键要求：
1. 功能核心必须完整覆盖
2. 物理约束中的技术要求必须在PRD中体现
3. 语义契约中的规则必须在需求中明确
4. 异常处理场景必须在用例中覆盖

请使用 Markdown 格式输出完整的 PRD。""",

        "architect": """你是一位资深架构师。基于以上四象限需求，生成技术架构设计文档。

关键要求：
1. 架构设计必须满足物理约束中的技术栈要求
2. 语义契约中的规则必须通过架构设计来保证
3. 异常处理场景必须在架构设计中考虑
4. 必须考虑可扩展性、可维护性、安全性

请使用 Markdown 格式输出完整的架构设计文档。""",

        "dev": """你是一位资深开发工程师。基于以上四象限需求，生成实现代码。

关键要求：
1. 必须严格遵守语义契约中的所有规则
2. 代码结构必须符合物理约束要求
3. 必须实现所有异常处理逻辑
4. 代码必须包含完整注释和文档

请生成高质量的、生产级别的代码。""",

        "qa": """你是一位资深测试工程师。基于以上四象限需求，生成测试用例。

关键要求：
1. 测试用例必须覆盖功能核心的所有场景
2. 必须包含语义契约中提到的所有规则验证
3. 必须包含异常与边缘情况的所有测试
4. 测试用例必须可执行、可自动化

请使用 Markdown 格式输出完整的测试计划和测试用例。""",

        "ops": """你是一位资深运维工程师。基于以上四象限需求，生成运维文档。

关键要求：
1. 部署文档必须符合物理约束中的环境要求
2. 监控方案必须覆盖语义契约中的关键指标
3. 应急预案必须包含异常与边缘情况的处理
4. 文档必须包含完整的部署、监控、告警配置

请使用 Markdown 格式输出完整的运维文档。""",
    }

    return base_prompt + role_instructions.get(agent_role, "")


def save_meta_prompt(slice_id: int, agent_role: str, prompt_content: str) -> int:
    """
    Save generated meta-prompt for tracking.

    Args:
        slice_id: Slice ID
        agent_role: Agent role
        prompt_content: The generated meta-prompt

    Returns:
        Meta-prompt record ID
    """
    now = now_iso()
    return execute(
        """INSERT INTO slice_meta_prompts (slice_id, agent_role, prompt_content, version, created_at)
           VALUES (?, ?, ?, 1, ?)""",
        (slice_id, agent_role, prompt_content, now)
    )


def get_slice_meta_prompts(slice_id: int) -> list[dict]:
    """
    Get all meta-prompts for a slice.

    Args:
        slice_id: Slice ID

    Returns:
        List of meta-prompt dictionaries
    """
    rows = fetchall(
        "SELECT * FROM slice_meta_prompts WHERE slice_id = ? ORDER BY created_at DESC",
        (slice_id,)
    )
    return [dict(r) for r in rows]

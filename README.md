# Agent Dev Dashboard 

> **基于 SOP 驱动的多 Agent 协作开发工作台**

一个集成了智谱 GLM-4.7 大模型的多 Agent 协作开发平台，通过标准化流程、产物约束、质量门禁和完整审计，将大模型 Agent 的风险降到可控范围。

## 🎯 核心理念

> **"大模型 Agent 可以做很多过去要人做的工作，但要靠 SOP、产物约束、门禁、审计记录来把风险降到可控"**

- **多 Agent 并行**：不是为了"全自动"，而是为了**按需加速**
- **人类总指挥**：设定目标、验收标准、合并决策
- **工具价值**：流程固定化、输出结构化、错误可追溯

## ✨ 主要特性

| 特性 | 说明 |
|------|------|
| 🤖 **GLM-4.7 集成** | 所有 Agent 使用智谱 GLM-4.7 生成专业文档 |
| 🗄️ **数据库支持** | 开发环境 SQLite / 生产环境 PostgreSQL，一键切换 |
| 🔐 **用户认证** | 本地账户系统，支持邀请码注册 |
| 👥 **团队协作** | 项目成员管理，支持 Owner 和 Member 角色 |
| 🔄 **Git 隔离** | 基于 Git Worktree 的独立开发环境 |
| ⚙️ **灵活配置** | 支持用户级、项目级、全局 LLM 配置 |
| 🚀 **ADSE 增强** | 可选的四象限需求法，提升 AI 生成代码质量 |
| ✅ **质量门禁** | Lint、Type Check、Contract、Test 自动化检查 |
| 🔀 **GitHub PR** | 自动创建 PR 并推送门禁结果 |
| 🌐 **多语言** | 支持中英文界面切换 |
| 📝 **完整审计** | 所有操作全量记录，可追溯 |

## 🚀 快速开始

### 方案一：开发环境（SQLite）

适合个人开发或小团队，零配置启动。

```bash
# 克隆项目
git clone <repository-url>
cd agent-dev-dashboard-route3-githubpr

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 配置环境变量（SQLite 默认配置）
export APP_DB_PATH=./dashboard.sqlite
export WORKSPACE_DIR=./workspace
export SESSION_SECRET="change-me-please"

# 启动服务
uvicorn app.main:app --reload --port 8787
```

访问：http://127.0.0.1:8787

### 方案二：生产环境（PostgreSQL）

适合团队协作和生产部署，支持高并发。

```bash
# 创建 PostgreSQL 数据库
createdb agent_dashboard

# 安装 PostgreSQL 驱动
pip install psycopg2-binary

# 配置环境变量
export DATABASE_URL="postgresql://user:password@localhost:5432/agent_dashboard"
export WORKSPACE_DIR=/data/workspace
export SESSION_SECRET="strong-random-secret-here"

# 启动服务（首次启动自动创建表结构）
uvicorn app.main:app --port 8787
```

**💡 提示**：
- **新项目推荐**：直接使用 PostgreSQL，无需迁移
- **已有 SQLite 数据**：需要迁移到 PostgreSQL，参阅 [数据库迁移指南](docs/数据库迁移指南.md)

### 首个用户

如果数据库中没有用户，登录页面会显示**"创建首个用户"**按钮。

### 配置智谱 AI API Key

编辑 `.env` 文件：

```bash
# 必需配置
LLM_API_KEY=your-zhipuai-api-key-here
LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4/
LLM_MODEL=glm-4-plus
```

获取 API Key：访问 [智谱 AI 开放平台](https://open.bigmodel.cn/)

## 📖 文档

- **[用户指南](docs/用户指南.md)** - 完整的中文用户指南，包含详细示例和使用说明
- **[数据库迁移指南](docs/数据库迁移指南.md)** - SQLite 与 PostgreSQL 切换及数据迁移说明

## 🏗️ 系统架构

### 系统组件

```
┌─────────────────────────────────────────┐
│         FastAPI Web Application          │
├─────────────────────────────────────────┤
│  用户认证与会话管理                       │
│  项目与 Slice 管理                       │
│  Agent 执行引擎                          │
│  质量门禁系统                            │
│  Git 操作 (Worktree)                     │
│  数据库 (SQLite / PostgreSQL)            │
└─────────────────────────────────────────┘
```

### Slice 状态机

```
草稿 → 上下文就绪 → PM → 架构设计 → 开发 → 测试 → 运维 → CI通过/CI失败
```

### Agent 角色与权限

| 角色 | 职责 | 可写路径 |
|------|------|----------|
| **PM** | 需求分析、PRD 文档 | `docs/`、`tasks/` |
| **Architect** | 架构设计、API 契约 | `docs/`、`contracts/` |
| **Dev** | 代码开发、单元测试 | `src/`、`tests/unit/`、`reports/` |
| **QA** | 测试用例、质量保证 | `tests/`、`docker/`、`reports/` |
| **Ops** | 部署文档、运维手册 | `docs/`、`reports/` |

## 📋 典型工作流程

1. **创建项目** - 连接到 Git 仓库
2. **添加成员** - 邀请团队成员（仅 Owner）
3. **创建 Slice** - 定义开发任务（范围、风险级别）
4. **设定验收标准** - 定义明确的验收标准
5. **生成上下文包** - 为 AI Agent 准备上下文
6. **运行 Agent** - 按顺序执行 PM → Architect → Dev → QA → Ops
7. **运行门禁** - 自动化质量检查
8. **创建 PR** - 自动创建 GitHub PR
9. **审核合并** - 人工决策

## ✅ 质量门禁

默认门禁（通过仓库中的 `Makefile` 配置）：

```bash
make lint      # 代码风格检查 (flake8、black 等)
make type      # 类型检查 (mypy 等)
make contract  # API 契约验证 (OpenAPI 等)
make test      # 单元和集成测试 (pytest 等)
```

门禁结果会自动作为评论发布到 GitHub PR。

## 🔐 安全性

- **密码加密**：PBKDF2 + SHA-256，120,000 次迭代
- **会话管理**：服务端安全签名
- **访问控制**：基于项目成员的权限验证
- **路径安全**：路径遍历保护和 Agent 路径白名单
- **审计追踪**：数据库中完整记录所有操作

## 🌍 多语言支持

点击页面右上角的语言按钮切换 **English** 和 **中文**。

语言偏好保存在用户会话中，刷新页面后保持不变。

## 🛠️ 配置说明

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATABASE_URL` | 数据库连接 URL（PostgreSQL） | SQLite（`APP_DB_PATH`） |
| `APP_DB_PATH` | SQLite 数据库路径 | `./dashboard.sqlite` |
| `WORKSPACE_DIR` | Git worktrees 目录 | `./workspace` |
| `SESSION_SECRET` | 会话加密密钥 | 自动生成 |
| `MAX_WORKERS` | 后台工作线程数 | `4` |
| `DB_POOL_SIZE` | PostgreSQL 连接池大小 | `5` |
| `DB_MAX_OVERFLOW` | PostgreSQL 最大溢出连接数 | `10` |
| `GITHUB_TOKEN` | GitHub API 令牌 | - |
| `GITHUB_API_URL` | GitHub API 端点 | `https://api.github.com` |

### 数据库配置

系统使用 SQLAlchemy ORM，支持以下数据库：

**开发环境（SQLite）**：
```bash
# 使用默认配置，无需设置 DATABASE_URL
APP_DB_PATH=./dashboard.sqlite
```

**生产环境（PostgreSQL）**：
```bash
# 设置 DATABASE_URL 自动切换到 PostgreSQL
DATABASE_URL=postgresql://user:password@host:5432/database
```

**切换数据库**：只需修改环境变量，无需更改代码。详细迁移步骤请参阅 [数据库迁移指南](docs/数据库迁移指南.md)。

### LLM 配置层级

系统支持三层 LLM 配置，优先级从高到低：

```
1. 用户级配置
     ↓ (如果用户配置存在且有效)

2. 项目级配置
     ↓ (如果项目配置存在且有效)

3. 全局配置（.env 文件）
     ↓ (默认配置)
```

**配置位置**：
- **全局**：`.env` 文件
- **用户级**：用户设置页面 (`/settings`)
- **项目级**：项目详情页（仅 Owner 可见）

### Agent 路径权限

编辑 `app/config.py` 自定义角色写权限：

```python
ROLE_ALLOWED_PREFIXES = {
    "pm": ["docs/", "tasks/"],
    "architect": ["docs/", "contracts/"],
    "dev": ["src/", "tests/unit/", "reports/"],
    "qa": ["tests/", "docker/", "reports/"],
    "ops": ["docs/", "reports/"],
}
```

## 📁 项目结构

```
app/
├── main.py          # FastAPI 应用路由
├── auth.py          # 认证与用户管理
├── models.py        # SQLAlchemy ORM 模型
├── db.py            # 数据库操作（SQLAlchemy）
├── config.py        # 配置管理
├── git_ops.py       # Git 操作与 Worktree
├── agents.py        # AI Agent 执行器
├── adse.py          # ADSE 增强模式
├── adse_tools.py    # ADSE 工具链
├── gates.py         # 质量门禁
├── jobs.py          # 后台任务
├── github.py        # GitHub PR 集成
├── i18n.py          # 国际化支持
├── help.py          # 在线帮助
├── utils.py         # 工具函数
└── templates/       # Jinja2 模板
        ├── base.html
        ├── login.html
        ├── index.html
        ├── project.html
        ├── slice.html
        └── help.html
```

## 💡 关键设计决策

### Git Worktree 隔离

每个 Run 都在独立的 Git worktree 中执行：
- 防止并行操作间的干扰
- 支持安全的并发 Agent 执行
- 完成后易于清理

### 基于 Slice 的开发

- 每个 Slice = 一个分支 = 一个独立任务
- 通过 Git 提交保留完整历史
- 易于回滚和审查

### 基于角色的访问控制

- Agent 只能写入指定路径
- 防止意外修改
- 强制关注点分离

### 完整审计追踪

所有操作都会被记录：
- 用户操作（登录、创建、更新）
- Agent 执行（输入、输出、文件变更）
- 门禁结果（通过/失败、输出）
- 文件修改（带 Git SHA 的产物）

## 🚀 ADSE 增强模式

### 什么是 ADSE？

**ADSE（AI-Driven Software Engineering）** 是一种通过**逻辑压制代码**的软件工程新范式，核心理念是：不再把代码当成核心资产，而是把**"定义代码生成的逻辑指令"**当成看家本领。

### 三板斧落地

| 步骤 | 名称 | 目标 | 示例 |
|------|------|------|------|
| **立法** | Meta-Prompting | 把经验变成AI无法违背的逻辑指令 | "所有接口必须包含异常处理" |
| **筑墙** | Constraints | 强制定义物理目录结构 | 核心逻辑和扩展功能严格分离 |
| **审计** | Logic Audit | 反向解构业务意图，与原始需求比对 | 确保AI生成的代码可理解、可追溯 |

### 四象限需求法

在创建 Slice 时，可以启用 ADSE 增强模式，填写四象限需求：

| 象限 | 关注点 | 示例 |
|------|--------|------|
| **功能核心** | 业务主路径与终态 | 用户通过API完成CRUD操作 |
| **物理约束** | 技术栈与环境 | FastAPI + PostgreSQL，QPS > 1000 |
| **语义契约** | 逻辑法则与安全边界 | 所有接口必须包含异常处理 |
| **异常与边缘** | 异常处理与鲁棒性 | API超时返回504，触发告警 |

## 🔗 GitHub PR 自动化

### 配置

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
export GITHUB_API_URL=https://api.github.com  # 可选，用于 GitHub Enterprise
```

### 工作流程

1. **创建 Slice** → 执行 Agent → 运行门禁
2. **点击"创建/更新 PR"** → 系统推送分支并创建 PR
3. **门禁结果自动评论** → 每个门禁运行结果自动发布到 PR

### 支持的 URL 格式

- SSH：`git@github.com:owner/repo.git`
- HTTPS：`https://github.com/owner/repo.git`

## ⚠️ 重要说明

- 提交仅在 Slice 分支的**本地**，直到手动推送
- 推送分支需要服务器上配置 **Git 凭证**
- 合并到主分支和生产部署仍然是**手动**（人工控制）
- 系统设计用于**低流量**环境（进程内线程池）

## 🤝 贡献指南

欢迎贡献！感兴趣的领域：
- 新增 Agent 角色
- 自定义质量门禁
- 增强 UI/UX
- 添加更多语言支持

## 📄 开源协议

MIT License

## 🙏 致谢

构建工具：
- [FastAPI](https://fastapi.tiangolo.com/) - 现代 Python Web 框架
- [SQLAlchemy](https://www.sqlalchemy.org/) - Python SQL 工具包和 ORM
- [SQLite](https://www.sqlite.org/) - 嵌入式数据库（开发环境）
- [PostgreSQL](https://www.postgresql.org/) - 关系型数据库（生产环境）
- [Git](https://git-scm.com/) - 版本控制（支持 worktree）
- [Jinja2](https://jinja.palletsprojects.com/) - 模板引擎
- [智谱 AI](https://open.bigmodel.cn/) - GLM-4.7 大模型服务

---

**版本**：v2.0.0
**更新日期**：2025-01-29
**新特性**：
- ✨ GLM-4.7 大模型集成
- ✨ 三层 LLM 配置（用户/项目/全局）
- ✨ 邀请码注册系统
- ✨ ADSE 增强模式与工具链
- ✨ 多语言支持（中英文）
- ✨ 在线帮助系统
- ✨ 数据库抽象层（SQLite / PostgreSQL 一键切换）

详细使用说明请参阅 [用户指南](docs/用户指南.md)。

"""
Internationalization (i18n) module for Agent Dev Dashboard.
Supports English and Chinese languages.
"""
from typing import Dict

# Translations
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        # Common
        "app_name": "AI Coding Collaborative Development Workbench",
        "app_subtitle": "No coding required. AI-powered one-stop development platform covering the full lifecycle from requirements to deployment.",
        "logout": "Logout",
        "login": "Login",
        "username": "Username",
        "password": "Password",
        "invite_code": "Invitation Code",
        "create_user": "Create user",
        "create_first_user": "Create the first user",
        "register_with_invite": "Register with Invitation Code",
        "submit": "Submit",
        "add": "Add",
        "create": "Create",
        "delete": "Delete",
        "save": "Save",
        "cancel": "Cancel",
        "edit": "Edit",
        "loading": "Loading...",
        "no_data": "No data yet.",
        "error_user_not_found": "User not found. Please check the username.",
        "error_not_owner": "Only the project owner can add members.",
        "error_invalid_invite_code": "Invalid or expired invitation code.",

        # Invitations
        "invitations": "Invitations",
        "create_invitation": "Create Invitation",
        "expires_days": "Expires (days)",
        "invitation_code": "Code",
        "invitation_status": "Status",
        "invitation_created_by": "Created by",
        "invitation_used_by": "Used by",
        "invitation_created_at": "Created at",
        "invitation_expires_at": "Expires at",
        "status_pending": "Pending",
        "status_used": "Used",
        "status_cancelled": "Cancelled",
        "no_invitations": "No invitations yet.",
        "revoke": "Revoke",

        # LLM Configuration
        "llm_config": "LLM Configuration",
        "llm_provider": "Provider",
        "llm_api_key": "API Key",
        "llm_base_url": "API Base URL",
        "llm_model": "Model",
        "llm_temperature": "Temperature",
        "llm_max_tokens": "Max Tokens",
        "llm_config_source": "Configuration Source",
        "llm_source_global": "Global (Default)",
        "llm_source_user": "User Configuration",
        "llm_source_project": "Project Configuration",
        "save_config": "Save Configuration",
        "delete_config": "Delete Configuration",
        "config_saved": "Configuration saved successfully.",
        "config_deleted": "Configuration deleted successfully.",
        "no_user_config": "No user LLM configuration found. Using global default.",
        "no_project_config": "No project LLM configuration found.",
        "provider_glm": "GLM (Zhipu AI)",
        "provider_openai": "OpenAI",
        "settings": "Settings",
        "user_settings": "User Settings",
        "project_settings": "Project Settings",
        "current_config": "Current Configuration",
        "effective_config": "Effective Configuration",

        # ADSE (AI-Driven Software Engineering)
        "adse_enable": "Enable ADSE Enhancement (Four Quadrant Requirements)",
        "adse_enable_desc": "ADSE methodology enhances AI-generated code quality through structured requirements. Recommended for advanced users.",
        "adse_four_quadrants": "Four Quadrant Requirements",
        "adse_template_type": "Template Type",
        "adse_no_template": "Blank (Fill manually)",
        "adse_template_web_api": "Web API",
        "adse_template_frontend": "Frontend Application",
        "adse_template_backend": "Backend Service",
        "adse_template_data": "Data Pipeline",
        "adse_template_desc": "Select a template to pre-fill the four quadrants. You can customize after selection.",
        "adse_quadrant_functional": "Functional Core",
        "adse_quadrant_physical": "Physical Constraints",
        "adse_quadrant_semantic": "Semantic Contract (Logic Rules)",
        "adse_quadrant_exceptions": "Exceptions & Edge Cases",
        "adse_quadrant_functional_placeholder": "What is the core business problem this system solves? Describe the main business flow and the desired end state.",
        "adse_quadrant_physical_placeholder": "Technology stack and environmental constraints (e.g., frameworks, databases, performance requirements).",
        "adse_quadrant_semantic_placeholder": "Logic rules and security boundaries that AI must follow. This is the most important 'legislation' part. Example: All APIs must include exception handling, database queries must use indexes.",
        "adse_quadrant_semantic_hint": "These rules will be strictly enforced when AI generates code. Be specific and comprehensive.",
        "adse_quadrant_exceptions_placeholder": "Exception handling and edge cases. Consider various failure scenarios and corresponding strategies.",
        "adse_enabled": "ADSE Enhanced",

        # Login page
        "help": "Help",
        "login_title": "Login",
        "login_msg_invalid": "Invalid credentials",
        "login_msg_disabled": "Registration disabled",

        # Index page
        "projects": "Projects",
        "projects_title": "Projects",
        "create_project": "Create Project",
        "project_name": "Project name",
        "repo_url": "Repo URL",
        "default_branch": "Default branch",
        "create_clone": "Create & Clone",
        "no_projects": "No projects yet.",

        # Project page
        "members": "Members",
        "add_member": "Add member (username)",
        "role": "Role",
        "role_member": "member",
        "role_readonly": "readonly",
        "create_slice": "Create Slice",
        "slice_title": "Title",
        "slice_scope": "Scope",
        "slice_out_of_scope": "Out of scope",
        "slice_risk_level": "Risk level",
        "risk_read_only": "read-only",
        "risk_low_write": "low-write",
        "risk_high_risk": "high-risk",
        "slices": "Slices",
        "no_slices": "No slices yet.",

        # Slice page
        "slice": "Slice",
        "pr_github": "PR (GitHub)",
        "pr_no_pr": "No PR created yet (requires GITHUB_TOKEN and GitHub repo URL).",
        "create_update_pr": "Create/Update PR",
        "pr_auto_comment": "If PR exists, Gates will auto-comment results.",
        "pr_commands_manual": "PR commands (manual)",
        "push_branch": "Push branch (background)",
        "push_branch_hint": "Server must have git credentials.",
        "actions": "Actions",
        "generate_context_pack": "Generate Context Pack",
        "run_gates": "Run Gates",
        "roles": "Roles",
        "run": "Run",
        "latest_context_pack": "Latest Context Pack",
        "no_context_pack": "No context pack yet.",
        "acceptance_criteria": "Acceptance Criteria",
        "ac_code": "Code",
        "ac_text": "Text",
        "ac_verification": "Verification",
        "add_ac": "Add AC",
        "no_ac": "No AC yet.",
        "runs": "Runs",
        "no_runs": "No runs yet.",
        "worktree": "worktree",
        "gates": "Gates",
        "no_gates": "No gates yet.",
        "refresh_tip": "Tip: refresh to see background job progress.",
        "status": "status",
        "branch": "branch",
        "risk": "risk",
        "created_by": "created by",
        "created_at": "at",
        "verify": "verify",
        "repo_local": "repo local",

        # Status
        "status_draft": "Draft",
        "status_context_ready": "ContextReady",
        "status_pm_done": "PMDone",
        "status_design_done": "DesignDone",
        "status_dev_in_progress": "DevInProgress",
        "status_qa_done": "QADone",
        "status_ops_ready": "OpsReady",
        "status_ci_passed": "CIPassed",
        "status_ci_failed": "CIFailed",

        # Run status
        "run_status_queued": "queued",
        "run_status_running": "running",
        "run_status_success": "success",
        "run_status_failed": "failed",

        # Gate status
        "gate_status_pass": "pass",
        "gate_status_fail": "fail",

        # Help page
        "search_results": "Search Results",
        "search_help_placeholder": "Search help documentation...",
        "no_results": "No results found",
        "quick_start": "Quick Start",
        "quick_start_desc": "Get started with the system",
        "core_concepts_desc": "Understand the core concepts",
        "adse_enhancement": "ADSE Enhancement",
        "adse_enhancement_desc": "Learn about ADSE methodology",
        "llm_config_desc": "Configure LLM settings",
    },

    "zh": {
        # Common
        "app_name": "AI Coding 协作开发工作台",
        "app_subtitle": "无需编码,全程基于AI的覆盖从需求到设计,开发,测试到部署的一站式开发平台",
        "logout": "退出登录",
        "login": "登录",
        "username": "用户名",
        "password": "密码",
        "invite_code": "邀请码",
        "create_user": "创建用户",
        "create_first_user": "创建首个用户",
        "register_with_invite": "使用邀请码注册",
        "submit": "提交",
        "add": "添加",
        "create": "创建",
        "delete": "删除",
        "save": "保存",
        "cancel": "取消",
        "edit": "编辑",
        "loading": "加载中...",
        "no_data": "暂无数据",
        "error_user_not_found": "用户不存在，请检查用户名",
        "error_not_owner": "只有项目所有者可以添加成员",
        "error_invalid_invite_code": "邀请码无效或已过期",

        # Invitations
        "invitations": "邀请码",
        "create_invitation": "创建邀请码",
        "expires_days": "有效期（天）",
        "invitation_code": "邀请码",
        "invitation_status": "状态",
        "invitation_created_by": "创建者",
        "invitation_used_by": "使用者",
        "invitation_created_at": "创建时间",
        "invitation_expires_at": "过期时间",
        "status_pending": "待使用",
        "status_used": "已使用",
        "status_cancelled": "已取消",
        "no_invitations": "暂无邀请码",
        "revoke": "撤销",

        # LLM Configuration
        "llm_config": "LLM 配置",
        "llm_provider": "提供商",
        "llm_api_key": "API 密钥",
        "llm_base_url": "API 基础 URL",
        "llm_model": "模型",
        "llm_temperature": "温度",
        "llm_max_tokens": "最大 Token 数",
        "llm_config_source": "配置来源",
        "llm_source_global": "全局（默认）",
        "llm_source_user": "用户配置",
        "llm_source_project": "项目配置",
        "save_config": "保存配置",
        "delete_config": "删除配置",
        "config_saved": "配置保存成功。",
        "config_deleted": "配置删除成功。",
        "no_user_config": "未找到用户 LLM 配置，使用全局默认配置。",
        "no_project_config": "未找到项目 LLM 配置。",
        "provider_glm": "GLM (智谱 AI)",
        "provider_openai": "OpenAI",
        "settings": "设置",
        "user_settings": "用户设置",
        "project_settings": "项目设置",
        "current_config": "当前配置",
        "effective_config": "有效配置",

        # ADSE (AI-Driven Software Engineering)
        "adse_enable": "启用 ADSE 增强模式（四象限需求法）",
        "adse_enable_desc": "ADSE 方法论通过结构化需求提升 AI 生成代码的质量。推荐高级用户使用。",
        "adse_four_quadrants": "四象限需求",
        "adse_template_type": "模板类型",
        "adse_no_template": "空白（手动填写）",
        "adse_template_web_api": "Web API",
        "adse_template_frontend": "前端应用",
        "adse_template_backend": "后端服务",
        "adse_template_data": "数据管道",
        "adse_template_desc": "选择模板预填充四象限内容，选择后可自行修改。",
        "adse_quadrant_functional": "功能核心",
        "adse_quadrant_physical": "物理约束",
        "adse_quadrant_semantic": "语义契约（逻辑规则）",
        "adse_quadrant_exceptions": "异常与边缘",
        "adse_quadrant_functional_placeholder": "系统要解决的核心业务问题是什么？请描述主要业务流程和成功的业务终态。",
        "adse_quadrant_physical_placeholder": "技术栈和环境约束（如框架、数据库、性能要求等）。",
        "adse_quadrant_semantic_placeholder": "AI 生成代码时必须遵守的逻辑规则和安全边界。这是最重要的「立法」部分。示例：所有接口必须包含异常处理、数据库查询必须加索引。",
        "adse_quadrant_semantic_hint": "这些规则将在 AI 生成代码时被严格执行，请尽可能具体和全面。",
        "adse_quadrant_exceptions_placeholder": "异常处理和边缘情况。请考虑各种异常场景和对应的处理策略。",
        "adse_enabled": "ADSE 增强模式",

        # Login page
        "help": "帮助",
        "login_title": "登录",
        "login_msg_invalid": "用户名或密码错误",
        "login_msg_disabled": "注册功能已关闭",

        # Index page
        "projects": "项目",
        "projects_title": "项目列表",
        "create_project": "创建项目",
        "project_name": "项目名称",
        "repo_url": "仓库地址",
        "default_branch": "默认分支",
        "create_clone": "创建并克隆",
        "no_projects": "暂无项目",

        # Project page
        "members": "成员",
        "add_member": "添加成员（用户名）",
        "role": "角色",
        "role_member": "成员",
        "role_readonly": "只读",
        "create_slice": "创建 Slice",
        "slice_title": "标题",
        "slice_scope": "范围",
        "slice_out_of_scope": "超出范围",
        "slice_risk_level": "风险级别",
        "risk_read_only": "只读",
        "risk_low_write": "低风险写入",
        "risk_high_risk": "高风险",
        "slices": "Slice 列表",
        "no_slices": "暂无 Slice",

        # Slice page
        "slice": "Slice",
        "pr_github": "PR（GitHub）",
        "pr_no_pr": "尚未创建 PR（需要配置 GITHUB_TOKEN 和 GitHub 仓库地址）",
        "create_update_pr": "创建/更新 PR",
        "pr_auto_comment": "如果 PR 已存在，门禁检查结果将自动评论到 PR。",
        "pr_commands_manual": "PR 手动命令",
        "push_branch": "推送分支（后台）",
        "push_branch_hint": "服务器必须配置 Git 凭证",
        "actions": "操作",
        "generate_context_pack": "生成上下文包",
        "run_gates": "运行门禁",
        "roles": "角色",
        "run": "运行",
        "latest_context_pack": "最新上下文包",
        "no_context_pack": "暂无上下文包",
        "acceptance_criteria": "验收标准",
        "ac_code": "编号",
        "ac_text": "描述",
        "ac_verification": "验证方式",
        "add_ac": "添加验收标准",
        "no_ac": "暂无验收标准",
        "runs": "运行记录",
        "no_runs": "暂无运行记录",
        "worktree": "工作树",
        "gates": "门禁",
        "no_gates": "暂无门禁记录",
        "refresh_tip": "提示：刷新页面查看后台任务进度",
        "status": "状态",
        "branch": "分支",
        "risk": "风险",
        "created_by": "创建者",
        "created_at": "创建时间",
        "verify": "验证",
        "repo_local": "本地仓库",

        # Status
        "status_draft": "草稿",
        "status_context_ready": "上下文就绪",
        "status_pm_done": "PM 完成",
        "status_design_done": "设计完成",
        "status_dev_in_progress": "开发中",
        "status_qa_done": "QA 完成",
        "status_ops_ready": "运维就绪",
        "status_ci_passed": "CI 通过",
        "status_ci_failed": "CI 失败",

        # Run status
        "run_status_queued": "排队中",
        "run_status_running": "运行中",
        "run_status_success": "成功",
        "run_status_failed": "失败",

        # Gate status
        "gate_status_pass": "通过",
        "gate_status_fail": "失败",

        # Help page
        "search_results": "搜索结果",
        "search_help_placeholder": "搜索帮助文档...",
        "no_results": "未找到相关结果",
        "quick_start": "快速开始",
        "quick_start_desc": "快速上手系统使用",
        "core_concepts_desc": "了解系统核心概念",
        "adse_enhancement": "ADSE 增强模式",
        "adse_enhancement_desc": "了解 ADSE 方法论",
        "llm_config_desc": "配置 LLM 设置",
    },
}


def get_translation(lang: str, key: str, **kwargs) -> str:
    """
    Get translated text for a given key and language.

    Args:
        lang: Language code ('en' or 'zh')
        key: Translation key
        **kwargs: Variables for string formatting

    Returns:
        Translated string, or the key itself if not found
    """
    if lang not in TRANSLATIONS:
        lang = "en"
    if key not in TRANSLATIONS[lang]:
        return key
    text = TRANSLATIONS[lang][key]
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            return text
    return text


def t(lang: str, key: str, **kwargs) -> str:
    """Shorthand for get_translation."""
    return get_translation(lang, key, **kwargs)


def get_language(request) -> str:
    """
    Get the current language from session or default to English.

    Args:
        request: FastAPI Request object

    Returns:
        Language code ('en' or 'zh')
    """
    lang = request.session.get("lang", "en")
    return lang if lang in ("en", "zh") else "en"


def set_language(request, lang: str) -> None:
    """
    Set the language in session.

    Args:
        request: FastAPI Request object
        lang: Language code ('en' or 'zh')
    """
    if lang in ("en", "zh"):
        request.session["lang"] = lang

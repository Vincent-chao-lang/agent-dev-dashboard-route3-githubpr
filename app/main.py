from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

# Load .env file at application startup
from dotenv import load_dotenv
load_dotenv()

from .db import init_db, fetchall, fetchone, execute
from .config import SESSION_SECRET
from .auth import authenticate, create_user, get_current_user, has_any_users
from .utils import now_iso, slugify, clamp_text, branch_name_for_slice
from .git_ops import clone_or_update_project_repo, create_worktree, commit_all, push_branch
from .context_pack import build_context_pack
from .agents import ROLE_RUNNERS
from .gates import run_gates
from .jobs import submit
from .github import parse_github_repo, create_or_get_pr, comment_on_pr
from .i18n import get_language, set_language, t
from .invitations import validate_invitation, use_invitation, get_project_invitations, create_invitation, revoke_invitation
from .llm_config import (
    get_user_config, get_project_config, get_effective_config, set_user_config, set_project_config,
    delete_user_config, delete_project_config, get_all_user_configs, get_all_project_configs, mask_api_key
)
from .llm_config import LLMConfig

app = FastAPI(title="Agent Dev Dashboard (Route-3 Monolith)")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, same_site="lax", https_only=False)
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _get_template_context(request: Request, **extra) -> dict:
    """Build common template context with language support."""
    lang = get_language(request)
    ctx = {
        "request": request,
        "lang": lang,
        "t": lambda key, **kwargs: t(lang, key, **kwargs),
        "user": get_current_user(request),
    }
    ctx.update(extra)
    return ctx

@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.post("/lang/{lang}")
def set_language_route(lang: str, request: Request):
    """Set language preference."""
    if lang in ("en", "zh"):
        set_language(request, lang)
    # Redirect back to referring page or home
    referer = request.headers.get("referer", "/")
    return RedirectResponse(url=referer, status_code=303)

@app.get("/settings", response_class=HTMLResponse)
def user_settings(request: Request, message: str = ""):
    """User settings page."""
    u = _require_user(request)
    lang = get_language(request)

    # Get current user config
    user_config = get_user_config(u["id"], "glm") or get_user_config(u["id"], "openai")
    if user_config:
        current_config = user_config.to_dict()
        current_config["api_key"] = mask_api_key(user_config.api_key)
        config_source = "user"
    else:
        current_config = {"provider": "glm", "api_key": "", "base_url": None, "model": None, "temperature": None, "max_tokens": None}
        config_source = "global"

    # Get effective config
    effective_config = get_effective_config(u["id"]).to_dict()

    return templates.TemplateResponse(
        "settings.html",
        _get_template_context(
            request,
            current_config=current_config,
            current_config_masked=mask_api_key(user_config.api_key) if user_config else "***",
            config_source=config_source,
            effective_config=effective_config,
            message=message,
        ),
    )

@app.get("/help", response_class=HTMLResponse)
def help_page(request: Request):
    """Online help page - displays the complete user guide."""
    lang = get_language(request)
    search_query = request.query_params.get("q", "")

    # Import help functions
    from .help import get_help_html, search_help

    # Handle search
    if search_query:
        search_results = search_help(search_query, lang)
        return templates.TemplateResponse(
            "help.html",
            _get_template_context(
                request,
                content={"title": "搜索结果", "content": "", "section": None},
                search_query=search_query,
                search_results=search_results,
            ),
        )

    # Render the complete user guide
    content = get_help_html(lang)

    return templates.TemplateResponse(
        "help.html",
        _get_template_context(
            request,
            content=content,
            search_query="",
            search_results=None,
        ),
    )

@app.post("/settings/llm")
def update_user_llm_config(
    request: Request,
    provider: str = Form("glm"),
    api_key: str = Form(""),
    base_url: str = Form(""),
    model: str = Form(""),
    temperature: str = Form(""),
    max_tokens: str = Form(""),
    delete: str = Form(""),
):
    """Update or delete user LLM configuration."""
    u = _require_user(request)

    if delete:
        delete_user_config(u["id"], provider)
        return RedirectResponse(url="/settings?message=config_deleted", status_code=303)

    # Only update API key if provided
    if not api_key:
        existing = get_user_config(u["id"], provider)
        if existing:
            api_key = existing.api_key
        else:
            return RedirectResponse(url="/settings?message=error_no_api_key", status_code=303)

    set_user_config(
        user_id=u["id"],
        provider=provider,
        api_key=api_key,
        base_url=base_url or None,
        model=model or None,
        temperature=float(temperature) if temperature else None,
        max_tokens=int(max_tokens) if max_tokens else None,
    )

    return RedirectResponse(url="/settings?message=config_saved", status_code=303)

def _require_user(request: Request) -> dict:
    u = get_current_user(request)
    if not u:
        raise PermissionError("Not authenticated")
    return u

def _user_can_access_project(user_id: int, project_id: int) -> bool:
    return fetchone("SELECT 1 FROM project_members WHERE project_id=? AND user_id=?", (project_id, user_id)) is not None

def _require_project_access(user_id: int, project_id: int) -> None:
    if not _user_can_access_project(user_id, project_id):
        raise PermissionError("No access to project")

def _slice_with_project(slice_id: int) -> tuple[dict[str, Any], dict[str, Any]]:
    s = fetchone("SELECT * FROM slices WHERE id=?", (slice_id,))
    if not s:
        raise RuntimeError("Slice not found")
    p = fetchone("SELECT * FROM projects WHERE id=?", (s["project_id"],))
    if not p:
        raise RuntimeError("Project not found")
    return dict(s), dict(p)

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, msg: str = ""):
    lang = get_language(request)
    msg_map = {
        "Invalid credentials": "login_msg_invalid",
        "Registration disabled": "login_msg_disabled",
        "Invalid invite code": "error_invalid_invite_code",
    }
    msg_key = msg_map.get(msg, msg)
    return templates.TemplateResponse(
        "login.html",
        _get_template_context(request, msg=msg_key, allow_create_first_user=not has_any_users()),
    )

@app.post("/login")
def login_action(request: Request, username: str = Form(...), password: str = Form(...)):
    u = authenticate(username.strip(), password)
    if not u:
        return RedirectResponse(url="/login?msg=Invalid%20credentials", status_code=303)
    request.session["user_id"] = u["id"]
    return RedirectResponse(url="/", status_code=303)

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)

@app.post("/register")
def register_first_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    invite_code: str = Form("")
):
    # If first user, allow registration without invite code
    if not has_any_users():
        uid = create_user(username.strip(), password)
        request.session["user_id"] = uid
        return RedirectResponse(url="/", status_code=303)

    # If users exist, require valid invite code
    invite_code = invite_code.strip()
    if not invite_code:
        return RedirectResponse(url="/login?msg=Invalid%20invite%20code", status_code=303)

    invitation = validate_invitation(invite_code)
    if not invitation:
        return RedirectResponse(url="/login?msg=Invalid%20invite%20code", status_code=303)

    # Create user and mark invitation as used
    uid = create_user(username.strip(), password)
    use_invitation(invite_code, uid)
    request.session["user_id"] = uid
    return RedirectResponse(url="/", status_code=303)

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    u = get_current_user(request)
    if not u:
        return RedirectResponse(url="/login", status_code=303)
    projects = fetchall(
        """SELECT p.* FROM projects p
           JOIN project_members m ON m.project_id=p.id
           WHERE m.user_id=?
           ORDER BY p.id DESC""",
        (u["id"],),
    )
    return templates.TemplateResponse("index.html", _get_template_context(request, projects=projects))

@app.post("/projects")
def create_project(request: Request, name: str = Form(...), repo_url: str = Form(...), default_branch: str = Form("main")):
    u = _require_user(request)
    proj_name = slugify(name)

    gh = parse_github_repo(repo_url)
    gh_owner = gh.owner if gh else None
    gh_repo = gh.repo if gh else None

    project_id = execute(
        "INSERT INTO projects(name, repo_url, default_branch, local_path, owner_user_id, created_at, github_owner, github_repo) VALUES(?,?,?,?,?,?,?,?)",
        (proj_name, repo_url, default_branch, "", u["id"], now_iso(), gh_owner, gh_repo),
    )
    repo = clone_or_update_project_repo(project_id, repo_url, default_branch)
    execute("UPDATE projects SET local_path=? WHERE id=?", (str(repo), project_id))
    execute("INSERT INTO project_members(project_id, user_id, role, created_at) VALUES(?,?,?,?)", (project_id, u["id"], "owner", now_iso()))
    return RedirectResponse(url="/", status_code=303)

@app.get("/projects/{project_id}", response_class=HTMLResponse)
def project_detail(project_id: int, request: Request, error: str = ""):
    u = _require_user(request)
    _require_project_access(u["id"], project_id)

    project = fetchone("SELECT * FROM projects WHERE id=?", (project_id,))
    if not project:
        return HTMLResponse("Project not found", status_code=404)

    clone_or_update_project_repo(project_id, project["repo_url"], project["default_branch"])

    slices = fetchall("SELECT * FROM slices WHERE project_id=? ORDER BY id DESC", (project_id,))
    members = fetchall(
        """SELECT u.username, m.role FROM project_members m
           JOIN users u ON u.id=m.user_id
           WHERE m.project_id=? ORDER BY m.role DESC, u.username""",
        (project_id,),
    )
    is_owner = fetchone(
        "SELECT 1 FROM project_members WHERE project_id=? AND user_id=? AND role='owner'",
        (project_id, u["id"]),
    ) is not None
    invitations = get_project_invitations(project_id)

    # Get project LLM config
    project_config = get_project_config(project_id, "glm") or get_project_config(project_id, "openai")
    if project_config:
        project_config_dict = project_config.to_dict()
        project_config_dict["api_key"] = mask_api_key(project_config.api_key)
        project_config_source = "project"
    else:
        project_config_dict = {"provider": "glm", "api_key": "", "base_url": None, "model": None, "temperature": None, "max_tokens": None}
        project_config_source = "global"

    return templates.TemplateResponse(
        "project.html",
        _get_template_context(
            request,
            project=project,
            slices=slices,
            members=members,
            is_owner=is_owner,
            invitations=invitations,
            project_config=project_config_dict,
            project_config_masked=mask_api_key(project_config.api_key) if project_config else "***",
            project_config_source=project_config_source,
            error=error,
        ),
    )

@app.post("/projects/{project_id}/members")
def add_member(project_id: int, request: Request, username: str = Form(...), role: str = Form("member")):
    u = _require_user(request)
    owner = fetchone("SELECT 1 FROM project_members WHERE project_id=? AND user_id=? AND role='owner'", (project_id, u["id"]))
    if not owner:
        return RedirectResponse(url=f"/projects/{project_id}?error=not_owner", status_code=303)
    target = fetchone("SELECT id FROM users WHERE username=?", (username.strip(),))
    if not target:
        return RedirectResponse(url=f"/projects/{project_id}?error=user_not_found", status_code=303)
    try:
        execute("INSERT INTO project_members(project_id, user_id, role, created_at) VALUES(?,?,?,?)", (project_id, target["id"], role, now_iso()))
    except Exception:
        pass  # User already a member
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)

@app.post("/projects/{project_id}/slices")
def create_slice(
    project_id: int,
    request: Request,
    title: str = Form(...),
    scope: str = Form(...),
    out_of_scope: str = Form(...),
    risk_level: str = Form("low-write"),
    adse_enabled: str = Form(""),
    functional_core: str = Form(""),
    physical_constraints: str = Form(""),
    semantic_contract: str = Form(""),
    exceptions_edges: str = Form(""),
):
    u = _require_user(request)
    _require_project_access(u["id"], project_id)

    # Check if ADSE is enabled
    adse_enabled_value = 1 if adse_enabled == "on" else 0

    slice_id = execute(
        "INSERT INTO slices(project_id, title, scope, out_of_scope, risk_level, status, branch_name, adse_enabled, created_by_user_id, created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (project_id, title, scope, out_of_scope, risk_level, "Draft", "pending", adse_enabled_value, u["id"], now_iso()),
    )

    # If ADSE is enabled, save the quadrants and initialize tools
    if adse_enabled_value and any([functional_core, physical_constraints, semantic_contract, exceptions_edges]):
        from .adse import set_quadrants
        from .adse_tools import create_p2c_tracking_items, initialize_project_control_table

        set_quadrants(
            slice_id,
            functional_core=functional_core,
            physical_constraints=physical_constraints,
            semantic_contract=semantic_contract,
            exceptions_edges=exceptions_edges,
        )

        # Initialize P2C tracking matrix
        p2c_count = create_p2c_tracking_items(slice_id)

        # Initialize ADSE project control table
        control_count = initialize_project_control_table(slice_id)

    branch = branch_name_for_slice(slice_id, title)
    execute("UPDATE slices SET branch_name=? WHERE id=?", (branch, slice_id))
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)

@app.post("/projects/{project_id}/invitations")
def create_invitation_route(project_id: int, request: Request, expires_days: int = Form(7)):
    u = _require_user(request)
    owner = fetchone("SELECT 1 FROM project_members WHERE project_id=? AND user_id=? AND role='owner'", (project_id, u["id"]))
    if not owner:
        return RedirectResponse(url=f"/projects/{project_id}?error=not_owner", status_code=303)
    create_invitation(project_id, u["id"], expires_days)
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)

@app.post("/projects/{project_id}/invitations/{invitation_id}/revoke")
def revoke_invitation_route(project_id: int, invitation_id: int, request: Request):
    u = _require_user(request)
    owner = fetchone("SELECT 1 FROM project_members WHERE project_id=? AND user_id=? AND role='owner'", (project_id, u["id"]))
    if not owner:
        return RedirectResponse(url=f"/projects/{project_id}?error=not_owner", status_code=303)
    revoke_invitation(invitation_id)
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)

@app.post("/projects/{project_id}/llm")
def update_project_llm_config(
    project_id: int,
    request: Request,
    provider: str = Form("glm"),
    api_key: str = Form(""),
    base_url: str = Form(""),
    model: str = Form(""),
    temperature: str = Form(""),
    max_tokens: str = Form(""),
    delete: str = Form(""),
):
    """Update or delete project LLM configuration."""
    u = _require_user(request)

    # Check if user is owner
    owner = fetchone("SELECT 1 FROM project_members WHERE project_id=? AND user_id=? AND role='owner'", (project_id, u["id"]))
    if not owner:
        return RedirectResponse(url=f"/projects/{project_id}?error=not_owner", status_code=303)

    if delete:
        delete_project_config(project_id, provider)
        return RedirectResponse(url=f"/projects/{project_id}", status_code=303)

    # Only update API key if provided
    if not api_key:
        existing = get_project_config(project_id, provider)
        if existing:
            api_key = existing.api_key
        else:
            return RedirectResponse(url=f"/projects/{project_id}", status_code=303)

    set_project_config(
        project_id=project_id,
        provider=provider,
        api_key=api_key,
        base_url=base_url or None,
        model=model or None,
        temperature=float(temperature) if temperature else None,
        max_tokens=int(max_tokens) if max_tokens else None,
    )

    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)

@app.get("/slices/{slice_id}", response_class=HTMLResponse)
def slice_detail(slice_id: int, request: Request):
    u = _require_user(request)
    s, project = _slice_with_project(slice_id)
    _require_project_access(u["id"], project["id"])

    creator = fetchone("SELECT username FROM users WHERE id=?", (s["created_by_user_id"],))
    ac_list = fetchall("SELECT * FROM acceptance_criteria WHERE slice_id=? ORDER BY id ASC", (slice_id,))
    ctx = fetchone("SELECT * FROM context_packs WHERE slice_id=? ORDER BY version DESC LIMIT 1", (slice_id,))

    ctx_preview = ""
    ctx_user = None
    if ctx:
        content = json.loads(ctx["content_json"])
        ctx_preview = clamp_text(json.dumps(content, ensure_ascii=False, indent=2), 9000)
        ctx_user = fetchone("SELECT username FROM users WHERE id=?", (ctx["created_by_user_id"],))

    runs = fetchall("SELECT * FROM runs WHERE slice_id=? ORDER BY id DESC LIMIT 20", (slice_id,))
    r_user_map = {}
    for r in runs:
        ru = fetchone("SELECT username FROM users WHERE id=?", (r["created_by_user_id"],))
        r_user_map[r["id"]] = ru["username"] if ru else "?"

    gates = fetchall("SELECT * FROM gates WHERE slice_id=? ORDER BY id DESC LIMIT 20", (slice_id,))
    g_user_map = {}
    for g in gates:
        gu = fetchone("SELECT username FROM users WHERE id=?", (g["created_by_user_id"],))
        g_user_map[g["id"]] = gu["username"] if gu else "?"

    # ADSE tools data (only if ADSE is enabled)
    p2c_matrix = []
    audit_reports = []
    project_control = []
    control_summary = None
    adse_enabled = s.get("adse_enabled", 0)

    if adse_enabled:
        from .adse_tools import get_p2c_tracking_matrix, get_audit_reports, get_project_control_table, get_control_summary
        p2c_matrix = get_p2c_tracking_matrix(slice_id)
        audit_reports = get_audit_reports(slice_id, limit=5)
        project_control = get_project_control_table(slice_id)
        control_summary = get_control_summary(slice_id)

    return templates.TemplateResponse(
        "slice.html",
        _get_template_context(
            request,
            s=s,
            project=project,
            creator=creator,
            ac_list=ac_list,
            ctx=ctx,
            ctx_user=ctx_user,
            ctx_preview=ctx_preview,
            runs=runs,
            r_user_map=r_user_map,
            gates=gates,
            g_user_map=g_user_map,
            pr_number=s.get("pr_number"),
            pr_url=s.get("pr_url"),
            adse_enabled=adse_enabled,
            p2c_matrix=p2c_matrix,
            audit_reports=audit_reports,
            project_control=project_control,
            control_summary=control_summary,
        ),
    )

@app.post("/slices/{slice_id}/ac")
def add_ac(slice_id: int, request: Request, code: str = Form(...), text: str = Form(...), verification: str = Form(...)):
    u = _require_user(request)
    s, project = _slice_with_project(slice_id)
    _require_project_access(u["id"], project["id"])
    execute("INSERT INTO acceptance_criteria(slice_id, code, text, verification) VALUES(?,?,?,?)", (slice_id, code.strip(), text.strip(), verification.strip()))
    return RedirectResponse(url=f"/slices/{slice_id}", status_code=303)

def _load_slice_context(slice_id: int):
    s, project = _slice_with_project(slice_id)
    ac_list = [dict(r) for r in fetchall("SELECT * FROM acceptance_criteria WHERE slice_id=? ORDER BY id ASC", (slice_id,))]
    return s, project, ac_list

@app.post("/slices/{slice_id}/context-pack")
def gen_context_pack(slice_id: int, request: Request):
    u = _require_user(request)
    s, project, ac_list = _load_slice_context(slice_id)
    _require_project_access(u["id"], project["id"])

    def job():
        clone_or_update_project_repo(project["id"], project["repo_url"], project["default_branch"])
        run_id = execute(
            "INSERT INTO runs(slice_id, role, context_pack_id, status, worktree_path, started_at, ended_at, log, created_by_user_id) VALUES(?,?,?,?,?,?,?,?,?)",
            (slice_id, "context_pack", None, "running", "", now_iso(), None, "generating context pack", u["id"]),
        )
        wt = create_worktree(project["id"], s["branch_name"], project["default_branch"], run_id)
        execute("UPDATE runs SET worktree_path=? WHERE id=?", (str(wt), run_id))
        last = fetchone("SELECT * FROM context_packs WHERE slice_id=? ORDER BY version DESC LIMIT 1", (slice_id,))
        version = int(last["version"]) + 1 if last else 1
        pack = build_context_pack(wt, s, ac_list)
        ctx_id = execute(
            "INSERT INTO context_packs(slice_id, version, content_json, created_by_user_id, created_at) VALUES(?,?,?,?,?)",
            (slice_id, version, json.dumps(pack, ensure_ascii=False), u["id"], now_iso()),
        )
        execute("UPDATE runs SET status=?, ended_at=?, log=? WHERE id=?", ("success", now_iso(), f"context pack v{version} created (id={ctx_id})", run_id))
        execute("UPDATE slices SET status=? WHERE id=?", ("ContextReady", slice_id))

    submit(job)
    return RedirectResponse(url=f"/slices/{slice_id}", status_code=303)

@app.post("/slices/{slice_id}/run/{role}")
def run_role(slice_id: int, role: str, request: Request):
    u = _require_user(request)
    role = role.strip().lower()
    if role not in ROLE_RUNNERS:
        return HTMLResponse("Unknown role", status_code=400)

    s, project, ac_list = _load_slice_context(slice_id)
    _require_project_access(u["id"], project["id"])
    ctx = fetchone("SELECT * FROM context_packs WHERE slice_id=? ORDER BY version DESC LIMIT 1", (slice_id,))
    ctx_id = int(ctx["id"]) if ctx else None

    run_id = execute(
        "INSERT INTO runs(slice_id, role, context_pack_id, status, worktree_path, started_at, ended_at, log, created_by_user_id) VALUES(?,?,?,?,?,?,?,?,?)",
        (slice_id, role, ctx_id, "queued", "", now_iso(), None, "queued", u["id"]),
    )

    def job():
        try:
            execute("UPDATE runs SET status=? WHERE id=?", ("running", run_id))
            clone_or_update_project_repo(project["id"], project["repo_url"], project["default_branch"])
            wt = create_worktree(project["id"], s["branch_name"], project["default_branch"], run_id)
            execute("UPDATE runs SET worktree_path=? WHERE id=?", (str(wt), run_id))
            out = ROLE_RUNNERS[role](wt, s, ac_list, user_id=u["id"], project_id=project["id"])
            sha = commit_all(project["id"], wt, f"slice {slice_id}: {role} artifacts")

            # Get artifacts list for P2C tracking
            artifact_list = []
            for fp in out.changed_files:
                execute("INSERT INTO artifacts(slice_id, run_id, kind, path, git_sha, created_at) VALUES(?,?,?,?,?,?)", (slice_id, run_id, "file", fp, sha, now_iso()))
                artifact_list.append({"path": fp, "kind": "file", "sha": sha})

            # Update P2C tracking if ADSE is enabled
            if s.get("adse_enabled"):
                from .adse_tools import update_p2c_from_artifacts, run_semantic_audit
                update_p2c_from_artifacts(slice_id, artifact_list)
                # Run logic audit after Dev role completes
                if role == "dev":
                    try:
                        run_semantic_audit(slice_id, wt, run_id)
                    except Exception as audit_err:
                        # Don't fail the job if audit fails
                        pass

            execute("UPDATE runs SET status=?, ended_at=?, log=? WHERE id=?", ("success", now_iso(), f"{out.summary}\nchanged={out.changed_files}\nsha={sha}", run_id))
            next_status = {"pm":"PMDone","architect":"DesignDone","dev":"DevInProgress","qa":"QADone","ops":"OpsReady"}.get(role, "InProgress")
            execute("UPDATE slices SET status=? WHERE id=?", (next_status, slice_id))
        except Exception as e:
            execute("UPDATE runs SET status=?, ended_at=?, log=? WHERE id=?", ("failed", now_iso(), f"{type(e).__name__}: {e}", run_id))

    submit(job)
    return RedirectResponse(url=f"/slices/{slice_id}", status_code=303)

def _format_gates_comment(slice_id: int, results: list[tuple[str, str]]) -> str:
    lines = []
    lines.append(f"## Gates results for Slice {slice_id}")
    lines.append("")
    lines.append("| Gate | Status |")
    lines.append("|------|--------|")
    for name, status in results:
        icon = "✅" if status == "pass" else "❌"
        lines.append(f"| `{name}` | {icon} **{status}** |")
    lines.append("")
    lines.append("> Generated by Agent Dev Dashboard (Route-3)")
    return "\n".join(lines)

@app.post("/slices/{slice_id}/gates")
def run_slice_gates(slice_id: int, request: Request):
    u = _require_user(request)
    s, project, _ac_list = _load_slice_context(slice_id)
    _require_project_access(u["id"], project["id"])

    run_id = execute(
        "INSERT INTO runs(slice_id, role, context_pack_id, status, worktree_path, started_at, ended_at, log, created_by_user_id) VALUES(?,?,?,?,?,?,?,?,?)",
        (slice_id, "gates", None, "queued", "", now_iso(), None, "queued", u["id"]),
    )

    def job():
        try:
            execute("UPDATE runs SET status=? WHERE id=?", ("running", run_id))
            clone_or_update_project_repo(project["id"], project["repo_url"], project["default_branch"])
            wt = create_worktree(project["id"], s["branch_name"], project["default_branch"], run_id)
            execute("UPDATE runs SET worktree_path=? WHERE id=?", (str(wt), run_id))
            results = run_gates(wt)

            for r in results:
                execute(
                    "INSERT INTO gates(slice_id, run_id, name, status, output, ran_at, created_by_user_id) VALUES(?,?,?,?,?,?,?)",
                    (slice_id, run_id, r.name, r.status, r.output, now_iso(), u["id"]),
                )

            execute("UPDATE runs SET status=?, ended_at=?, log=? WHERE id=?", ("success", now_iso(), "gates finished", run_id))
            execute("UPDATE slices SET status=? WHERE id=?", ("CIPassed" if all(r.status == "pass" for r in results) else "CIFailed", slice_id))

            # Auto comment to PR if exists
            if s.get("pr_number") and project.get("github_owner") and project.get("github_repo"):
                body = _format_gates_comment(slice_id, [(r.name, r.status) for r in results])
                try:
                    comment_on_pr(project["github_owner"], project["github_repo"], int(s["pr_number"]), body)
                except Exception as ce:
                    execute("UPDATE runs SET log=? WHERE id=?", (f"gates finished; PR comment failed: {type(ce).__name__}: {ce}", run_id))
        except Exception as e:
            execute("UPDATE runs SET status=?, ended_at=?, log=? WHERE id=?", ("failed", now_iso(), f"{type(e).__name__}: {e}", run_id))

    submit(job)
    return RedirectResponse(url=f"/slices/{slice_id}", status_code=303)

@app.post("/slices/{slice_id}/push")
def push_slice_branch(slice_id: int, request: Request):
    u = _require_user(request)
    s, project, _ac_list = _load_slice_context(slice_id)
    _require_project_access(u["id"], project["id"])

    run_id = execute(
        "INSERT INTO runs(slice_id, role, context_pack_id, status, worktree_path, started_at, ended_at, log, created_by_user_id) VALUES(?,?,?,?,?,?,?,?,?)",
        (slice_id, "push", None, "queued", "", now_iso(), None, "queued", u["id"]),
    )

    def job():
        try:
            execute("UPDATE runs SET status=? WHERE id=?", ("running", run_id))
            clone_or_update_project_repo(project["id"], project["repo_url"], project["default_branch"])
            wt = create_worktree(project["id"], s["branch_name"], project["default_branch"], run_id)
            execute("UPDATE runs SET worktree_path=? WHERE id=?", (str(wt), run_id))
            out = push_branch(project["id"], wt, s["branch_name"])
            execute("UPDATE runs SET status=?, ended_at=?, log=? WHERE id=?", ("success", now_iso(), out, run_id))
        except Exception as e:
            execute("UPDATE runs SET status=?, ended_at=?, log=? WHERE id=?", ("failed", now_iso(), f"{type(e).__name__}: {e}", run_id))

    submit(job)
    return RedirectResponse(url=f"/slices/{slice_id}", status_code=303)

@app.post("/slices/{slice_id}/pr/create")
def create_or_update_pr(slice_id: int, request: Request):
    u = _require_user(request)
    s, project, _ac_list = _load_slice_context(slice_id)
    _require_project_access(u["id"], project["id"])

    run_id = execute(
        "INSERT INTO runs(slice_id, role, context_pack_id, status, worktree_path, started_at, ended_at, log, created_by_user_id) VALUES(?,?,?,?,?,?,?,?,?)",
        (slice_id, "pr", None, "queued", "", now_iso(), None, "queued", u["id"]),
    )

    def job():
        try:
            execute("UPDATE runs SET status=? WHERE id=?", ("running", run_id))
            if not project.get("github_owner") or not project.get("github_repo"):
                raise RuntimeError("Project repo_url is not a github.com URL (cannot parse owner/repo).")
            # push branch first
            clone_or_update_project_repo(project["id"], project["repo_url"], project["default_branch"])
            wt = create_worktree(project["id"], s["branch_name"], project["default_branch"], run_id)
            execute("UPDATE runs SET worktree_path=? WHERE id=?", (str(wt), run_id))
            push_branch(project["id"], wt, s["branch_name"])

            title = f"Slice {slice_id}: {s['title']}"
            body = f"Auto-created by Agent Dev Dashboard.\n\nBranch: `{s['branch_name']}`"
            pr = create_or_get_pr(project["github_owner"], project["github_repo"], title, s["branch_name"], project["default_branch"], body)
            pr_number = int(pr.get("number"))
            pr_url = pr.get("html_url")
            execute("UPDATE slices SET pr_number=?, pr_url=? WHERE id=?", (pr_number, pr_url, slice_id))
            execute("UPDATE runs SET status=?, ended_at=?, log=? WHERE id=?", ("success", now_iso(), f"PR ready: #{pr_number} {pr_url}", run_id))
        except Exception as e:
            execute("UPDATE runs SET status=?, ended_at=?, log=? WHERE id=?", ("failed", now_iso(), f"{type(e).__name__}: {e}", run_id))

    submit(job)
    return RedirectResponse(url=f"/slices/{slice_id}", status_code=303)

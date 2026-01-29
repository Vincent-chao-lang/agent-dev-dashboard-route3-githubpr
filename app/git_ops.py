from __future__ import annotations
import os, subprocess, shutil
from pathlib import Path
from typing import Optional

from .config import WORKSPACE_DIR
from .locks import file_lock

class GitError(RuntimeError):
    pass

def _run(cmd: list[str], cwd: Optional[Path] = None, timeout_sec: int = 600) -> str:
    p = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        timeout=timeout_sec,
    )
    out = p.stdout
    if p.returncode != 0:
        raise GitError(f"Command failed: {' '.join(cmd)}\n{out}")
    return out

def project_root(project_id: int) -> Path:
    return (WORKSPACE_DIR / f"project_{project_id}").resolve()

def project_repo_path(project_id: int) -> Path:
    return project_root(project_id) / "repo"

def worktrees_root(project_id: int) -> Path:
    return project_root(project_id) / "worktrees"

def project_lock_path(project_id: int) -> Path:
    return project_root(project_id) / ".gitops.lock"

def clone_or_update_project_repo(project_id: int, repo_url: str, default_branch: str) -> Path:
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    root = project_root(project_id)
    repo = project_repo_path(project_id)
    root.mkdir(parents=True, exist_ok=True)

    with file_lock(project_lock_path(project_id), timeout_sec=60):
        if (repo / ".git").exists():
            _run(["git", "fetch", "--all", "--prune"], cwd=repo, timeout_sec=300)
            _run(["git", "checkout", default_branch], cwd=repo, timeout_sec=120)
            _run(["git", "pull", "--ff-only"], cwd=repo, timeout_sec=300)
            return repo
        _run(["git", "clone", "--branch", default_branch, "--single-branch", repo_url, str(repo)], timeout_sec=600)
        return repo

def ensure_branch_from(repo: Path, branch: str, base_ref: str) -> None:
    try:
        _run(["git", "show-ref", "--verify", f"refs/heads/{branch}"], cwd=repo, timeout_sec=60)
    except GitError:
        _run(["git", "branch", branch, base_ref], cwd=repo, timeout_sec=60)

def create_worktree(project_id: int, branch: str, base_ref: str, run_id: int) -> Path:
    repo = project_repo_path(project_id)
    wt_root = worktrees_root(project_id)
    wt_root.mkdir(parents=True, exist_ok=True)
    wt_path = (wt_root / f"run_{run_id}_{branch.replace('/', '_')}").resolve()

    with file_lock(project_lock_path(project_id), timeout_sec=120):
        _run(["git", "fetch", "--all", "--prune"], cwd=repo, timeout_sec=300)
        ensure_branch_from(repo, branch, base_ref)
        if wt_path.exists():
            try:
                _run(["git", "worktree", "remove", "--force", str(wt_path)], cwd=repo, timeout_sec=120)
            except Exception:
                pass
            shutil.rmtree(wt_path, ignore_errors=True)
        _run(["git", "worktree", "add", str(wt_path), branch], cwd=repo, timeout_sec=180)
    return wt_path

def current_sha(repo_or_wt: Path) -> str:
    return _run(["git", "rev-parse", "HEAD"], cwd=repo_or_wt, timeout_sec=60).strip()

def status_porcelain(repo_or_wt: Path) -> str:
    return _run(["git", "status", "--porcelain"], cwd=repo_or_wt, timeout_sec=60)

def commit_all(project_id: int, repo_or_wt: Path, message: str) -> str:
    if not status_porcelain(repo_or_wt).strip():
        return current_sha(repo_or_wt)
    with file_lock(project_lock_path(project_id), timeout_sec=120):
        _run(["git", "add", "-A"], cwd=repo_or_wt, timeout_sec=120)
        _run(["git", "commit", "-m", message], cwd=repo_or_wt, timeout_sec=120)
        return current_sha(repo_or_wt)

def push_branch(project_id: int, repo_or_wt: Path, branch: str) -> str:
    with file_lock(project_lock_path(project_id), timeout_sec=180):
        return _run(["git", "push", "-u", "origin", branch], cwd=repo_or_wt, timeout_sec=300)

def write_file(repo_or_wt: Path, rel_path: str, content: str) -> None:
    p = (repo_or_wt / rel_path).resolve()
    root = repo_or_wt.resolve()
    if root not in p.parents and p != root:
        raise GitError("Illegal path write (escape detected).")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")

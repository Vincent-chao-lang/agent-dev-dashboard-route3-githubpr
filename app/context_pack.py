from __future__ import annotations
import os, subprocess
from pathlib import Path
from typing import Any

from .utils import clamp_text, safe_relpath

DEFAULT_ALWAYS_FILES = [
    "docs/CHARTER.md",
    "docs/PRD.md",
    "docs/ACCEPTANCE.md",
    "docs/DESIGN.md",
    "docs/TEST_STRATEGY.md",
    "contracts/openapi.yaml",
    "Makefile",
]

def _run(cmd: list[str], cwd: Path) -> str:
    p = subprocess.run(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    )
    return p.stdout

def _excerpt_file(path: Path, max_lines: int = 200) -> str:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(lines[:max_lines])
    except Exception as e:
        return f"<failed to read {path}: {e}>"

def build_context_pack(worktree_path: Path, slice_obj: dict[str, Any], ac_list: list[dict[str, Any]]) -> dict[str, Any]:
    files: list[Path] = []
    for f in DEFAULT_ALWAYS_FILES:
        p = worktree_path / f
        if p.exists() and p.is_file():
            files.append(p)

    git_log = _run(["git", "log", "-n", "20", "--oneline"], cwd=worktree_path)

    file_entries = []
    for p in files[:20]:
        rel = safe_relpath(p, worktree_path)
        file_entries.append({"path": rel, "excerpt": clamp_text(_excerpt_file(p), 7000)})

    return {
        "slice": {
            "id": slice_obj["id"],
            "title": slice_obj["title"],
            "scope": slice_obj["scope"],
            "out_of_scope": slice_obj["out_of_scope"],
            "risk_level": slice_obj["risk_level"],
            "status": slice_obj["status"],
            "branch_name": slice_obj["branch_name"],
        },
        "acceptance_criteria": [{"code": a["code"], "text": a["text"], "verification": a["verification"]} for a in ac_list],
        "repo": {"worktree_path": str(worktree_path), "git_log": clamp_text(git_log, 9000)},
        "files": file_entries,
        "suggested_commands": ["make lint", "make type", "make contract", "make test"],
    }

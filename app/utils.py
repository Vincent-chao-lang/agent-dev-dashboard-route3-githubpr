from __future__ import annotations
from datetime import datetime, timezone
import re
from pathlib import Path
from typing import Iterable

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9\-\s_]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-{2,}", "-", s)
    return s[:60] or "item"

def clamp_text(s: str, max_chars: int = 8000) -> str:
    if len(s) <= max_chars:
        return s
    return s[:max_chars] + "\n...<truncated>..."

def safe_relpath(path: Path, root: Path) -> str:
    return str(path.resolve().relative_to(root.resolve()))

def within_prefix(rel_path: str, allowed_prefixes: Iterable[str]) -> bool:
    rp = rel_path.replace('\\', '/')
    return any(rp.startswith(p) for p in allowed_prefixes)

def branch_name_for_slice(slice_id: int, title: str) -> str:
    return f"slice/{slice_id:04d}-{slugify(title)}"

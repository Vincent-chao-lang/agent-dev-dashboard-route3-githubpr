from __future__ import annotations
from pathlib import Path

def upsert_block(path: Path, start_marker: str, end_marker: str, block: str) -> None:
    content = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    start = content.find(start_marker)
    end = content.find(end_marker)
    if start != -1 and end != -1 and end > start:
        new_content = content[:start] + start_marker + "\n" + block.rstrip() + "\n" + end_marker + content[end+len(end_marker):]
    else:
        sep = "" if content.endswith("\n") or content == "" else "\n"
        new_content = content + sep + start_marker + "\n" + block.rstrip() + "\n" + end_marker + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new_content, encoding="utf-8")

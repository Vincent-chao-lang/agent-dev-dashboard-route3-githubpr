from __future__ import annotations
import os, subprocess
from pathlib import Path
from dataclasses import dataclass

from .utils import clamp_text

@dataclass
class GateResult:
    name: str
    status: str
    output: str

def _run(cmd: list[str], cwd: Path, timeout_sec: int = 1800) -> tuple[int, str]:
    p = subprocess.run(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        timeout=timeout_sec,
    )
    return p.returncode, p.stdout

DEFAULT_GATES = [
    ("lint", ["make", "lint"]),
    ("type", ["make", "type"]),
    ("contract", ["make", "contract"]),
    ("test", ["make", "test"]),
]

def run_gates(worktree_path: Path) -> list[GateResult]:
    res = []
    for name, cmd in DEFAULT_GATES:
        try:
            code, out = _run(cmd, cwd=worktree_path)
            res.append(GateResult(name, "pass" if code == 0 else "fail", clamp_text(out, 15000)))
        except Exception as e:
            res.append(GateResult(name, "fail", clamp_text(str(e), 15000)))
    return res

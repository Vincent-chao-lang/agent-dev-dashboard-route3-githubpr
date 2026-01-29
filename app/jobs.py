from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Any
from .config import MAX_WORKERS

_executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

def submit(fn: Callable[[], Any]) -> None:
    _executor.submit(fn)

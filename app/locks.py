from __future__ import annotations
import os, time
from pathlib import Path
from contextlib import contextmanager

class LockTimeout(RuntimeError):
    pass

@contextmanager
def file_lock(lock_path: Path, timeout_sec: int = 30, poll_sec: float = 0.2):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    start = time.time()
    fd = None
    while True:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
            os.write(fd, str(os.getpid()).encode("utf-8"))
            break
        except FileExistsError:
            if time.time() - start > timeout_sec:
                raise LockTimeout(f"Timed out acquiring lock: {lock_path}")
            time.sleep(poll_sec)
    try:
        yield
    finally:
        try:
            if fd is not None:
                os.close(fd)
            lock_path.unlink(missing_ok=True)
        except Exception:
            pass

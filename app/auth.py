from __future__ import annotations
import hashlib
import hmac
import os
from typing import Optional

from fastapi import Request
from .db import fetchone, execute
from .utils import now_iso

PBKDF2_ITERS = 120_000

def make_password_hash(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERS, dklen=32)
    return f"pbkdf2_sha256${PBKDF2_ITERS}${salt.hex()}${digest.hex()}"

def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters_s, salt_hex, digest_hex = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iters = int(iters_s)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        got = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iters, dklen=len(expected))
        return hmac.compare_digest(got, expected)
    except Exception:
        return False

def get_current_user(request: Request) -> Optional[dict]:
    uid = request.session.get("user_id")
    if not uid:
        return None
    row = fetchone("SELECT id, username FROM users WHERE id=?", (uid,))
    return dict(row) if row else None

def create_user(username: str, password: str) -> int:
    return execute(
        "INSERT INTO users(username, password_hash, created_at) VALUES(?,?,?)",
        (username, make_password_hash(password), now_iso()),
    )

def authenticate(username: str, password: str) -> Optional[dict]:
    row = fetchone("SELECT * FROM users WHERE username=?", (username,))
    if not row:
        return None
    if not verify_password(password, row["password_hash"]):
        return None
    return {"id": row["id"], "username": row["username"]}

def has_any_users() -> bool:
    row = fetchone("SELECT COUNT(*) AS c FROM users")
    return bool(row and row["c"] > 0)

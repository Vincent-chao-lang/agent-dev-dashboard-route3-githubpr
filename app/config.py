from __future__ import annotations
import os
from pathlib import Path

APP_DB_PATH = Path(os.getenv("APP_DB_PATH", "./dashboard.sqlite")).resolve()
WORKSPACE_DIR = Path(os.getenv("WORKSPACE_DIR", "./workspace")).resolve()

SESSION_SECRET = os.getenv("SESSION_SECRET", "dev-insecure-secret-change-me")

# LLM Configuration - GLM-4.7
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "glm")  # glm, openai, etc.
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")
LLM_MODEL = os.getenv("LLM_MODEL", "glm-4-plus")  # GLM-4.7 (glm-4-plus)
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "4096"))

ROLE_ALLOWED_PREFIXES = {
    "pm": ["docs/", "tasks/"],
    "architect": ["docs/", "contracts/"],
    "dev": ["src/", "tests/unit/", "reports/"],
    "qa": ["tests/", "docker/", "reports/"],
    "ops": ["docs/", "reports/"],
}

MAX_WORKERS = int(os.getenv("MAX_WORKERS", "4"))

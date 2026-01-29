"""
LLM Configuration Management Module

Supports hierarchical LLM configuration with priority:
1. User-level configuration (highest priority)
2. Project-level configuration
3. Global default configuration (.env file)

This allows flexible cost allocation and configuration management.
"""
from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Any, Optional

from .db import fetchone, fetchall, execute
from .config import (
    LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS
)
from .utils import now_iso


@dataclass
class LLMConfig:
    """LLM configuration data class."""
    provider: str
    api_key: str
    base_url: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    source: str = "global"  # global, user, project

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, excluding sensitive fields."""
        return {
            "provider": self.provider,
            "base_url": self.base_url,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "source": self.source,
        }


def get_global_config() -> LLMConfig:
    """
    Get global default LLM configuration from environment variables.

    Returns:
        LLMConfig with global defaults
    """
    return LLMConfig(
        provider=os.getenv("LLM_PROVIDER", "glm"),
        api_key=LLM_API_KEY or "",
        base_url=LLM_BASE_URL,
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_TOKENS,
        source="global",
    )


def get_user_config(user_id: int, provider: str = "glm") -> Optional[LLMConfig]:
    """
    Get user-level LLM configuration.

    Args:
        user_id: User ID
        provider: LLM provider (default: "glm")

    Returns:
        LLMConfig if found, None otherwise
    """
    config = fetchone(
        """SELECT * FROM user_llm_configs
           WHERE user_id = ? AND provider = ?""",
        (user_id, provider)
    )

    if not config:
        return None

    return LLMConfig(
        provider=config["provider"],
        api_key=config["api_key"],
        base_url=config.get("base_url"),
        model=config.get("model"),
        temperature=config.get("temperature"),
        max_tokens=config.get("max_tokens"),
        source="user",
    )


def get_project_config(project_id: int, provider: str = "glm") -> Optional[LLMConfig]:
    """
    Get project-level LLM configuration.

    Args:
        project_id: Project ID
        provider: LLM provider (default: "glm")

    Returns:
        LLMConfig if found, None otherwise
    """
    config = fetchone(
        """SELECT * FROM project_llm_configs
           WHERE project_id = ? AND provider = ?""",
        (project_id, provider)
    )

    if not config:
        return None

    return LLMConfig(
        provider=config["provider"],
        api_key=config["api_key"],
        base_url=config.get("base_url"),
        model=config.get("model"),
        temperature=config.get("temperature"),
        max_tokens=config.get("max_tokens"),
        source="project",
    )


def get_effective_config(
    user_id: Optional[int] = None,
    project_id: Optional[int] = None,
    provider: str = "glm",
) -> LLMConfig:
    """
    Get effective LLM configuration with priority:
    1. User-level configuration (highest priority)
    2. Project-level configuration
    3. Global default configuration

    Args:
        user_id: User ID (optional)
        project_id: Project ID (optional)
        provider: LLM provider (default: "glm")

    Returns:
        Effective LLMConfig
    """
    # Priority 1: User-level configuration
    if user_id:
        user_config = get_user_config(user_id, provider)
        if user_config and user_config.api_key:
            return user_config

    # Priority 2: Project-level configuration
    if project_id:
        project_config = get_project_config(project_id, provider)
        if project_config and project_config.api_key:
            return project_config

    # Priority 3: Global default configuration
    return get_global_config()


def set_user_config(
    user_id: int,
    provider: str,
    api_key: str,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> int:
    """
    Set or update user-level LLM configuration.

    Args:
        user_id: User ID
        provider: LLM provider
        api_key: API key
        base_url: API base URL (optional)
        model: Model name (optional)
        temperature: Temperature (optional)
        max_tokens: Max tokens (optional)

    Returns:
        Configuration ID
    """
    existing = fetchone(
        "SELECT id FROM user_llm_configs WHERE user_id = ? AND provider = ?",
        (user_id, provider)
    )

    now = now_iso()

    if existing:
        execute(
            """UPDATE user_llm_configs
               SET api_key = ?, base_url = ?, model = ?, temperature = ?, max_tokens = ?, updated_at = ?
               WHERE id = ?""",
            (api_key, base_url, model, temperature, max_tokens, now, existing["id"])
        )
        return int(existing["id"])
    else:
        return execute(
            """INSERT INTO user_llm_configs (user_id, provider, api_key, base_url, model, temperature, max_tokens, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, provider, api_key, base_url, model, temperature, max_tokens, now, now)
        )


def set_project_config(
    project_id: int,
    provider: str,
    api_key: str,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> int:
    """
    Set or update project-level LLM configuration.

    Args:
        project_id: Project ID
        provider: LLM provider
        api_key: API key
        base_url: API base URL (optional)
        model: Model name (optional)
        temperature: Temperature (optional)
        max_tokens: Max tokens (optional)

    Returns:
        Configuration ID
    """
    existing = fetchone(
        "SELECT id FROM project_llm_configs WHERE project_id = ? AND provider = ?",
        (project_id, provider)
    )

    now = now_iso()

    if existing:
        execute(
            """UPDATE project_llm_configs
               SET api_key = ?, base_url = ?, model = ?, temperature = ?, max_tokens = ?, updated_at = ?
               WHERE id = ?""",
            (api_key, base_url, model, temperature, max_tokens, now, existing["id"])
        )
        return int(existing["id"])
    else:
        return execute(
            """INSERT INTO project_llm_configs (project_id, provider, api_key, base_url, model, temperature, max_tokens, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (project_id, provider, api_key, base_url, model, temperature, max_tokens, now, now)
        )


def delete_user_config(user_id: int, provider: str = "glm") -> bool:
    """
    Delete user-level LLM configuration.

    Args:
        user_id: User ID
        provider: LLM provider

    Returns:
        True if deleted, False otherwise
    """
    rows = execute(
        "DELETE FROM user_llm_configs WHERE user_id = ? AND provider = ?",
        (user_id, provider)
    )
    return rows > 0


def delete_project_config(project_id: int, provider: str = "glm") -> bool:
    """
    Delete project-level LLM configuration.

    Args:
        project_id: Project ID
        provider: LLM provider

    Returns:
        True if deleted, False otherwise
    """
    rows = execute(
        "DELETE FROM project_llm_configs WHERE project_id = ? AND provider = ?",
        (project_id, provider)
    )
    return rows > 0


def get_all_user_configs(user_id: int) -> list[dict]:
    """
    Get all LLM configurations for a user.

    Args:
        user_id: User ID

    Returns:
        List of configuration dictionaries (without API keys)
    """
    configs = fetchall(
        """SELECT provider, base_url, model, temperature, max_tokens, created_at, updated_at
           FROM user_llm_configs WHERE user_id = ?""",
        (user_id,)
    )
    return [dict(c) for c in configs]


def get_all_project_configs(project_id: int) -> list[dict]:
    """
    Get all LLM configurations for a project.

    Args:
        project_id: Project ID

    Returns:
        List of configuration dictionaries (without API keys)
    """
    configs = fetchall(
        """SELECT provider, base_url, model, temperature, max_tokens, created_at, updated_at
           FROM project_llm_configs WHERE project_id = ?""",
        (project_id,)
    )
    return [dict(c) for c in configs]


def mask_api_key(api_key: str) -> str:
    """
    Mask API key for display.

    Args:
        api_key: API key to mask

    Returns:
        Masked API key (e.g., "sk-***xyz")
    """
    if not api_key or len(api_key) < 8:
        return "***"
    return f"{api_key[:4]}...{api_key[-4:]}"

"""
LLM Client Module for GLM-4.7 Integration

Supports GLM-4.7 (Zhipu AI) via OpenAI-compatible API.
Supports hierarchical configuration:
    1. User-level configuration
    2. Project-level configuration
    3. Global default configuration (.env file)
"""
from __future__ import annotations
import os
from typing import Any, Optional
from dataclasses import dataclass

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from .config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS
from .llm_config import LLMConfig, get_effective_config


@dataclass
class LLMMessage:
    """LLM message structure."""
    role: str  # system, user, assistant
    content: str


@dataclass
class LLMResponse:
    """LLM response structure."""
    content: str
    model: str
    tokens_used: Optional[int] = None
    error: Optional[str] = None


class LLMClient:
    """
    LLM Client for GLM-4.7 integration.

    Uses OpenAI-compatible API to support GLM-4.7 (glm-4-plus) from Zhipu AI.
    Supports hierarchical configuration (user > project > global).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        """
        Initialize LLM client.

        Args:
            api_key: API key (defaults to LLM_API_KEY env var)
            base_url: API base URL (defaults to LLM_BASE_URL env var)
            model: Model name (defaults to LLM_MODEL env var)
            temperature: Sampling temperature (defaults to LLM_TEMPERATURE env var)
            max_tokens: Max tokens in response (defaults to LLM_MAX_TOKENS env var)
        """
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "OpenAI package is required. Install it with: pip install openai"
            )

        self.api_key = api_key or LLM_API_KEY
        self.base_url = base_url or LLM_BASE_URL
        self.model = model or LLM_MODEL
        self.temperature = temperature if temperature is not None else LLM_TEMPERATURE
        self.max_tokens = max_tokens if max_tokens is not None else LLM_MAX_TOKENS

        if not self.api_key:
            raise ValueError(
                "LLM_API_KEY is required. Set it as environment variable or pass it to the constructor."
            )

        # Initialize OpenAI client with custom base_url for GLM compatibility
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    @classmethod
    def from_config(cls, config: LLMConfig) -> "LLMClient":
        """
        Create LLM client from LLMConfig object.

        Args:
            config: LLMConfig object

        Returns:
            LLMClient instance
        """
        return cls(
            api_key=config.api_key,
            base_url=config.base_url,
            model=config.model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    def chat(
        self,
        messages: list[LLMMessage] | list[dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Send chat completion request to LLM.

        Args:
            messages: List of message objects with 'role' and 'content' keys
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            **kwargs: Additional parameters to pass to the API

        Returns:
            LLMResponse with content and metadata
        """
        # Convert LLMMessage objects to dicts if needed
        formatted_messages = []
        for msg in messages:
            if isinstance(msg, LLMMessage):
                formatted_messages.append({"role": msg.role, "content": msg.content})
            else:
                formatted_messages.append(msg)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=formatted_messages,
                temperature=temperature if temperature is not None else self.temperature,
                max_tokens=max_tokens if max_tokens is not None else self.max_tokens,
                **kwargs,
            )

            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else None

            return LLMResponse(
                content=content,
                model=response.model,
                tokens_used=tokens_used,
            )

        except Exception as e:
            return LLMResponse(
                content="",
                model=self.model,
                error=str(e),
            )

    def chat_simple(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Simplified chat interface with system and user prompts.

        Args:
            system_prompt: System message setting up the context
            user_prompt: User message with the actual task
            temperature: Override default temperature
            max_tokens: Override default max_tokens

        Returns:
            LLMResponse with content and metadata
        """
        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]
        return self.chat(messages, temperature=temperature, max_tokens=max_tokens)


# Singleton instance for convenience
_global_client: Optional[LLMClient] = None


def get_llm_client(
    user_id: Optional[int] = None,
    project_id: Optional[int] = None,
    provider: str = "glm",
) -> LLMClient:
    """
    Get LLM client with hierarchical configuration:
    1. User-level configuration (highest priority)
    2. Project-level configuration
    3. Global default configuration

    Args:
        user_id: User ID (optional)
        project_id: Project ID (optional)
        provider: LLM provider (default: "glm")

    Returns:
        LLMClient instance
    """
    config = get_effective_config(user_id, project_id, provider)
    return LLMClient.from_config(config)


def reset_llm_client() -> None:
    """Reset global LLM client instance (useful for testing)."""
    global _global_client
    _global_client = None

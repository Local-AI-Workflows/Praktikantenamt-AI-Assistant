"""
Anthropic API client implementing the BaseClient interface.
"""

import os
import time
from typing import Tuple

from prompt_tester.clients.base import BaseClient


class AnthropicClient(BaseClient):
    """Client for Anthropic Messages API."""

    def __init__(
        self,
        model: str = "claude-haiku-4-5",
        api_key: str = None,
        max_tokens: int = 50,
    ):
        """
        Initialize Anthropic client.

        Args:
            model: Anthropic model ID (e.g. 'claude-haiku-4-5', 'claude-haiku-4-5-20251001')
            api_key: API key. If None, reads from ANTHROPIC_API_KEY env var.
            max_tokens: Max tokens in the completion
        """
        try:
            import anthropic as sdk
        except ImportError:
            raise ImportError(
                "anthropic package not installed. Run: pip install anthropic>=0.28.0"
            )

        self._model = model
        self._max_tokens = max_tokens
        self._client = sdk.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def provider(self) -> str:
        return "anthropic"

    def generate(self, system_prompt: str, user_prompt: str) -> Tuple[str, float]:
        """
        Generate completion via Anthropic Messages API.

        Note: Anthropic uses `system` as a top-level parameter, not a role in messages.

        Args:
            system_prompt: System context prompt
            user_prompt: User message

        Returns:
            Tuple of (response text, elapsed seconds)
        """
        start = time.time()
        message = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        elapsed = time.time() - start
        return message.content[0].text, elapsed

    def health_check(self) -> bool:
        """
        Check if the API key is configured.

        Returns:
            True if ANTHROPIC_API_KEY is set (does not make a network call)
        """
        return bool(os.environ.get("ANTHROPIC_API_KEY") or self._client.api_key)

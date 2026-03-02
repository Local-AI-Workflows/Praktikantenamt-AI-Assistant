"""
OpenAI API client implementing the BaseClient interface.
"""

import os
import time
from typing import Tuple

from prompt_tester.clients.base import BaseClient


class OpenAIClient(BaseClient):
    """Client for OpenAI Chat Completions API."""

    def __init__(
        self,
        model: str = "gpt-4.1-mini",
        api_key: str = None,
        max_tokens: int = 50,
        temperature: float = 0.0,
    ):
        """
        Initialize OpenAI client.

        Args:
            model: OpenAI model ID (e.g. 'gpt-4.1-mini', 'gpt-4o')
            api_key: API key. If None, reads from OPENAI_API_KEY env var.
            max_tokens: Max tokens in the completion (50 is enough for category names)
            temperature: Sampling temperature (0.0 = deterministic)
        """
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai package not installed. Run: pip install openai>=1.30.0"
            )

        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def provider(self) -> str:
        return "openai"

    def generate(self, system_prompt: str, user_prompt: str) -> Tuple[str, float]:
        """
        Generate completion via OpenAI Chat Completions API.

        Args:
            system_prompt: System message content
            user_prompt: User message content

        Returns:
            Tuple of (response text, elapsed seconds)
        """
        start = time.time()
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=self._max_tokens,
            temperature=self._temperature,
        )
        elapsed = time.time() - start
        content = response.choices[0].message.content or ""
        return content, elapsed

    def health_check(self) -> bool:
        """
        Check if the API key is configured.

        Returns:
            True if OPENAI_API_KEY is set (does not make a network call)
        """
        return bool(os.environ.get("OPENAI_API_KEY") or self._client.api_key)

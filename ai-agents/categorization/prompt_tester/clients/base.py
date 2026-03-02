"""
Abstract base class for all LLM backend clients.
"""

from abc import ABC, abstractmethod
from typing import Tuple


class BaseClient(ABC):
    """Abstract interface for all LLM backends (Ollama, OpenAI, Anthropic, etc.)."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Canonical model identifier, e.g. 'llama3.1:8b' or 'gpt-4.1-mini'."""
        ...

    @property
    @abstractmethod
    def provider(self) -> str:
        """Provider string: 'ollama', 'openai', or 'anthropic'."""
        ...

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> Tuple[str, float]:
        """
        Generate a completion.

        Args:
            system_prompt: System context / instruction prompt
            user_prompt: User message / input prompt

        Returns:
            Tuple of (raw_response_text, wall_clock_seconds)
        """
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """
        Check whether the backend is reachable / configured.

        Returns:
            True if the backend is ready to accept requests.
        """
        ...

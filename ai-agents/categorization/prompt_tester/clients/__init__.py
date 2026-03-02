"""
Client implementations for the prompt testing benchmark runner.
"""

from prompt_tester.clients.base import BaseClient
from prompt_tester.clients.openai_client import OpenAIClient
from prompt_tester.clients.anthropic_client import AnthropicClient

# OllamaClient lives in prompt_tester.core.executor (inherits BaseClient there)
# Re-exported here for convenience
from prompt_tester.core.executor import OllamaClient

__all__ = [
    "BaseClient",
    "OllamaClient",
    "OpenAIClient",
    "AnthropicClient",
]

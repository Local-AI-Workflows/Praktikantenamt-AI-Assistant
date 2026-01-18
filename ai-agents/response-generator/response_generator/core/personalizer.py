"""
LLM-based personalization using Ollama API.
"""

import time
from pathlib import Path
from typing import Optional, Tuple

import requests

from response_generator.data.schemas import CategorizedEmail, Config, ResponseTone


class OllamaClient:
    """HTTP-based client for Ollama API."""

    def __init__(
        self,
        endpoint: str,
        model: str,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """
        Initialize Ollama client.

        Args:
            endpoint: Ollama API endpoint URL
            model: Model name to use
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries

    def generate(self, system_prompt: str, user_prompt: str) -> Tuple[str, float]:
        """
        Generate completion from Ollama API.

        Args:
            system_prompt: System prompt text
            user_prompt: User prompt text

        Returns:
            Tuple of (response text, execution time in seconds)

        Raises:
            ConnectionError: If cannot connect to Ollama
            requests.HTTPError: If API returns error
        """
        url = f"{self.endpoint}/api/generate"
        payload = {
            "model": self.model,
            "prompt": user_prompt,
            "system": system_prompt,
            "stream": False,
        }

        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                response = requests.post(url, json=payload, timeout=self.timeout)
                execution_time = time.time() - start_time

                response.raise_for_status()
                result = response.json()

                return result.get("response", ""), execution_time

            except requests.exceptions.ConnectionError as e:
                if attempt == self.max_retries - 1:
                    raise ConnectionError(
                        f"Cannot connect to Ollama at {self.endpoint}. "
                        f"Please ensure Ollama is running."
                    ) from e
                # Wait before retry with exponential backoff
                time.sleep(2**attempt)

            except requests.exceptions.Timeout as e:
                if attempt == self.max_retries - 1:
                    raise TimeoutError(
                        f"Request to Ollama timed out after {self.timeout} seconds"
                    ) from e
                time.sleep(2**attempt)

            except requests.exceptions.HTTPError as e:
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(2**attempt)

        raise RuntimeError("Max retries exceeded")

    def health_check(self) -> bool:
        """
        Check if Ollama is reachable.

        Returns:
            True if Ollama is accessible, False otherwise
        """
        try:
            response = requests.get(f"{self.endpoint}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False


class Personalizer:
    """Generates personalized content for email responses using LLM."""

    def __init__(
        self,
        ollama_client: OllamaClient,
        system_prompt_path: str,
        user_prompt_template_path: str,
        config: Optional[Config] = None,
    ):
        """
        Initialize personalizer.

        Args:
            ollama_client: Configured OllamaClient instance
            system_prompt_path: Path to system prompt file
            user_prompt_template_path: Path to user prompt template file
            config: Optional configuration
        """
        self.client = ollama_client
        self.config = config or Config()
        self.system_prompt = self._load_prompt(system_prompt_path)
        self.user_prompt_template = self._load_prompt(user_prompt_template_path)

    def _load_prompt(self, file_path: str) -> str:
        """Load prompt from file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Prompt file not found: {file_path}")

        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def personalize(
        self, email: CategorizedEmail, tone: ResponseTone
    ) -> Tuple[str, str]:
        """
        Generate personalized content for an email response.

        Args:
            email: Email to respond to
            tone: Desired tone of the response

        Returns:
            Tuple of (personalized content, raw LLM output)
        """
        # Format user prompt with email data
        user_prompt = self.user_prompt_template.format(
            subject=email.subject,
            sender=email.sender,
            category=email.category.value,
            body=email.body,
            tone=tone.value,
        )

        # Call Ollama API
        raw_response, _ = self.client.generate(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
        )

        # Clean up response
        personalized_content = self._clean_response(raw_response)

        return personalized_content, raw_response

    def _clean_response(self, response: str) -> str:
        """
        Clean LLM response to extract just the personalized paragraph.

        Args:
            response: Raw LLM response

        Returns:
            Cleaned personalized content
        """
        # Remove common prefixes the LLM might add
        prefixes_to_remove = [
            "Hier ist der personalisierte Absatz:",
            "Der personalisierte Absatz:",
            "Personalisierter Absatz:",
            "Here is the personalized paragraph:",
        ]

        cleaned = response.strip()

        for prefix in prefixes_to_remove:
            if cleaned.lower().startswith(prefix.lower()):
                cleaned = cleaned[len(prefix) :].strip()

        # Remove quotes if the response is wrapped in them
        if cleaned.startswith('"') and cleaned.endswith('"'):
            cleaned = cleaned[1:-1]

        return cleaned.strip()


def create_personalizer_from_config(config: Config) -> Optional[Personalizer]:
    """
    Create a Personalizer instance from configuration.

    Args:
        config: Configuration object

    Returns:
        Personalizer instance or None if personalization is disabled
    """
    if not config.personalization_enabled:
        return None

    # Determine prompt paths
    prompts_dir = Path(config.prompts_directory)
    system_prompt_path = prompts_dir / "system_prompt.txt"
    user_prompt_path = prompts_dir / "personalization_v1.txt"

    # Check if prompts exist
    if not system_prompt_path.exists() or not user_prompt_path.exists():
        return None

    # Create OllamaClient
    ollama_client = OllamaClient(
        endpoint=config.ollama_endpoint,
        model=config.ollama_model,
        timeout=config.ollama_timeout,
        max_retries=config.ollama_max_retries,
    )

    return Personalizer(
        ollama_client=ollama_client,
        system_prompt_path=str(system_prompt_path),
        user_prompt_template_path=str(user_prompt_path),
        config=config,
    )

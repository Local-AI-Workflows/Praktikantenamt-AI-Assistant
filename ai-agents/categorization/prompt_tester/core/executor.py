"""
Ollama API client and prompt execution orchestration.
"""

import re
import time
from datetime import datetime
from typing import List, Tuple

import requests

from prompt_tester.data.schemas import Email, PromptConfig, Result


class OllamaClient:
    """HTTP-based client for Ollama API."""

    def __init__(self, endpoint: str, model: str, timeout: int = 30, max_retries: int = 3):
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
                time.sleep(2 ** attempt)

            except requests.exceptions.Timeout as e:
                if attempt == self.max_retries - 1:
                    raise TimeoutError(
                        f"Request to Ollama timed out after {self.timeout} seconds"
                    ) from e
                time.sleep(2 ** attempt)

            except requests.exceptions.HTTPError as e:
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(2 ** attempt)

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


class PromptExecutor:
    """Orchestrates prompt execution over email datasets."""

    def __init__(self, ollama_client: OllamaClient):
        """
        Initialize prompt executor.

        Args:
            ollama_client: Configured OllamaClient instance
        """
        self.client = ollama_client

    def execute_batch(
        self, emails: List[Email], prompt_config: PromptConfig
    ) -> List[Result]:
        """
        Execute prompt on a batch of emails.

        Args:
            emails: List of emails to categorize
            prompt_config: Prompt configuration to use

        Returns:
            List of Result objects
        """
        results = []

        for email in emails:
            result = self.execute_single(email, prompt_config)
            results.append(result)

        return results

    def execute_single(self, email: Email, prompt_config: PromptConfig) -> Result:
        """
        Execute prompt on a single email.

        Args:
            email: Email to categorize
            prompt_config: Prompt configuration to use

        Returns:
            Result object with prediction and metadata
        """
        # Format user prompt with email data
        user_prompt = prompt_config.user_prompt_template.format(
            subject=email.subject,
            sender=email.sender,
            has_attachment=email.has_attachment,
            body=email.body,
        )

        # Call Ollama API
        raw_response, execution_time = self.client.generate(
            system_prompt=prompt_config.system_prompt,
            user_prompt=user_prompt,
        )

        # Extract category from response
        predicted_category = self._parse_category(raw_response)

        # Create result object
        return Result(
            email_id=email.id,
            predicted_category=predicted_category,
            expected_category=email.expected_category,
            raw_response=raw_response.strip(),
            execution_time=execution_time,
            timestamp=datetime.now(),
        )

    def _parse_category(self, response: str) -> str:
        """
        Parse category from LLM response.

        Supports multiple response formats:
        - Plain category name
        - "Category: <category>"
        - JSON with category field
        - Categories in quotes or backticks

        Args:
            response: Raw LLM response

        Returns:
            Extracted category name or "parse_error" if cannot parse
        """
        response = response.strip()

        # List of valid categories (hardcoded for robustness)
        valid_categories = [
            "contract_submission",
            "international_office_question",
            "internship_postponement",
            "uncategorized",
        ]

        # Try to find exact category match (case-insensitive)
        response_lower = response.lower()
        for category in valid_categories:
            if category.lower() in response_lower:
                return category

        # Try to extract from "Category: <value>" pattern
        category_pattern = r"category:\s*([a-z_]+)"
        match = re.search(category_pattern, response_lower)
        if match:
            extracted = match.group(1)
            # Check if it matches a valid category
            for category in valid_categories:
                if category.lower() == extracted:
                    return category

        # If nothing worked, return parse_error
        return "parse_error"

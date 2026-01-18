"""
Ollama API client and contract extraction orchestration.
"""

import json
import re
import time
from datetime import date, datetime
from typing import List, Optional, Tuple

import requests

from contract_validator.data.schemas import (
    Contract,
    ExtractedData,
    ExtractionResult,
    GroundTruth,
    PromptConfig,
)


class OllamaClient:
    """HTTP-based client for Ollama API."""

    def __init__(self, endpoint: str, model: str, timeout: int = 60, max_retries: int = 3):
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


class ContractExecutor:
    """Orchestrates contract extraction over contract datasets."""

    def __init__(self, ollama_client: OllamaClient):
        """
        Initialize contract executor.

        Args:
            ollama_client: Configured OllamaClient instance
        """
        self.client = ollama_client

    def execute_batch(
        self, contracts: List[Contract], prompt_config: PromptConfig
    ) -> List[ExtractionResult]:
        """
        Execute extraction on a batch of contracts.

        Args:
            contracts: List of contracts to process
            prompt_config: Prompt configuration to use

        Returns:
            List of ExtractionResult objects
        """
        results = []

        for contract in contracts:
            result = self.execute_single(contract, prompt_config)
            results.append(result)

        return results

    def execute_single(
        self, contract: Contract, prompt_config: PromptConfig
    ) -> ExtractionResult:
        """
        Execute extraction on a single contract.

        Args:
            contract: Contract to process
            prompt_config: Prompt configuration to use

        Returns:
            ExtractionResult object with extracted data and correctness flags
        """
        # Format user prompt with contract data
        user_prompt = prompt_config.user_prompt_template.format(
            contract_text=contract.text,
        )

        # Call Ollama API
        raw_response, execution_time = self.client.generate(
            system_prompt=prompt_config.system_prompt,
            user_prompt=user_prompt,
        )

        # Parse extracted data from response
        extracted = self._parse_extracted_data(raw_response)

        # Compare with ground truth
        correctness = self._compare_with_ground_truth(extracted, contract.ground_truth)

        # Create result object
        return ExtractionResult(
            contract_id=contract.id,
            extracted=extracted,
            expected=contract.ground_truth,
            student_name_correct=correctness["student_name"],
            matrikelnummer_correct=correctness["matrikelnummer"],
            company_name_correct=correctness["company_name"],
            start_date_correct=correctness["start_date"],
            end_date_correct=correctness["end_date"],
            all_correct=all(correctness.values()),
            raw_response=raw_response.strip(),
            execution_time=execution_time,
        )

    def _parse_extracted_data(self, response: str) -> ExtractedData:
        """
        Parse extracted data from LLM JSON response.

        Args:
            response: Raw LLM response

        Returns:
            ExtractedData object with parsed fields
        """
        response = response.strip()

        # Try to extract JSON from response
        json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if not json_match:
            # No JSON found, return empty data
            return ExtractedData()

        try:
            data = json.loads(json_match.group())
        except json.JSONDecodeError:
            return ExtractedData()

        # Parse individual fields
        student_name = self._parse_string(data.get("student_name"))
        matrikelnummer = self._parse_string(data.get("matrikelnummer"))
        company_name = self._parse_string(data.get("company_name"))
        company_address = self._parse_string(data.get("company_address"))
        start_date = self._parse_date(data.get("start_date"))
        end_date = self._parse_date(data.get("end_date"))

        return ExtractedData(
            student_name=student_name,
            matrikelnummer=matrikelnummer,
            company_name=company_name,
            company_address=company_address,
            start_date=start_date,
            end_date=end_date,
        )

    def _parse_string(self, value: Optional[str]) -> Optional[str]:
        """Parse a string value, returning None for empty or placeholder values."""
        if value is None:
            return None
        value = str(value).strip()
        if not value or value == "..." or value.lower() == "null" or value.lower() == "none":
            return None
        return value

    def _parse_date(self, value: Optional[str]) -> Optional[date]:
        """
        Parse a date from various formats.

        Supports:
        - YYYY-MM-DD (ISO format)
        - DD.MM.YYYY (German format)
        """
        if value is None:
            return None

        value = str(value).strip()
        if not value or value == "..." or value == "YYYY-MM-DD":
            return None

        # Try ISO format first
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            pass

        # Try German format
        try:
            return datetime.strptime(value, "%d.%m.%Y").date()
        except ValueError:
            pass

        return None

    def _compare_with_ground_truth(
        self, extracted: ExtractedData, ground_truth: GroundTruth
    ) -> dict:
        """
        Compare extracted data with ground truth.

        Args:
            extracted: Extracted data from LLM
            ground_truth: Ground truth data

        Returns:
            Dictionary with correctness flags for each field
        """
        return {
            "student_name": self._compare_strings(
                extracted.student_name, ground_truth.student_name
            ),
            "matrikelnummer": self._compare_strings(
                extracted.matrikelnummer, ground_truth.matrikelnummer
            ),
            "company_name": self._compare_strings(
                extracted.company_name, ground_truth.company_name
            ),
            "start_date": extracted.start_date == ground_truth.start_date,
            "end_date": extracted.end_date == ground_truth.end_date,
        }

    def _compare_strings(self, extracted: Optional[str], expected: str) -> bool:
        """
        Compare two strings with fuzzy matching.

        Args:
            extracted: Extracted string (may be None)
            expected: Expected string

        Returns:
            True if strings match (case-insensitive, whitespace-normalized)
        """
        if extracted is None:
            return False

        # Normalize both strings
        extracted_norm = " ".join(extracted.lower().split())
        expected_norm = " ".join(expected.lower().split())

        # Handle German umlauts (contract text uses ae, oe, ue instead of umlauts)
        umlaut_map = {
            "ae": "a",
            "oe": "o",
            "ue": "u",
            "ss": "ss",
        }
        for old, new in umlaut_map.items():
            extracted_norm = extracted_norm.replace(old, new)
            expected_norm = expected_norm.replace(old, new)

        return extracted_norm == expected_norm

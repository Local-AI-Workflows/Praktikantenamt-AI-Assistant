"""
Data loading utilities for test datasets and prompts.
"""

import json
from pathlib import Path
from typing import List

from prompt_tester.data.schemas import Email, EmailDataset, PromptConfig


class DataLoader:
    """Loads test data from JSON files and prompts from text files."""

    @staticmethod
    def load_emails(file_path: str) -> List[Email]:
        """
        Load emails from JSON file.

        Args:
            file_path: Path to JSON file containing emails

        Returns:
            List of Email objects

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If JSON is invalid or doesn't match schema
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Email dataset file not found: {file_path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Validate and parse using EmailDataset schema
            dataset = EmailDataset(**data)
            return dataset.emails

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {file_path}: {e}")
        except Exception as e:
            raise ValueError(f"Error loading emails from {file_path}: {e}")

    @staticmethod
    def load_prompt(file_path: str) -> str:
        """
        Load prompt from text file.

        Args:
            file_path: Path to prompt text file

        Returns:
            Prompt text content

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Prompt file not found: {file_path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            raise ValueError(f"Error loading prompt from {file_path}: {e}")

    @staticmethod
    def validate_dataset(emails: List[Email], valid_categories: List[str]) -> bool:
        """
        Validate that all emails have valid categories.

        Args:
            emails: List of emails to validate
            valid_categories: List of valid category names

        Returns:
            True if all emails are valid

        Raises:
            ValueError: If any email has invalid category
        """
        invalid_emails = []

        for email in emails:
            if email.expected_category not in valid_categories:
                invalid_emails.append(
                    f"Email {email.id}: invalid category '{email.expected_category}'"
                )

        if invalid_emails:
            raise ValueError(
                f"Dataset validation failed:\n" + "\n".join(invalid_emails)
            )

        return True

    @staticmethod
    def create_prompt_config(
        name: str,
        version: str,
        system_prompt_path: str,
        user_prompt_path: str,
    ) -> PromptConfig:
        """
        Create a PromptConfig from prompt files.

        Args:
            name: Prompt name/identifier
            version: Prompt version
            system_prompt_path: Path to system prompt file
            user_prompt_path: Path to user prompt template file

        Returns:
            PromptConfig object

        Raises:
            FileNotFoundError: If any prompt file doesn't exist
        """
        system_prompt = DataLoader.load_prompt(system_prompt_path)
        user_prompt_template = DataLoader.load_prompt(user_prompt_path)

        return PromptConfig(
            name=name,
            version=version,
            system_prompt=system_prompt,
            user_prompt_template=user_prompt_template,
        )

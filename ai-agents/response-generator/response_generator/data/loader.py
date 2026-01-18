"""
Data loading utilities for templates, emails, and prompts.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from response_generator.data.schemas import (
    CategorizedEmail,
    CategorizedEmailDataset,
    EmailCategory,
    ResponseTemplate,
    ResponseTone,
)


class TemplateLoader:
    """Loads and manages response templates."""

    def __init__(self, templates_directory: str = "templates"):
        """
        Initialize template loader.

        Args:
            templates_directory: Path to directory containing templates
        """
        self.templates_directory = Path(templates_directory)
        self._templates: Dict[Tuple[EmailCategory, ResponseTone], ResponseTemplate] = {}
        self._load_all_templates()

    def _load_all_templates(self) -> None:
        """Load all templates from the templates directory."""
        for category in EmailCategory:
            for tone in ResponseTone:
                template = self._load_template(category, tone)
                if template:
                    self._templates[(category, tone)] = template

    def _load_template(
        self, category: EmailCategory, tone: ResponseTone
    ) -> Optional[ResponseTemplate]:
        """
        Load a single template file.

        Args:
            category: Email category
            tone: Response tone

        Returns:
            ResponseTemplate or None if file doesn't exist
        """
        template_path = self.templates_directory / category.value / f"{tone.value}.txt"

        if not template_path.exists():
            return None

        try:
            with open(template_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse subject and body from template
            subject_template, body_template = self._parse_template(content)

            # Extract placeholders
            placeholders = self._extract_placeholders(content)

            return ResponseTemplate(
                category=category,
                tone=tone,
                subject_template=subject_template,
                body_template=body_template,
                placeholders=placeholders,
            )
        except Exception as e:
            print(f"Warning: Failed to load template {template_path}: {e}")
            return None

    def _parse_template(self, content: str) -> Tuple[str, str]:
        """
        Parse template content into subject and body.

        Args:
            content: Raw template content

        Returns:
            Tuple of (subject_template, body_template)
        """
        lines = content.strip().split("\n")
        subject_template = ""
        body_lines = []
        in_body = False

        for line in lines:
            if line.startswith("SUBJECT:"):
                subject_template = line.replace("SUBJECT:", "").strip()
            elif subject_template and not in_body:
                if line.strip():  # First non-empty line after subject
                    in_body = True
                    body_lines.append(line)
                else:
                    # Skip empty lines between subject and body
                    continue
            else:
                body_lines.append(line)

        body_template = "\n".join(body_lines).strip()
        return subject_template, body_template

    def _extract_placeholders(self, content: str) -> List[str]:
        """
        Extract placeholder names from template content.

        Args:
            content: Template content

        Returns:
            List of placeholder names
        """
        # Find all {placeholder} patterns
        pattern = r"\{([a-z_]+)\}"
        matches = re.findall(pattern, content)
        # Return unique placeholders
        return list(set(matches))

    def get_template(
        self, category: EmailCategory, tone: ResponseTone
    ) -> Optional[ResponseTemplate]:
        """
        Get a template for the given category and tone.

        Args:
            category: Email category
            tone: Response tone

        Returns:
            ResponseTemplate or None if not found
        """
        return self._templates.get((category, tone))

    def get_templates_for_category(
        self, category: EmailCategory
    ) -> Dict[ResponseTone, ResponseTemplate]:
        """
        Get all templates for a category.

        Args:
            category: Email category

        Returns:
            Dictionary mapping tone to template
        """
        result = {}
        for tone in ResponseTone:
            template = self.get_template(category, tone)
            if template:
                result[tone] = template
        return result

    def list_available_templates(self) -> List[Tuple[EmailCategory, ResponseTone]]:
        """
        List all available template combinations.

        Returns:
            List of (category, tone) tuples
        """
        return list(self._templates.keys())

    def reload_templates(self) -> None:
        """Reload all templates from disk."""
        self._templates.clear()
        self._load_all_templates()


class DataLoader:
    """Loads test data from JSON files and prompts from text files."""

    @staticmethod
    def load_emails(file_path: str) -> List[CategorizedEmail]:
        """
        Load categorized emails from JSON file.

        Args:
            file_path: Path to JSON file containing emails

        Returns:
            List of CategorizedEmail objects

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

            # Validate and parse using CategorizedEmailDataset schema
            dataset = CategorizedEmailDataset(**data)
            return dataset.emails

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {file_path}: {e}")
        except Exception as e:
            raise ValueError(f"Error loading emails from {file_path}: {e}")

    @staticmethod
    def load_single_email(file_path: str) -> CategorizedEmail:
        """
        Load a single email from JSON file.

        Args:
            file_path: Path to JSON file containing a single email

        Returns:
            CategorizedEmail object

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If JSON is invalid or doesn't match schema
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Email file not found: {file_path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            return CategorizedEmail(**data)

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {file_path}: {e}")
        except Exception as e:
            raise ValueError(f"Error loading email from {file_path}: {e}")

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
    def validate_emails(
        emails: List[CategorizedEmail], valid_categories: List[str]
    ) -> bool:
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
            if email.category.value not in valid_categories:
                invalid_emails.append(
                    f"Email {email.id}: invalid category '{email.category.value}'"
                )

        if invalid_emails:
            raise ValueError(
                f"Dataset validation failed:\n" + "\n".join(invalid_emails)
            )

        return True

    @staticmethod
    def save_emails(emails: List[CategorizedEmail], file_path: str) -> None:
        """
        Save emails to JSON file.

        Args:
            emails: List of emails to save
            file_path: Output file path
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "metadata": {
                "version": "1.0",
                "total_emails": len(emails),
            },
            "emails": [email.model_dump() for email in emails],
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

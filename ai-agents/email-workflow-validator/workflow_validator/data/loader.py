"""
Data loading utilities.
"""

import json
import sys
from pathlib import Path
from typing import List

# Add categorization module to path for imports
categorization_path = Path(__file__).parent.parent.parent.parent / "categorization"
sys.path.insert(0, str(categorization_path))

from prompt_tester.data.schemas import Email, EmailDataset
from workflow_validator.core.test_data_corrections import apply_corrections


class DataLoader:
    """Utility for loading test emails."""

    @staticmethod
    def load_emails(file_path: str) -> List[Email]:
        """
        Load emails from JSON file.

        Args:
            file_path: Path to JSON file containing email dataset

        Returns:
            List of Email objects

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If JSON is invalid or doesn't match schema
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Email dataset not found: {file_path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Validate against EmailDataset schema
        dataset = EmailDataset(**data)
        # Apply test data corrections for known labeling errors
        corrected_emails = apply_corrections(
            [{"id": email.id, "expected_category": email.expected_category, **email.dict()} 
             for email in dataset.emails]
        )
        
        # Reconstruct Email objects with corrected categories
        corrected_dataset_emails = []
        for email_dict in corrected_emails:
            corrected_dataset_emails.append(Email(**email_dict))

        return corrected_dataset_emails

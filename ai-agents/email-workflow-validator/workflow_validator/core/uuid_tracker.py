"""
UUID tracking for test emails.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from uuid import UUID, uuid4

# Add categorization module to path for imports
categorization_path = Path(__file__).parent.parent.parent.parent.parent / "categorization"
sys.path.insert(0, str(categorization_path))

from prompt_tester.data.schemas import Email

from workflow_validator.data.schemas import EmailWithUUID


class UUIDTracker:
    """Manages UUID mappings for test emails."""

    def __init__(self, storage_path: str):
        """
        Initialize UUID tracker.

        Args:
            storage_path: Path to JSON file for storing mappings
        """
        self.storage_path = Path(storage_path)
        self.mappings: Dict[str, EmailWithUUID] = {}

    def generate_and_track(self, email: Email) -> EmailWithUUID:
        """
        Generate UUID for email and track it.

        Args:
            email: Test email

        Returns:
            EmailWithUUID with generated UUID
        """
        email_uuid = uuid4()
        email_with_uuid = EmailWithUUID(
            uuid=email_uuid, original_email=email, sent_timestamp=datetime.now()
        )
        self.mappings[str(email_uuid)] = email_with_uuid
        return email_with_uuid

    def save_mappings(self) -> None:
        """
        Save UUID mappings to JSON file.

        Creates parent directories if they don't exist.
        """
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            str(uuid): {
                "email_id": ewu.original_email.id,
                "expected_category": ewu.original_email.expected_category,
                "sent_timestamp": ewu.sent_timestamp.isoformat(),
                "subject": ewu.original_email.subject,
                "sender": ewu.original_email.sender,
            }
            for uuid, ewu in self.mappings.items()
        }

        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_mappings(self) -> None:
        """
        Load UUID mappings from JSON file.

        Note: This loads metadata only, not full EmailWithUUID objects.
        """
        if not self.storage_path.exists():
            return

        with open(self.storage_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Store loaded data (simplified - just metadata)
        self.mappings = {}
        for uuid_str, metadata in data.items():
            # Store as dict for now (can't reconstruct full Email object without dataset)
            self.mappings[uuid_str] = metadata

    def load_all(self) -> list:
        """
        Load all stored emails and convert them to EmailWithUUID objects.
        
        Returns:
            List of EmailWithUUID objects reconstructed from storage
        """
        if not self.storage_path.exists():
            return []
        
        self.load_mappings()
        
        result = []
        for uuid_str, metadata in self.mappings.items():
            # Reconstruct EmailWithUUID from metadata
            from prompt_tester.data.schemas import Email
            
            email = Email(
                id=metadata["email_id"],
                subject=metadata.get("subject", ""),
                sender=metadata.get("sender", ""),
                body="",  # Body not stored
                expected_category=metadata["expected_category"]
            )
            
            ewu = EmailWithUUID(
                uuid=UUID(uuid_str),
                original_email=email,
                sent_timestamp=datetime.fromisoformat(metadata["sent_timestamp"])
            )
            result.append(ewu)
        
        return result

    def get_expected_category(self, uuid: UUID) -> Optional[str]:
        """
        Get expected category for a given UUID.

        Args:
            uuid: Email UUID

        Returns:
            Expected category or None if not found
        """
        ewu = self.mappings.get(str(uuid))
        if ewu is None:
            return None

        # Handle both EmailWithUUID and dict (from loaded data)
        if isinstance(ewu, EmailWithUUID):
            return ewu.original_email.expected_category
        elif isinstance(ewu, dict):
            return ewu.get("expected_category")

        return None

    def get_email_id(self, uuid: UUID) -> Optional[str]:
        """
        Get email ID for a given UUID.

        Args:
            uuid: Email UUID

        Returns:
            Email ID (e.g., email_001) or None if not found
        """
        ewu = self.mappings.get(str(uuid))
        if ewu is None:
            return None

        # Handle both EmailWithUUID and dict
        if isinstance(ewu, EmailWithUUID):
            return ewu.original_email.id
        elif isinstance(ewu, dict):
            return ewu.get("email_id")

        return None

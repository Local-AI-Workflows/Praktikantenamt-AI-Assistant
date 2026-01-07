"""
Email sending orchestration.
"""

import sys
from pathlib import Path
from typing import List

# Add categorization module to path for imports
categorization_path = Path(__file__).parent.parent.parent.parent.parent / "categorization"
sys.path.insert(0, str(categorization_path))

from prompt_tester.data.schemas import Email

from workflow_validator.core.uuid_tracker import UUIDTracker
from workflow_validator.data.schemas import EmailWithUUID
from workflow_validator.email.smtp_client import SMTPClient


class EmailSender:
    """Orchestrates sending test emails."""

    def __init__(self, smtp_client: SMTPClient, uuid_tracker: UUIDTracker):
        """
        Initialize email sender.

        Args:
            smtp_client: SMTP client for sending
            uuid_tracker: UUID tracker for mapping
        """
        self.smtp_client = smtp_client
        self.uuid_tracker = uuid_tracker

    def send_batch(
        self, emails: List[Email], test_inbox: str, verbose: bool = False
    ) -> List[EmailWithUUID]:
        """
        Send batch of test emails to test inbox.

        Args:
            emails: List of test emails
            test_inbox: Target inbox email address
            verbose: Print detailed progress

        Returns:
            List of successfully sent emails with UUIDs
        """
        sent_emails = []

        for i, email in enumerate(emails, 1):
            # Generate UUID and track
            email_with_uuid = self.uuid_tracker.generate_and_track(email)

            # Send via SMTP
            success = self.smtp_client.send_test_email(
                subject=email.subject,
                body=email.body,
                sender=email.sender,
                uuid=email_with_uuid.uuid,
                to_address=test_inbox,
            )

            if success:
                sent_emails.append(email_with_uuid)
                if verbose:
                    print(f"  ✓ Sent {email.id} ({i}/{len(emails)})")
            else:
                if verbose:
                    print(f"  ✗ Failed {email.id} ({i}/{len(emails)})")

        # Save UUID mappings
        self.uuid_tracker.save_mappings()

        return sent_emails

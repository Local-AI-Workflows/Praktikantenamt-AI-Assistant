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
from workflow_validator.data.attachment_generator import (
    extract_email_metadata_for_pdf,
    generate_dummy_contract_pdf,
)
from workflow_validator.data.schemas import AttachmentInfo, EmailWithUUID
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
        self,
        emails: List[Email],
        test_inbox: str,
        verbose: bool = False,
        include_attachments: bool = True,
    ) -> List[EmailWithUUID]:
        """
        Send batch of test emails to test inbox.

        For emails with has_attachment=True (contract_submission), a dummy PDF
        simulating a Praktikumsvertrag is generated and attached when
        include_attachments is True.

        Args:
            emails: List of test emails
            test_inbox: Target inbox email address
            verbose: Print detailed progress
            include_attachments: Generate and attach PDF for has_attachment emails

        Returns:
            List of successfully sent emails with UUIDs
        """
        sent_emails = []

        for i, email in enumerate(emails, 1):
            # Generate PDF attachment for emails that should have one
            attachment_data = None
            attachment_info = None

            if include_attachments and email.has_attachment:
                pdf_meta = extract_email_metadata_for_pdf(email.subject, email.sender)
                pdf_bytes = generate_dummy_contract_pdf(**pdf_meta)
                filename = f"praktikumsvertrag_{email.id}.pdf"
                attachment_data = (pdf_bytes, filename, "application/pdf")
                attachment_info = AttachmentInfo(
                    filename=filename,
                    content_type="application/pdf",
                    size_bytes=len(pdf_bytes),
                )

            # Generate UUID and track (with attachment info when applicable)
            email_with_uuid = self.uuid_tracker.generate_and_track(
                email, attachment=attachment_info
            )

            # Send via SMTP
            success = self.smtp_client.send_test_email(
                subject=email.subject,
                body=email.body,
                sender=email.sender,
                uuid=email_with_uuid.uuid,
                to_address=test_inbox,
                attachment=attachment_data,
            )

            if success:
                sent_emails.append(email_with_uuid)
                if verbose:
                    attach_note = " (+PDF)" if attachment_info else ""
                    print(f"  ✓ Sent {email.id} ({i}/{len(emails)}){attach_note}")
            else:
                if verbose:
                    print(f"  ✗ Failed {email.id} ({i}/{len(emails)})")

        # Close SMTP connection if persistent
        try:
            self.uuid_tracker.save_mappings()
        finally:
            try:
                self.smtp_client.close()
            except Exception:
                # ignore close errors
                pass

        return sent_emails

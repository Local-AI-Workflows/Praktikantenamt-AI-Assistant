"""
SMTP client for sending test emails.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
from uuid import UUID

from workflow_validator.data.schemas import SMTPConfig


class SMTPClient:
    """SMTP client for sending test emails with embedded UUIDs."""

    def __init__(self, config: SMTPConfig):
        """
        Initialize SMTP client.

        Args:
            config: SMTP configuration
        """
        self.config = config

    def send_test_email(
        self,
        subject: str,
        body: str,
        sender: str,
        uuid: UUID,
        to_address: Optional[str] = None,
    ) -> bool:
        """
        Send a test email with embedded UUID.

        UUID Embedding Strategy:
        1. Custom header: X-Test-UUID: <uuid>
        2. Body footer: [TEST-ID: <uuid>]
        3. Both allow retrieval during validation

        Args:
            subject: Email subject line
            body: Email body content
            sender: Original sender address (from test data)
            uuid: UUID for tracking
            to_address: Recipient address (defaults to config.from_address)

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart()
            msg["From"] = sender  # Use original sender from test data
            msg["To"] = to_address or self.config.from_address
            msg["Subject"] = subject
            msg["X-Test-UUID"] = str(uuid)  # Custom header for tracking

            # Embed UUID in body for redundancy
            body_with_uuid = f"{body}\n\n[TEST-ID: {uuid}]"
            msg.attach(MIMEText(body_with_uuid, "plain", "utf-8"))

            # Connect and send
            with smtplib.SMTP(self.config.host, self.config.port) as server:
                if self.config.use_tls:
                    server.starttls()
                server.login(self.config.username, self.config.password)
                server.send_message(msg)

            return True

        except Exception as e:
            print(f"Failed to send email: {e}")
            return False

    def health_check(self) -> bool:
        """
        Check if SMTP server is accessible.

        Returns:
            True if accessible, False otherwise
        """
        try:
            with smtplib.SMTP(self.config.host, self.config.port, timeout=5) as server:
                if self.config.use_tls:
                    server.starttls()
                server.login(self.config.username, self.config.password)
            return True
        except Exception:
            return False

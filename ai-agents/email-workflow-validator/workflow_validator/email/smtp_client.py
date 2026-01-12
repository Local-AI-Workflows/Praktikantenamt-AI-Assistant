"""
SMTP client for sending test emails with optional connection reuse, retries, and delays.
"""

import smtplib
import time
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
from uuid import UUID

from workflow_validator.data.schemas import SMTPConfig

logger = logging.getLogger(__name__)


class SMTPClient:
    """SMTP client for sending test emails with embedded UUIDs."""

    def __init__(self, config: SMTPConfig):
        """
        Initialize SMTP client.

        Args:
            config: SMTP configuration
        """
        self.config = config
        self.server: Optional[smtplib.SMTP] = None

    def _connect(self) -> None:
        """Establish SMTP connection and login."""
        logger.debug("Connecting to SMTP %s:%s", self.config.host, self.config.port)
        server = smtplib.SMTP(self.config.host, self.config.port, timeout=self.config.timeout_seconds)
        server.ehlo()
        if self.config.use_tls:
            server.starttls()
            server.ehlo()
        server.login(self.config.username, self.config.password)
        self.server = server

    def _disconnect(self) -> None:
        """Gracefully close SMTP connection if open."""
        if self.server:
            try:
                self.server.quit()
            except Exception:
                # Some servers close connection abruptly; ignore
                pass
            finally:
                self.server = None

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

        This implementation attempts to reuse the SMTP connection when configured to do so,
        and will retry on transient errors such as SMTPServerDisconnected.
        """
        # Prepare message
        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = to_address or self.config.from_address
        msg["Subject"] = subject
        msg["X-Test-UUID"] = str(uuid)
        body_with_uuid = f"{body}\n\n[TEST-ID: {uuid}]"
        msg.attach(MIMEText(body_with_uuid, "plain", "utf-8"))

        attempts = 0
        while attempts <= self.config.max_retries:
            try:
                if not self.config.reuse_connection or self.server is None:
                    # connect per-send or if no connection exists
                    self._connect()

                # send
                assert self.server is not None
                self.server.send_message(msg)

                # optional small delay to reduce rate-limiting
                if self.config.send_delay_seconds and self.config.send_delay_seconds > 0:
                    time.sleep(self.config.send_delay_seconds)

                return True

            except smtplib.SMTPServerDisconnected as e:
                logger.warning("SMTP server disconnected unexpectedly: %s; attempt %s", e, attempts)
                # force reconnect and retry
                self._disconnect()
                attempts += 1
                time.sleep(1 * attempts)
                continue

            except (smtplib.SMTPException, OSError) as e:
                logger.error("SMTP send failed: %s", e)
                # Do not retry for other persistent errors
                self._disconnect()
                return False

            except Exception as e:
                logger.exception("Unexpected error while sending email: %s", e)
                self._disconnect()
                return False

        # If we exhausted retries
        logger.error("Exhausted SMTP retries for email %s", uuid)
        return False

    def health_check(self) -> bool:
        """
        Check if SMTP server is accessible.

        Returns:
            True if accessible, False otherwise
        """
        try:
            server = smtplib.SMTP(self.config.host, self.config.port, timeout=5)
            server.ehlo()
            if self.config.use_tls:
                server.starttls()
                server.ehlo()
            server.login(self.config.username, self.config.password)
            server.quit()
            return True
        except Exception:
            return False

    def close(self) -> None:
        """Public method to close persistent SMTP connection."""
        self._disconnect()

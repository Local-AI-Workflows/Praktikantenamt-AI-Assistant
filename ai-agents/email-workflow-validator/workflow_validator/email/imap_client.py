"""
IMAP client for email validation and retrieval.
"""

import email
import imaplib
import re
from email.header import decode_header
from typing import Dict, List, Optional
from uuid import UUID

from workflow_validator.data.schemas import IMAPConfig


class IMAPClient:
    """IMAP client with connection management and UUID-based search."""

    def __init__(self, config: IMAPConfig):
        """
        Initialize IMAP client.

        Args:
            config: IMAP configuration
        """
        self.config = config
        self.connection: Optional[imaplib.IMAP4] = None

    def connect(self) -> None:
        """
        Establish IMAP connection with SSL.

        Raises:
            ConnectionError: If connection fails
        """
        try:
            if self.config.use_ssl:
                # IMAPS direct SSL connection
                self.connection = imaplib.IMAP4_SSL(
                    self.config.host, self.config.port
                )
            else:
                # Plain connection with optional STARTTLS upgrade
                self.connection = imaplib.IMAP4(self.config.host, self.config.port)
                if self.config.use_starttls:
                    self.connection.starttls()

            self.connection.login(self.config.username, self.config.password)
        except Exception as e:
            raise ConnectionError(f"Failed to connect to IMAP server: {e}")

    def disconnect(self) -> None:
        """Close IMAP connection."""
        if self.connection:
            try:
                self.connection.close()
                self.connection.logout()
            except Exception:
                pass
            self.connection = None

    def health_check(self) -> bool:
        """
        Check if IMAP server is accessible.

        Returns:
            True if accessible, False otherwise
        """
        try:
            self.connect()
            self.disconnect()
            return True
        except Exception:
            return False

    def list_folders(self) -> List[str]:
        """
        List all available folders.

        Returns:
            List of folder names

        Raises:
            RuntimeError: If not connected
        """
        if not self.connection:
            raise RuntimeError("Not connected to IMAP server")

        try:
            status, folders = self.connection.list()
            if status != "OK":
                return []

            folder_names = []
            for folder_bytes in folders:
                # Parse folder list response
                # Format: (\\HasNoChildren) "." INBOX.folder_name
                # The folder name is the part AFTER the last quoted string (delimiter)
                folder_str = folder_bytes.decode('utf-8', errors='ignore')
                
                # Split by quotes to extract the delimiter and folder name
                parts = folder_str.split('"')
                # parts[0] = "(\\HasNoChildren) "
                # parts[1] = "." (the delimiter, quoted)
                # parts[2] = " INBOX.folder_name" (folder name without quotes, with leading space)
                
                if len(parts) >= 3:
                    # The folder name is after the delimiter
                    folder_name = parts[-1].strip()  # Last part after the last quote, stripped
                    if folder_name:  # Only add non-empty folder names
                        folder_names.append(folder_name)

            return folder_names
        except Exception as e:
            print(f"Error listing folders: {e}")
            return []

    def search_by_uuid(self, uuid: UUID, folder: str) -> Optional[Dict]:
        """
        Search for email by UUID in a specific folder.

        Strategy:
        1. SELECT folder
        2. Search for UUID in body text (more reliable than headers)
        3. FETCH email content if found
        4. Parse and extract UUID

        Args:
            uuid: UUID to search for
            folder: Folder name to search in

        Returns:
            Email details dict if found, None otherwise
        """
        if not self.connection:
            raise RuntimeError("Not connected to IMAP server")

        uuid_str = str(uuid)

        try:
            # Select folder
            status, _ = self.connection.select(folder, readonly=True)
            if status != "OK":
                return None

            # Search for UUID in body text
            # Use TEXT search which searches entire email including body
            search_term = f'TEXT "[TEST-ID: {uuid_str}]"'
            status, messages = self.connection.search(None, search_term)

            if status != "OK" or not messages[0]:
                return None

            # Get first matching message
            msg_nums = messages[0].split()
            if not msg_nums:
                return None

            msg_num = msg_nums[0]

            # Fetch email content
            status, msg_data = self.connection.fetch(msg_num, "(RFC822)")
            if status != "OK":
                return None

            # Parse email
            raw_email = msg_data[0][1]
            email_message = email.message_from_bytes(raw_email)

            # Extract details
            subject = self._decode_header(email_message["Subject"])
            sender = email_message["From"]

            return {
                "message_num": msg_num.decode(),
                "subject": subject,
                "sender": sender,
                "folder": folder,
            }

        except Exception as e:
            print(f"Error searching in folder {folder}: {e}")
            return None

    def find_email_location(self, uuid: UUID, folders: List[str]) -> Optional[str]:
        """
        Find which folder contains the email with given UUID.

        Args:
            uuid: UUID to search for
            folders: List of folders to search

        Returns:
            Folder name where email was found, None if not found
        """
        for folder in folders:
            try:
                result = self.search_by_uuid(uuid, folder)
                if result:
                    return folder
            except Exception as e:
                print(f"Error searching folder {folder}: {e}")
                continue

        return None

    def delete_emails_by_uuid(self, uuids: List[UUID]) -> int:
        """
        Delete test emails after validation.

        Args:
            uuids: List of UUIDs to delete

        Returns:
            Number of emails deleted
        """
        if not self.connection:
            raise RuntimeError("Not connected to IMAP server")

        deleted_count = 0

        # Get all folders
        folders = self.list_folders()

        for uuid in uuids:
            # Find email location
            folder = self.find_email_location(uuid, folders)
            if not folder:
                continue

            try:
                # Select folder (read-write mode)
                status, _ = self.connection.select(folder, readonly=False)
                if status != "OK":
                    continue

                # Search for email
                uuid_str = str(uuid)
                search_term = f'TEXT "[TEST-ID: {uuid_str}]"'
                status, messages = self.connection.search(None, search_term)

                if status != "OK" or not messages[0]:
                    continue

                # Mark as deleted
                msg_nums = messages[0].split()
                for msg_num in msg_nums:
                    self.connection.store(msg_num, "+FLAGS", "\\Deleted")
                    deleted_count += 1

                # Expunge to permanently delete
                self.connection.expunge()

            except Exception as e:
                print(f"Error deleting email {uuid}: {e}")
                continue

        return deleted_count

    def _decode_header(self, header: str) -> str:
        """
        Decode email header.

        Args:
            header: Header string to decode

        Returns:
            Decoded header string
        """
        if not header:
            return ""

        decoded_parts = decode_header(header)
        decoded_str = ""

        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                decoded_str += part.decode(encoding or "utf-8", errors="ignore")
            else:
                decoded_str += part

        return decoded_str

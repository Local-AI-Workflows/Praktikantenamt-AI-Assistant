"""
Data models for workflow validation using Pydantic.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

# Add categorization module to path for imports
categorization_path = Path(__file__).parent.parent.parent.parent / "categorization"
sys.path.insert(0, str(categorization_path))

from prompt_tester.data.schemas import Email, Metrics, ValidationReport


class EmailWithUUID(BaseModel):
    """Email with tracking UUID for validation."""

    uuid: UUID = Field(..., description="RFC4122 UUID for tracking")
    original_email: Email = Field(..., description="Original test email")
    sent_timestamp: datetime = Field(..., description="When email was sent")


class EmailLocation(BaseModel):
    """Tracks where an email ended up in IMAP."""

    uuid: UUID = Field(..., description="Email UUID")
    email_id: str = Field(..., description="Original email ID (email_001, etc)")
    found_in_folder: Optional[str] = Field(
        None, description="IMAP folder name where email was found"
    )
    expected_category: str = Field(..., description="Expected category")
    predicted_category: Optional[str] = Field(
        None, description="Inferred from folder mapping"
    )
    is_correct: bool = Field(False, description="Whether routing was correct")
    validation_timestamp: datetime = Field(
        ..., description="When validation occurred"
    )


class FolderMapping(BaseModel):
    """Maps IMAP folder names to email categories."""

    folder_name: str = Field(..., description="IMAP folder name")
    category: str = Field(..., description="Email category")


class IMAPConfig(BaseModel):
    """IMAP server configuration."""

    host: str = Field(..., description="IMAP server host")
    port: int = Field(default=993, description="IMAP port (993 for SSL)")
    username: str = Field(..., description="IMAP username")
    password: str = Field(..., description="IMAP password (env var recommended)")
    use_ssl: bool = Field(default=True, description="Use SSL/TLS")
    mailbox: str = Field(default="INBOX", description="Target mailbox")


class SMTPConfig(BaseModel):
    """SMTP server configuration."""

    host: str = Field(..., description="SMTP server host")
    port: int = Field(default=587, description="SMTP port (587 for TLS)")
    username: str = Field(..., description="SMTP username")
    password: str = Field(..., description="SMTP password")
    use_tls: bool = Field(default=True, description="Use STARTTLS")
    from_address: str = Field(..., description="From email address")


class WorkflowValidationConfig(BaseModel):
    """Complete configuration for workflow validation."""

    imap: IMAPConfig = Field(..., description="IMAP configuration")
    smtp: SMTPConfig = Field(..., description="SMTP configuration")
    folder_mappings: List[FolderMapping] = Field(
        default=[
            FolderMapping(
                folder_name="INBOX.Contract_Submission",
                category="contract_submission",
            ),
            FolderMapping(
                folder_name="INBOX.International_Questions",
                category="international_office_question",
            ),
            FolderMapping(
                folder_name="INBOX.Postponement_Requests",
                category="internship_postponement",
            ),
            FolderMapping(folder_name="INBOX.Uncategorized", category="uncategorized"),
        ],
        description="IMAP folder to category mappings",
    )
    wait_time_seconds: int = Field(
        default=60, description="Wait time for n8n processing"
    )
    cleanup_after_test: bool = Field(
        default=True, description="Delete test emails after validation"
    )
    uuid_storage_path: str = Field(
        default="results/uuid_mapping.json", description="Where to store UUID mappings"
    )
    categories: List[str] = Field(
        default=[
            "contract_submission",
            "international_office_question",
            "internship_postponement",
            "uncategorized",
        ],
        description="Valid email categories",
    )
    output_format: str = Field(
        default="both", description="Output format: json, csv, or both"
    )
    output_directory: str = Field(default="results", description="Output directory")
    timestamp_format: str = Field(
        default="%Y%m%d_%H%M%S", description="Timestamp format for filenames"
    )


class WorkflowValidationReport(ValidationReport):
    """Extended validation report for workflow testing."""

    email_locations: List[EmailLocation] = Field(
        ..., description="Where each email was found"
    )
    emails_not_found: List[str] = Field(
        default=[], description="UUIDs of emails not found (as strings)"
    )
    folder_mappings_used: List[FolderMapping] = Field(
        ..., description="Folder mappings used"
    )
    wait_time_seconds: int = Field(..., description="How long we waited")
    total_sent: int = Field(..., description="Total emails sent")
    total_found: int = Field(..., description="Total emails found")

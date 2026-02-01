"""Pydantic data models for company lookup."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class CompanyStatus(str, Enum):
    """Status of a company in the lookup system."""

    WHITELISTED = "whitelisted"
    BLACKLISTED = "blacklisted"
    UNKNOWN = "unknown"


class CompanyInfo(BaseModel):
    """Information about a company in the list."""

    name: str = Field(..., description="Official company name")
    status: CompanyStatus = Field(..., description="Whitelist/blacklist status")
    notes: Optional[str] = Field(None, description="Additional notes about the company")
    added_date: Optional[datetime] = Field(None, description="When the company was added")
    category: Optional[str] = Field(None, description="Industry category")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure company name is not empty."""
        if not v or not v.strip():
            raise ValueError("Company name cannot be empty")
        return v.strip()


class MatchResult(BaseModel):
    """Result of a fuzzy match operation."""

    matched_name: str = Field(..., description="The matched company name from the list")
    original_query: str = Field(..., description="The original search query")
    similarity_score: float = Field(
        ..., ge=0.0, le=100.0, description="Fuzzy match score (0-100)"
    )
    status: CompanyStatus = Field(..., description="Status of the matched company")
    notes: Optional[str] = Field(None, description="Notes about the matched company")
    is_exact_match: bool = Field(False, description="Whether this was an exact match")


class LookupRequest(BaseModel):
    """Request for company lookup."""

    company_name: str = Field(..., description="Company name to look up")
    fuzzy_threshold: float = Field(
        80.0,
        ge=0.0,
        le=100.0,
        description="Minimum similarity score for fuzzy matches (0-100)",
    )
    include_partial_matches: bool = Field(
        True, description="Include partial/fuzzy matches below threshold"
    )
    max_results: int = Field(5, ge=1, le=20, description="Maximum number of results to return")

    @field_validator("company_name")
    @classmethod
    def validate_company_name(cls, v: str) -> str:
        """Ensure company name is not empty."""
        if not v or not v.strip():
            raise ValueError("Company name cannot be empty")
        return v.strip()


class LookupResult(BaseModel):
    """Result of a company lookup operation."""

    query: str = Field(..., description="The original search query")
    status: CompanyStatus = Field(..., description="Overall status determination")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in the result (0-1)"
    )
    best_match: Optional[MatchResult] = Field(None, description="Best matching company")
    all_matches: list[MatchResult] = Field(
        default_factory=list, description="All matches above threshold"
    )
    warnings: list[str] = Field(default_factory=list, description="Any warnings or notes")
    lookup_timestamp: datetime = Field(
        default_factory=datetime.now, description="When the lookup was performed"
    )

    @property
    def is_approved(self) -> bool:
        """Check if company is approved for internship."""
        return self.status == CompanyStatus.WHITELISTED

    @property
    def is_blocked(self) -> bool:
        """Check if company is blocked from internship."""
        return self.status == CompanyStatus.BLACKLISTED


class CompanyListStats(BaseModel):
    """Statistics about the company lists."""

    total_companies: int = Field(..., description="Total number of companies")
    whitelisted_count: int = Field(..., description="Number of whitelisted companies")
    blacklisted_count: int = Field(..., description="Number of blacklisted companies")
    categories: list[str] = Field(default_factory=list, description="Available categories")
    last_updated: Optional[datetime] = Field(None, description="When lists were last updated")
    source_file: Optional[str] = Field(None, description="Source file path")


class Config(BaseModel):
    """Configuration for company lookup."""

    language: str = Field(
        "en", description="Language for output (en=English, de=German)"
    )
    excel_file_path: Optional[str] = Field(
        None, description="Path to the Excel file with company lists"
    )
    default_fuzzy_threshold: float = Field(
        80.0, ge=0.0, le=100.0, description="Default fuzzy matching threshold"
    )
    case_sensitive: bool = Field(False, description="Whether matching is case-sensitive")
    whitelist_sheet: str = Field("Whitelist", description="Sheet name for whitelist")
    blacklist_sheet: str = Field("Blacklist", description="Sheet name for blacklist")
    company_name_column: str = Field("Company Name", description="Column header for company names")
    notes_column: Optional[str] = Field("Notes", description="Column header for notes")
    category_column: Optional[str] = Field("Category", description="Column header for category")
    api_host: str = Field("0.0.0.0", description="API server host")
    api_port: int = Field(8000, description="API server port")
    output_format: str = Field("json", description="Default output format")
    output_directory: str = Field("results", description="Output directory for exports")

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        """Validate language code."""
        lang = v.lower().strip()
        if lang in ("de", "german", "deutsch", "de-de", "de_de"):
            return "de"
        elif lang in ("en", "english", "en-us", "en_us", "en-gb", "en_gb"):
            return "en"
        # Default to English for unknown languages
        return "en"

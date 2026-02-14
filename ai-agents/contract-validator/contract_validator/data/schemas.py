"""
Data models for contract validation framework using Pydantic.
"""

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ContractFormat(str, Enum):
    """Supported contract text formats."""

    STRUCTURED = "structured"
    TABULAR = "tabular"
    FORM_STYLE = "form_style"
    FLOWING_TEXT = "flowing_text"


class ValidationStatus(str, Enum):
    """Possible validation outcomes for a contract."""

    VALID = "valid"
    INVALID_DURATION = "invalid_duration"
    BLACKLISTED_COMPANY = "blacklisted_company"
    MISSING_DATA = "missing_data"


class OcrSeverity(str, Enum):
    """Severity level for OCR corruption / scan artifact simulation."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ExtractedData(BaseModel):
    """Data extracted from a contract by the LLM."""

    student_name: Optional[str] = Field(default=None, description="Full name of the student")
    matrikelnummer: Optional[str] = Field(default=None, description="7-digit student ID number")
    company_name: Optional[str] = Field(default=None, description="Name of the company")
    company_address: Optional[str] = Field(default=None, description="Address of the company")
    start_date: Optional[date] = Field(default=None, description="Internship start date")
    end_date: Optional[date] = Field(default=None, description="Internship end date")


class GroundTruth(BaseModel):
    """Ground truth data for a contract."""

    student_name: str = Field(..., description="Full name of the student")
    matrikelnummer: str = Field(..., description="7-digit student ID number")
    company_name: str = Field(..., description="Name of the company")
    company_address: Optional[str] = Field(default=None, description="Address of the company")
    start_date: date = Field(..., description="Internship start date")
    end_date: date = Field(..., description="Internship end date")
    working_days: int = Field(..., description="Number of working days in the internship")
    expected_status: ValidationStatus = Field(..., description="Expected validation status")


class Contract(BaseModel):
    """Represents a test contract for extraction and validation."""

    id: str = Field(..., description="Unique contract identifier")
    text: str = Field(..., description="Contract text content")
    format: ContractFormat = Field(..., description="Format of the contract text")
    ground_truth: GroundTruth = Field(..., description="Ground truth data for validation")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata (difficulty, edge_case, etc.)"
    )


class ContractDataset(BaseModel):
    """Container for contract test dataset."""

    metadata: Dict[str, Any] = Field(..., description="Dataset metadata")
    contracts: List[Contract] = Field(..., description="List of test contracts")


class PromptConfig(BaseModel):
    """Configuration for a prompt."""

    name: str = Field(..., description="Prompt name/identifier")
    version: str = Field(..., description="Prompt version")
    system_prompt: str = Field(..., description="System prompt text")
    user_prompt_template: str = Field(..., description="User prompt template with variables")


class ExtractionResult(BaseModel):
    """Result of extracting data from a single contract."""

    contract_id: str = Field(..., description="Contract identifier")
    contract_format: ContractFormat = Field(..., description="Format of the source contract")
    extracted: ExtractedData = Field(..., description="Extracted data from the contract")
    expected: GroundTruth = Field(..., description="Ground truth data")
    student_name_correct: bool = Field(..., description="Whether student name was extracted correctly")
    matrikelnummer_correct: bool = Field(..., description="Whether matrikelnummer was extracted correctly")
    company_name_correct: bool = Field(..., description="Whether company name was extracted correctly")
    start_date_correct: bool = Field(..., description="Whether start date was extracted correctly")
    end_date_correct: bool = Field(..., description="Whether end date was extracted correctly")
    all_correct: bool = Field(..., description="Whether all fields were extracted correctly")
    raw_response: str = Field(..., description="Raw LLM response")
    execution_time: float = Field(..., description="Execution time in seconds")

    @property
    def is_correct(self) -> bool:
        """Check if all fields were extracted correctly."""
        return self.all_correct


class ExtractionMetrics(BaseModel):
    """Metrics for extraction accuracy."""

    total_contracts: int = Field(..., description="Total number of contracts tested")
    student_name_accuracy: float = Field(..., description="Accuracy for student name extraction")
    matrikelnummer_accuracy: float = Field(..., description="Accuracy for matrikelnummer extraction")
    company_name_accuracy: float = Field(..., description="Accuracy for company name extraction")
    start_date_accuracy: float = Field(..., description="Accuracy for start date extraction")
    end_date_accuracy: float = Field(..., description="Accuracy for end date extraction")
    overall_accuracy: float = Field(..., description="Overall extraction accuracy")
    per_format_accuracy: Dict[str, float] = Field(..., description="Accuracy per contract format")


class ValidationResult(BaseModel):
    """Result of validating a single contract."""

    contract_id: str = Field(..., description="Contract identifier")
    extracted: ExtractedData = Field(..., description="Extracted data from the contract")
    calculated_working_days: Optional[int] = Field(
        default=None, description="Calculated working days from dates"
    )
    status: ValidationStatus = Field(..., description="Determined validation status")
    expected_status: ValidationStatus = Field(..., description="Expected validation status")
    is_correct: bool = Field(..., description="Whether validation status matches expected")
    issues: List[str] = Field(default_factory=list, description="List of validation issues found")


class ValidationReport(BaseModel):
    """Complete validation report for a prompt."""

    total_contracts: int = Field(..., description="Total number of contracts tested")
    extraction_metrics: ExtractionMetrics = Field(..., description="Extraction accuracy metrics")
    validation_accuracy: float = Field(..., description="Validation status accuracy")
    per_status_accuracy: Dict[str, float] = Field(..., description="Accuracy per validation status")
    results: List[ExtractionResult] = Field(..., description="Detailed extraction results")
    validation_results: List[ValidationResult] = Field(..., description="Detailed validation results")
    prompt_name: str = Field(..., description="Name of the prompt tested")
    test_timestamp: datetime = Field(default_factory=datetime.now, description="When test was run")


class ComparisonReport(BaseModel):
    """Report comparing multiple prompts."""

    prompts_compared: List[str] = Field(..., description="List of prompt names compared")
    extraction_accuracy_comparison: Dict[str, float] = Field(
        ..., description="Overall extraction accuracy for each prompt"
    )
    validation_accuracy_comparison: Dict[str, float] = Field(
        ..., description="Validation accuracy for each prompt"
    )
    per_format_comparison: Dict[str, Dict[str, float]] = Field(
        ..., description="Per-format accuracy for each prompt"
    )
    winner: Optional[str] = Field(default=None, description="Best performing prompt")
    test_timestamp: datetime = Field(default_factory=datetime.now, description="When comparison was run")


class Config(BaseModel):
    """Configuration for the contract validation framework."""

    ollama_endpoint: str = Field(
        default="http://localhost:11434", description="Ollama API endpoint"
    )
    ollama_model: str = Field(default="llama3.2:3b", description="Ollama model to use")
    ollama_timeout: int = Field(default=60, description="Timeout in seconds")
    ollama_max_retries: int = Field(default=3, description="Maximum retry attempts")
    min_working_days: int = Field(default=95, description="Minimum required working days")
    output_format: str = Field(default="json", description="Output format: json or csv")
    output_directory: str = Field(default="results", description="Output directory")
    timestamp_format: str = Field(
        default="%Y%m%d_%H%M%S", description="Timestamp format for filenames"
    )

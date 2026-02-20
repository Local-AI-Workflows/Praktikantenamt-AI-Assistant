"""
Data models for prompt testing framework using Pydantic.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Email(BaseModel):
    """Represents a test email for categorization."""

    id: str = Field(..., description="Unique email identifier")
    subject: str = Field(..., description="Email subject line")
    body: str = Field(..., description="Email body content")
    sender: str = Field(..., description="Email sender address")
    has_attachment: bool = Field(default=False, description="Whether email has attachments")
    expected_category: str = Field(..., description="Ground truth category")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata (difficulty, keywords, etc.)"
    )


class EmailDataset(BaseModel):
    """Container for email test dataset."""

    metadata: Dict[str, Any] = Field(..., description="Dataset metadata")
    emails: List[Email] = Field(..., description="List of test emails")


class PromptConfig(BaseModel):
    """Configuration for a prompt."""

    name: str = Field(..., description="Prompt name/identifier")
    version: str = Field(..., description="Prompt version")
    system_prompt: str = Field(..., description="System prompt text")
    user_prompt_template: str = Field(..., description="User prompt template with variables")


class Result(BaseModel):
    """Result of categorizing a single email."""

    email_id: str = Field(..., description="Email identifier")
    predicted_category: str = Field(..., description="Predicted category from LLM")
    expected_category: str = Field(..., description="Ground truth category")
    confidence: Optional[float] = Field(
        default=None, description="Confidence score if available"
    )
    raw_response: str = Field(..., description="Raw LLM response")
    execution_time: float = Field(..., description="Execution time in seconds")
    timestamp: datetime = Field(default_factory=datetime.now, description="When test was run")

    @property
    def is_correct(self) -> bool:
        """Check if prediction matches expected category."""
        return self.predicted_category == self.expected_category


class Metrics(BaseModel):
    """Metrics for a single category."""

    precision: float = Field(..., description="Precision score")
    recall: float = Field(..., description="Recall score")
    f1_score: float = Field(..., description="F1 score")
    support: int = Field(..., description="Number of true instances")


class ValidationReport(BaseModel):
    """Complete validation report for a prompt."""

    overall_accuracy: float = Field(..., description="Overall accuracy")
    total_emails: int = Field(..., description="Total number of emails tested")
    correct_predictions: int = Field(..., description="Number of correct predictions")
    incorrect_predictions: int = Field(..., description="Number of incorrect predictions")
    parse_errors: int = Field(default=0, description="Number of emails where LLM response could not be parsed")
    mean_execution_time: float = Field(default=0.0, description="Mean execution time per email in seconds")
    per_category_metrics: Dict[str, Metrics] = Field(
        ..., description="Metrics for each category"
    )
    confusion_matrix: List[List[int]] = Field(..., description="Confusion matrix")
    misclassifications: List[Result] = Field(..., description="List of misclassified emails")
    prompt_name: Optional[str] = Field(default=None, description="Name of prompt tested")
    prompt_version: Optional[str] = Field(default=None, description="Version of prompt tested")
    test_timestamp: datetime = Field(
        default_factory=datetime.now, description="When test was run"
    )


class Disagreement(BaseModel):
    """Represents a case where two prompts disagree on categorization."""

    email_id: str = Field(..., description="Email identifier")
    prompt_a_prediction: str = Field(..., description="First prompt's prediction")
    prompt_b_prediction: str = Field(..., description="Second prompt's prediction")
    expected_category: str = Field(..., description="Ground truth category")
    prompt_a_correct: bool = Field(..., description="Whether prompt A was correct")
    prompt_b_correct: bool = Field(..., description="Whether prompt B was correct")
    prompt_a_raw_response: Optional[str] = Field(default=None, description="Full LLM response from prompt A")
    prompt_b_raw_response: Optional[str] = Field(default=None, description="Full LLM response from prompt B")


class ComparisonReport(BaseModel):
    """Report comparing multiple prompts."""

    prompts_compared: List[str] = Field(..., description="List of prompt names compared")
    accuracy_comparison: Dict[str, float] = Field(
        ..., description="Accuracy for each prompt"
    )
    disagreements: List[Disagreement] = Field(
        ..., description="Cases where prompts disagreed"
    )
    winner: Optional[str] = Field(default=None, description="Best performing prompt")
    test_timestamp: datetime = Field(
        default_factory=datetime.now, description="When comparison was run"
    )


class AggregatedMetrics(BaseModel):
    """Aggregated metrics over multiple test runs."""

    mean_precision: float = Field(..., description="Mean precision across runs")
    std_precision: float = Field(..., description="Standard deviation of precision")
    mean_recall: float = Field(..., description="Mean recall across runs")
    std_recall: float = Field(..., description="Standard deviation of recall")
    mean_f1_score: float = Field(..., description="Mean F1-score across runs")
    std_f1_score: float = Field(..., description="Standard deviation of F1-score")
    support: int = Field(..., description="Number of true instances (constant across runs)")


class AggregatedValidationReport(BaseModel):
    """Validation report aggregated over multiple test runs."""

    num_iterations: int = Field(..., description="Number of test iterations")
    mean_accuracy: float = Field(..., description="Mean overall accuracy")
    std_accuracy: float = Field(..., description="Standard deviation of accuracy")
    mean_parse_errors: float = Field(default=0.0, description="Mean number of parse errors per run")
    mean_execution_time: float = Field(default=0.0, description="Mean execution time per email across all runs in seconds")

    per_category_metrics: Dict[str, AggregatedMetrics] = Field(
        ..., description="Aggregated metrics for each category"
    )

    # Confusion matrices
    confusion_matrices: List[List[List[int]]] = Field(
        ..., description="All confusion matrices from individual runs"
    )
    aggregated_confusion_matrix: List[List[float]] = Field(
        ..., description="Mean confusion matrix across all runs"
    )
    std_confusion_matrix: List[List[float]] = Field(
        ..., description="Standard deviation confusion matrix"
    )

    # Individual reports for reference
    individual_reports: List[ValidationReport] = Field(
        ..., description="All individual validation reports"
    )

    # Metadata
    prompt_name: Optional[str] = Field(default=None, description="Name of prompt tested")
    prompt_version: Optional[str] = Field(default=None, description="Version of prompt tested")
    test_timestamp: datetime = Field(
        default_factory=datetime.now, description="When test was run"
    )


class AggregatedComparisonReport(BaseModel):
    """Comparison report with aggregated metrics over multiple iterations."""

    num_iterations: int = Field(..., description="Number of iterations per prompt")
    prompts_compared: List[str] = Field(..., description="List of prompt names compared")

    # Aggregated accuracy comparison
    aggregated_accuracy_comparison: Dict[str, Dict[str, float]] = Field(
        ..., description="Mean and std accuracy for each prompt"
    )

    # Individual aggregated reports per prompt
    per_prompt_reports: Dict[str, AggregatedValidationReport] = Field(
        ..., description="Aggregated report for each prompt"
    )

    winner: Optional[str] = Field(
        default=None, description="Best performing prompt (by mean accuracy)"
    )
    test_timestamp: datetime = Field(default_factory=datetime.now)


class Config(BaseModel):
    """Configuration for the testing framework."""

    ollama_endpoint: str = Field(default="http://localhost:11434", description="Ollama API endpoint")
    ollama_model: str = Field(default="llama3.2:3b", description="Ollama model to use")
    ollama_timeout: int = Field(default=30, description="Timeout in seconds")
    ollama_max_retries: int = Field(default=3, description="Maximum retry attempts")
    categories: List[str] = Field(
        default=[
            "contract_submission",
            "international_office_question",
            "internship_postponement",
            "uncategorized",
        ],
        description="Valid categories",
    )
    output_format: str = Field(default="both", description="Output format: json, csv, or both")
    output_directory: str = Field(default="results", description="Output directory")
    timestamp_format: str = Field(
        default="%Y%m%d_%H%M%S", description="Timestamp format for filenames"
    )
    include_confusion_matrix: bool = Field(
        default=True, description="Whether to include confusion matrix"
    )
    per_category_metrics: bool = Field(
        default=True, description="Whether to calculate per-category metrics"
    )

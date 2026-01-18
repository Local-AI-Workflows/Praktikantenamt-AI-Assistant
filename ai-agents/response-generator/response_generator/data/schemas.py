"""
Data models for response generator using Pydantic.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ResponseTone(str, Enum):
    """Tone of the generated response."""

    FORMAL = "formal"
    INFORMAL = "informal"


class EmailCategory(str, Enum):
    """Categories for email classification."""

    CONTRACT_SUBMISSION = "contract_submission"
    INTERNATIONAL_OFFICE = "international_office_question"
    POSTPONEMENT = "internship_postponement"
    UNCATEGORIZED = "uncategorized"


class CategorizedEmail(BaseModel):
    """Represents a categorized email ready for response generation."""

    id: str = Field(..., description="Unique email identifier")
    subject: str = Field(..., description="Email subject line")
    body: str = Field(..., description="Email body content")
    sender: str = Field(..., description="Email sender address")
    has_attachment: bool = Field(default=False, description="Whether email has attachments")
    category: EmailCategory = Field(..., description="Email category")
    categorization_confidence: Optional[float] = Field(
        default=None, description="Confidence score from categorization"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata"
    )


class CategorizedEmailDataset(BaseModel):
    """Container for categorized email dataset."""

    metadata: Dict[str, Any] = Field(..., description="Dataset metadata")
    emails: List[CategorizedEmail] = Field(..., description="List of categorized emails")


class ResponseTemplate(BaseModel):
    """Template for generating email responses."""

    category: EmailCategory = Field(..., description="Category this template is for")
    tone: ResponseTone = Field(..., description="Tone of the response")
    subject_template: str = Field(..., description="Subject line template")
    body_template: str = Field(..., description="Body content template")
    placeholders: List[str] = Field(
        default_factory=list, description="Available placeholders in template"
    )


class GeneratedResponse(BaseModel):
    """A single generated response for an email."""

    id: str = Field(..., description="Unique response identifier")
    email_id: str = Field(..., description="ID of the original email")
    tone: ResponseTone = Field(..., description="Tone of this response")
    subject: str = Field(..., description="Generated subject line")
    body: str = Field(..., description="Generated response body")
    confidence: float = Field(..., description="Confidence score for this response")
    template_used: str = Field(..., description="Name of template used")
    personalization_applied: bool = Field(
        default=False, description="Whether LLM personalization was applied"
    )
    generation_time: float = Field(..., description="Time taken to generate in seconds")
    raw_llm_output: Optional[str] = Field(
        default=None, description="Raw LLM output if personalization was used"
    )


class ResponseSuggestion(BaseModel):
    """Collection of response suggestions for a single email."""

    email_id: str = Field(..., description="ID of the original email")
    category: EmailCategory = Field(..., description="Category of the email")
    responses: List[GeneratedResponse] = Field(
        default_factory=list, description="List of generated responses"
    )
    recommended_response_id: str = Field(
        ..., description="ID of the recommended response"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="When suggestions were generated"
    )

    def to_n8n_output(self) -> Dict[str, Any]:
        """Convert to n8n-compatible output format."""
        return {
            "email_id": self.email_id,
            "category": self.category.value,
            "recommended_response_id": self.recommended_response_id,
            "responses": [
                {
                    "id": r.id,
                    "tone": r.tone.value,
                    "subject": r.subject,
                    "body": r.body,
                    "confidence": r.confidence,
                }
                for r in self.responses
            ],
        }


class QualityMetrics(BaseModel):
    """Quality metrics for evaluating a generated response."""

    relevance_score: float = Field(
        ..., ge=0.0, le=1.0, description="How relevant the response is to the email"
    )
    completeness_score: float = Field(
        ..., ge=0.0, le=1.0, description="How complete the response is"
    )
    tone_appropriateness: float = Field(
        ..., ge=0.0, le=1.0, description="How appropriate the tone is"
    )
    grammar_score: float = Field(
        ..., ge=0.0, le=1.0, description="Grammar and spelling quality"
    )
    overall_score: float = Field(
        ..., ge=0.0, le=1.0, description="Overall quality score"
    )


class EvaluationResult(BaseModel):
    """Result of evaluating a single generated response."""

    email_id: str = Field(..., description="ID of the original email")
    response_id: str = Field(..., description="ID of the evaluated response")
    generated_response: GeneratedResponse = Field(
        ..., description="The generated response being evaluated"
    )
    expected_response: Optional[str] = Field(
        default=None, description="Expected/reference response if available"
    )
    metrics: QualityMetrics = Field(..., description="Quality metrics")
    passed: bool = Field(..., description="Whether the response passed quality threshold")
    feedback: List[str] = Field(
        default_factory=list, description="Feedback messages"
    )


class EvaluationReport(BaseModel):
    """Complete evaluation report for response generation."""

    total_emails: int = Field(..., description="Total number of emails evaluated")
    total_responses: int = Field(..., description="Total number of responses generated")
    average_confidence: float = Field(..., description="Average confidence score")
    average_quality: float = Field(..., description="Average quality score")
    pass_rate: float = Field(..., description="Percentage of responses that passed")
    per_category_stats: Dict[str, Dict[str, float]] = Field(
        ..., description="Statistics per category"
    )
    per_tone_stats: Dict[str, Dict[str, float]] = Field(
        ..., description="Statistics per tone"
    )
    results: List[EvaluationResult] = Field(..., description="Individual evaluation results")
    prompt_name: str = Field(..., description="Name of personalization prompt used")
    test_timestamp: datetime = Field(
        default_factory=datetime.now, description="When evaluation was run"
    )


class ComparisonReport(BaseModel):
    """Report comparing multiple template sets or prompts."""

    templates_compared: List[str] = Field(
        ..., description="List of template sets compared"
    )
    quality_comparison: Dict[str, float] = Field(
        ..., description="Average quality for each template set"
    )
    per_category_comparison: Dict[str, Dict[str, float]] = Field(
        ..., description="Quality scores per category per template set"
    )
    winner: Optional[str] = Field(default=None, description="Best performing template set")
    test_timestamp: datetime = Field(
        default_factory=datetime.now, description="When comparison was run"
    )


class Config(BaseModel):
    """Configuration for the response generator."""

    ollama_endpoint: str = Field(
        default="http://localhost:11434", description="Ollama API endpoint"
    )
    ollama_model: str = Field(default="llama3.2:3b", description="Ollama model to use")
    ollama_timeout: int = Field(default=30, description="Timeout in seconds")
    ollama_max_retries: int = Field(default=3, description="Maximum retry attempts")
    categories: List[str] = Field(
        default_factory=lambda: [
            "contract_submission",
            "international_office_question",
            "internship_postponement",
            "uncategorized",
        ],
        description="Valid categories",
    )
    default_tone: str = Field(default="formal", description="Default response tone")
    generate_both_tones: bool = Field(
        default=True, description="Generate both formal and informal responses"
    )
    personalization_enabled: bool = Field(
        default=True, description="Enable LLM personalization"
    )
    confidence_threshold: float = Field(
        default=0.7, description="Minimum confidence threshold"
    )
    quality_threshold: float = Field(
        default=0.6, description="Minimum quality threshold for passing"
    )
    output_format: str = Field(default="json", description="Output format: json or csv")
    output_directory: str = Field(default="results", description="Output directory")
    timestamp_format: str = Field(
        default="%Y%m%d_%H%M%S", description="Timestamp format for filenames"
    )
    templates_directory: str = Field(
        default="templates", description="Directory containing templates"
    )
    prompts_directory: str = Field(
        default="prompts", description="Directory containing prompts"
    )

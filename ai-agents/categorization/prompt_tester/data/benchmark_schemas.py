"""
Pydantic models for the multi-model benchmark runner.
"""

from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from prompt_tester.data.schemas import AggregatedValidationReport


class ModelConfig(BaseModel):
    """Configuration for a single model in the benchmark."""

    model_id: str = Field(..., description="Model identifier, e.g. 'llama3.1:8b' or 'gpt-4.1-mini'")
    provider: Literal["ollama", "openai", "anthropic"] = Field(
        ..., description="LLM provider"
    )
    display_name: Optional[str] = Field(
        default=None, description="Human-readable label for tables. Defaults to model_id."
    )
    enabled: bool = Field(default=True, description="Set to false to skip this model")

    # Ollama-specific (ignored for API models)
    endpoint: Optional[str] = Field(
        default=None,
        description="Ollama endpoint URL. Falls back to OLLAMA_ENDPOINT env var or config default.",
    )
    timeout: int = Field(default=90, description="Request timeout in seconds (Ollama only)")
    max_retries: int = Field(default=3, description="Max retry attempts (Ollama only)")

    # API model options (ignored for Ollama)
    max_tokens: int = Field(
        default=50, description="Max tokens in completion (API models only)"
    )
    temperature: float = Field(
        default=0.0, description="Sampling temperature 0.0=deterministic (API models only)"
    )

    @property
    def label(self) -> str:
        """Return display_name if set, otherwise model_id."""
        return self.display_name or self.model_id


class ModelBenchmarkStatus(BaseModel):
    """Live status entry for the progress summary table (updated during run)."""

    model_id: str
    display_name: str
    provider: str
    status: Literal["pending", "running", "done", "error"] = "pending"
    current_iteration: int = 0
    total_iterations: int = 5
    mean_accuracy: Optional[float] = None
    std_accuracy: Optional[float] = None
    mean_execution_time_ms: Optional[float] = None
    error_message: Optional[str] = None


class BenchmarkModelResult(BaseModel):
    """Final result for a single model after all iterations."""

    model_id: str
    display_name: str
    provider: str
    status: Literal["success", "error"] = Field(..., description="'success' or 'error'")
    error_message: Optional[str] = Field(
        default=None, description="Error details if status='error'"
    )
    aggregated_report: Optional[AggregatedValidationReport] = Field(
        default=None, description="Full aggregated stats; None if status='error'"
    )


class BenchmarkRankEntry(BaseModel):
    """One row in the final rankings table."""

    rank: int
    model_id: str
    display_name: str
    provider: str
    mean_accuracy: float
    std_accuracy: float
    mean_execution_time_ms: float
    mean_parse_errors: float


class BenchmarkReport(BaseModel):
    """Top-level benchmark result across all models."""

    benchmark_timestamp: datetime = Field(default_factory=datetime.now)
    prompt_name: str
    prompt_user_file: str
    prompt_system_file: str
    num_iterations: int
    total_emails: int
    total_models_attempted: int
    total_models_succeeded: int
    model_results: Dict[str, BenchmarkModelResult] = Field(
        ..., description="Keyed by model_id"
    )
    rankings: List[BenchmarkRankEntry] = Field(
        ..., description="Succeeded models sorted by mean_accuracy desc"
    )
    winner: Optional[str] = Field(
        default=None, description="model_id of the top performer"
    )

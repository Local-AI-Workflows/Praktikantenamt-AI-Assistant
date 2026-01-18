"""
Data layer for response generator.
"""

from response_generator.data.loader import DataLoader, TemplateLoader
from response_generator.data.schemas import (
    CategorizedEmail,
    CategorizedEmailDataset,
    ComparisonReport,
    Config,
    EmailCategory,
    EvaluationReport,
    EvaluationResult,
    GeneratedResponse,
    QualityMetrics,
    ResponseSuggestion,
    ResponseTemplate,
    ResponseTone,
)

__all__ = [
    "CategorizedEmail",
    "CategorizedEmailDataset",
    "ComparisonReport",
    "Config",
    "DataLoader",
    "EmailCategory",
    "EvaluationReport",
    "EvaluationResult",
    "GeneratedResponse",
    "QualityMetrics",
    "ResponseSuggestion",
    "ResponseTemplate",
    "ResponseTone",
    "TemplateLoader",
]

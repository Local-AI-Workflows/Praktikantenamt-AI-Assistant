"""
Export results to files (JSON and CSV formats).
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from response_generator.data.schemas import (
    ComparisonReport,
    EvaluationReport,
    GeneratedResponse,
    ResponseSuggestion,
)


class ResultExporter:
    """Exports generation and evaluation results to various file formats."""

    def __init__(
        self,
        output_directory: str = "results",
        timestamp_format: str = "%Y%m%d_%H%M%S",
    ):
        """
        Initialize result exporter.

        Args:
            output_directory: Directory to save results
            timestamp_format: Format for timestamps in filenames
        """
        self.output_directory = Path(output_directory)
        self.timestamp_format = timestamp_format

        # Ensure output directory exists
        self.output_directory.mkdir(parents=True, exist_ok=True)

    def export_suggestions(
        self,
        suggestions: List[ResponseSuggestion],
        file_path: Optional[str] = None,
    ) -> str:
        """
        Export response suggestions to JSON file.

        Args:
            suggestions: List of ResponseSuggestion objects
            file_path: Optional file path. If not provided, auto-generates.

        Returns:
            Path to exported file
        """
        if file_path is None:
            timestamp = datetime.now().strftime(self.timestamp_format)
            file_path = self.output_directory / f"suggestions_{timestamp}.json"
        else:
            file_path = Path(file_path)

        # Convert suggestions to dict
        data = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "total_suggestions": len(suggestions),
            },
            "suggestions": [
                {
                    "email_id": s.email_id,
                    "category": s.category.value,
                    "recommended_response_id": s.recommended_response_id,
                    "timestamp": s.timestamp.isoformat(),
                    "responses": [
                        {
                            "id": r.id,
                            "tone": r.tone.value,
                            "subject": r.subject,
                            "body": r.body,
                            "confidence": r.confidence,
                            "template_used": r.template_used,
                            "personalization_applied": r.personalization_applied,
                            "generation_time": r.generation_time,
                        }
                        for r in s.responses
                    ],
                }
                for s in suggestions
            ],
        }

        # Write to file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return str(file_path)

    def export_evaluation(
        self,
        report: EvaluationReport,
        file_path: Optional[str] = None,
    ) -> str:
        """
        Export evaluation report to JSON file.

        Args:
            report: EvaluationReport to export
            file_path: Optional file path. If not provided, auto-generates.

        Returns:
            Path to exported file
        """
        if file_path is None:
            timestamp = datetime.now().strftime(self.timestamp_format)
            file_path = self.output_directory / f"evaluation_{report.prompt_name}_{timestamp}.json"
        else:
            file_path = Path(file_path)

        # Convert report to dict
        data = {
            "metadata": {
                "timestamp": report.test_timestamp.isoformat(),
                "prompt_name": report.prompt_name,
                "total_emails": report.total_emails,
                "total_responses": report.total_responses,
            },
            "summary": {
                "average_confidence": report.average_confidence,
                "average_quality": report.average_quality,
                "pass_rate": report.pass_rate,
            },
            "per_category_stats": report.per_category_stats,
            "per_tone_stats": report.per_tone_stats,
            "results": [
                {
                    "email_id": r.email_id,
                    "response_id": r.response_id,
                    "tone": r.generated_response.tone.value,
                    "passed": r.passed,
                    "metrics": {
                        "relevance_score": r.metrics.relevance_score,
                        "completeness_score": r.metrics.completeness_score,
                        "tone_appropriateness": r.metrics.tone_appropriateness,
                        "grammar_score": r.metrics.grammar_score,
                        "overall_score": r.metrics.overall_score,
                    },
                    "feedback": r.feedback,
                }
                for r in report.results
            ],
        }

        # Write to file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return str(file_path)

    def export_comparison(
        self,
        report: ComparisonReport,
        file_path: Optional[str] = None,
    ) -> str:
        """
        Export comparison report to JSON file.

        Args:
            report: ComparisonReport to export
            file_path: Optional file path. If not provided, auto-generates.

        Returns:
            Path to exported file
        """
        if file_path is None:
            timestamp = datetime.now().strftime(self.timestamp_format)
            file_path = self.output_directory / f"comparison_{timestamp}.json"
        else:
            file_path = Path(file_path)

        # Convert report to dict
        data = {
            "metadata": {
                "timestamp": report.test_timestamp.isoformat(),
                "templates_compared": report.templates_compared,
                "winner": report.winner,
            },
            "quality_comparison": report.quality_comparison,
            "per_category_comparison": report.per_category_comparison,
        }

        # Write to file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return str(file_path)

    def export_responses_csv(
        self,
        suggestions: List[ResponseSuggestion],
        file_path: Optional[str] = None,
    ) -> str:
        """
        Export responses to CSV file.

        Args:
            suggestions: List of ResponseSuggestion objects
            file_path: Optional file path. If not provided, auto-generates.

        Returns:
            Path to exported file
        """
        if file_path is None:
            timestamp = datetime.now().strftime(self.timestamp_format)
            file_path = self.output_directory / f"responses_{timestamp}.csv"
        else:
            file_path = Path(file_path)

        # Write CSV
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                "email_id",
                "category",
                "tone",
                "subject",
                "body",
                "confidence",
                "template_used",
                "personalization_applied",
                "is_recommended",
            ])

            # Data rows
            for suggestion in suggestions:
                for response in suggestion.responses:
                    writer.writerow([
                        suggestion.email_id,
                        suggestion.category.value,
                        response.tone.value,
                        response.subject,
                        response.body.replace("\n", " "),  # Remove newlines for CSV
                        f"{response.confidence:.3f}",
                        response.template_used,
                        response.personalization_applied,
                        response.id == suggestion.recommended_response_id,
                    ])

        return str(file_path)

    def export_n8n_format(
        self,
        suggestions: List[ResponseSuggestion],
        file_path: Optional[str] = None,
    ) -> str:
        """
        Export suggestions in n8n-compatible format.

        Args:
            suggestions: List of ResponseSuggestion objects
            file_path: Optional file path. If not provided, auto-generates.

        Returns:
            Path to exported file
        """
        if file_path is None:
            timestamp = datetime.now().strftime(self.timestamp_format)
            file_path = self.output_directory / f"n8n_output_{timestamp}.json"
        else:
            file_path = Path(file_path)

        # Convert to n8n format
        n8n_output = [s.to_n8n_output() for s in suggestions]

        # Write to file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(n8n_output, f, indent=2, ensure_ascii=False)

        return str(file_path)

    def export_all(
        self,
        suggestions: List[ResponseSuggestion],
        report: Optional[EvaluationReport] = None,
        prefix: str = None,
    ) -> dict:
        """
        Export all formats at once.

        Args:
            suggestions: List of ResponseSuggestion objects
            report: Optional EvaluationReport
            prefix: Optional filename prefix

        Returns:
            Dictionary with paths to all exported files
        """
        timestamp = datetime.now().strftime(self.timestamp_format)
        prefix = prefix or "response_gen"

        paths = {}

        # Export suggestions JSON
        json_path = self.output_directory / f"{prefix}_{timestamp}.json"
        paths["json"] = self.export_suggestions(suggestions, str(json_path))

        # Export CSV
        csv_path = self.output_directory / f"{prefix}_{timestamp}.csv"
        paths["csv"] = self.export_responses_csv(suggestions, str(csv_path))

        # Export n8n format
        n8n_path = self.output_directory / f"{prefix}_n8n_{timestamp}.json"
        paths["n8n"] = self.export_n8n_format(suggestions, str(n8n_path))

        # Export evaluation if provided
        if report:
            eval_path = self.output_directory / f"{prefix}_eval_{timestamp}.json"
            paths["evaluation"] = self.export_evaluation(report, str(eval_path))

        return paths

"""
Export results to files (JSON and CSV formats).
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import List

from contract_validator.data.schemas import (
    ComparisonReport,
    ExtractionResult,
    ValidationReport,
    ValidationResult,
)


class ResultExporter:
    """Exports test results to various file formats."""

    def __init__(
        self, output_directory: str = "results", timestamp_format: str = "%Y%m%d_%H%M%S"
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

    def export_json(self, report: ValidationReport, file_path: str = None) -> str:
        """
        Export validation report to JSON file.

        Args:
            report: ValidationReport to export
            file_path: Optional file path. If not provided, auto-generates.

        Returns:
            Path to exported file
        """
        if file_path is None:
            timestamp = datetime.now().strftime(self.timestamp_format)
            prompt_name = report.prompt_name or "unknown"
            file_path = self.output_directory / f"test_{prompt_name}_{timestamp}.json"
        else:
            file_path = Path(file_path)

        # Convert report to dict
        report_dict = {
            "test_metadata": {
                "timestamp": report.test_timestamp.isoformat(),
                "prompt_name": report.prompt_name,
                "total_contracts": report.total_contracts,
            },
            "extraction_metrics": {
                "total_contracts": report.extraction_metrics.total_contracts,
                "student_name_accuracy": report.extraction_metrics.student_name_accuracy,
                "matrikelnummer_accuracy": report.extraction_metrics.matrikelnummer_accuracy,
                "company_name_accuracy": report.extraction_metrics.company_name_accuracy,
                "start_date_accuracy": report.extraction_metrics.start_date_accuracy,
                "end_date_accuracy": report.extraction_metrics.end_date_accuracy,
                "overall_accuracy": report.extraction_metrics.overall_accuracy,
                "per_format_accuracy": report.extraction_metrics.per_format_accuracy,
            },
            "validation_metrics": {
                "validation_accuracy": report.validation_accuracy,
                "per_status_accuracy": report.per_status_accuracy,
            },
            "extraction_results": [
                {
                    "contract_id": r.contract_id,
                    "extracted": {
                        "student_name": r.extracted.student_name,
                        "matrikelnummer": r.extracted.matrikelnummer,
                        "company_name": r.extracted.company_name,
                        "company_address": r.extracted.company_address,
                        "start_date": str(r.extracted.start_date) if r.extracted.start_date else None,
                        "end_date": str(r.extracted.end_date) if r.extracted.end_date else None,
                    },
                    "student_name_correct": r.student_name_correct,
                    "matrikelnummer_correct": r.matrikelnummer_correct,
                    "company_name_correct": r.company_name_correct,
                    "start_date_correct": r.start_date_correct,
                    "end_date_correct": r.end_date_correct,
                    "all_correct": r.all_correct,
                    "execution_time": r.execution_time,
                }
                for r in report.results
            ],
            "validation_results": [
                {
                    "contract_id": r.contract_id,
                    "status": r.status.value,
                    "expected_status": r.expected_status.value,
                    "is_correct": r.is_correct,
                    "calculated_working_days": r.calculated_working_days,
                    "issues": r.issues,
                }
                for r in report.validation_results
            ],
        }

        # Write to file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)

        return str(file_path)

    def export_csv(self, results: List[ExtractionResult], file_path: str = None) -> str:
        """
        Export extraction results to CSV file.

        Args:
            results: List of ExtractionResult objects to export
            file_path: Optional file path. If not provided, auto-generates.

        Returns:
            Path to exported file
        """
        if file_path is None:
            timestamp = datetime.now().strftime(self.timestamp_format)
            file_path = self.output_directory / f"results_{timestamp}.csv"
        else:
            file_path = Path(file_path)

        # Write CSV
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                "contract_id",
                "student_name_extracted",
                "student_name_expected",
                "student_name_correct",
                "matrikelnummer_extracted",
                "matrikelnummer_expected",
                "matrikelnummer_correct",
                "company_name_extracted",
                "company_name_expected",
                "company_name_correct",
                "start_date_extracted",
                "start_date_expected",
                "start_date_correct",
                "end_date_extracted",
                "end_date_expected",
                "end_date_correct",
                "all_correct",
                "execution_time",
            ])

            # Data rows
            for r in results:
                writer.writerow([
                    r.contract_id,
                    r.extracted.student_name or "",
                    r.expected.student_name,
                    r.student_name_correct,
                    r.extracted.matrikelnummer or "",
                    r.expected.matrikelnummer,
                    r.matrikelnummer_correct,
                    r.extracted.company_name or "",
                    r.expected.company_name,
                    r.company_name_correct,
                    str(r.extracted.start_date) if r.extracted.start_date else "",
                    str(r.expected.start_date),
                    r.start_date_correct,
                    str(r.extracted.end_date) if r.extracted.end_date else "",
                    str(r.expected.end_date),
                    r.end_date_correct,
                    r.all_correct,
                    f"{r.execution_time:.3f}",
                ])

        return str(file_path)

    def export_comparison(self, report: ComparisonReport, file_path: str = None) -> str:
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
            prompts_str = "_vs_".join(report.prompts_compared[:2])
            file_path = self.output_directory / f"comparison_{prompts_str}_{timestamp}.json"
        else:
            file_path = Path(file_path)

        # Convert report to dict
        report_dict = {
            "test_metadata": {
                "timestamp": report.test_timestamp.isoformat(),
                "prompts_compared": report.prompts_compared,
                "winner": report.winner,
            },
            "extraction_accuracy_comparison": report.extraction_accuracy_comparison,
            "validation_accuracy_comparison": report.validation_accuracy_comparison,
            "per_format_comparison": report.per_format_comparison,
        }

        # Write to file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)

        return str(file_path)

    def export_both(
        self, report: ValidationReport, results: List[ExtractionResult], prefix: str = None
    ) -> tuple:
        """
        Export both JSON and CSV formats.

        Args:
            report: ValidationReport to export
            results: List of ExtractionResult objects for CSV
            prefix: Optional filename prefix

        Returns:
            Tuple of (json_path, csv_path)
        """
        timestamp = datetime.now().strftime(self.timestamp_format)
        prompt_name = report.prompt_name or "unknown"

        if prefix:
            json_file = self.output_directory / f"{prefix}_{timestamp}.json"
            csv_file = self.output_directory / f"{prefix}_{timestamp}.csv"
        else:
            json_file = self.output_directory / f"test_{prompt_name}_{timestamp}.json"
            csv_file = self.output_directory / f"results_{prompt_name}_{timestamp}.csv"

        json_path = self.export_json(report, str(json_file))
        csv_path = self.export_csv(results, str(csv_file))

        return (json_path, csv_path)

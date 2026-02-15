"""
Export results to files (JSON and CSV formats).
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import List

from prompt_tester.data.schemas import (
    AggregatedComparisonReport,
    AggregatedValidationReport,
    ComparisonReport,
    Result,
    ValidationReport,
)


class ResultExporter:
    """Exports test results to various file formats."""

    def __init__(self, output_directory: str = "results", timestamp_format: str = "%Y%m%d_%H%M%S"):
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

    def export_json(
        self, report: ValidationReport, file_path: str = None
    ) -> str:
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
                "prompt_version": report.prompt_version,
                "total_emails": report.total_emails,
            },
            "metrics": {
                "overall_accuracy": report.overall_accuracy,
                "correct_predictions": report.correct_predictions,
                "incorrect_predictions": report.incorrect_predictions,
            },
            "per_category_metrics": {
                category: {
                    "precision": metrics.precision,
                    "recall": metrics.recall,
                    "f1_score": metrics.f1_score,
                    "support": metrics.support,
                }
                for category, metrics in report.per_category_metrics.items()
            },
            "confusion_matrix": report.confusion_matrix,
            "misclassifications": [
                {
                    "email_id": result.email_id,
                    "expected_category": result.expected_category,
                    "predicted_category": result.predicted_category,
                    "raw_response": result.raw_response,
                    "execution_time": result.execution_time,
                }
                for result in report.misclassifications
            ],
        }

        # Write to file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)

        return str(file_path)

    def export_csv(
        self, results: List[Result], file_path: str = None
    ) -> str:
        """
        Export results to CSV file.

        Args:
            results: List of Result objects to export
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
                "email_id",
                "expected_category",
                "predicted_category",
                "correct",
                "execution_time",
                "raw_response",
            ])

            # Data rows
            for result in results:
                writer.writerow([
                    result.email_id,
                    result.expected_category,
                    result.predicted_category,
                    result.is_correct,
                    f"{result.execution_time:.3f}",
                    result.raw_response.replace("\n", " "),  # Remove newlines for CSV
                ])

        return str(file_path)

    def export_comparison(
        self, report: ComparisonReport, file_path: str = None
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
            prompts_str = "_vs_".join(report.prompts_compared[:2])  # First 2 prompts
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
            "accuracy_comparison": report.accuracy_comparison,
            "disagreements": [
                {
                    "email_id": d.email_id,
                    "prompt_a_prediction": d.prompt_a_prediction,
                    "prompt_b_prediction": d.prompt_b_prediction,
                    "expected_category": d.expected_category,
                    "prompt_a_correct": d.prompt_a_correct,
                    "prompt_b_correct": d.prompt_b_correct,
                    "prompt_a_raw_response": d.prompt_a_raw_response,
                    "prompt_b_raw_response": d.prompt_b_raw_response,
                }
                for d in report.disagreements
            ],
        }

        # Write to file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)

        return str(file_path)

    def export_both(
        self, report: ValidationReport, results: List[Result], prefix: str = None
    ) -> tuple:
        """
        Export both JSON and CSV formats.

        Args:
            report: ValidationReport to export
            results: List of Result objects for CSV
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

    def export_aggregated_json(
        self, report: AggregatedValidationReport, file_path: str = None
    ) -> str:
        """
        Export aggregated validation report to JSON file.

        Args:
            report: AggregatedValidationReport to export
            file_path: Optional file path. If not provided, auto-generates.

        Returns:
            Path to exported file
        """
        if file_path is None:
            timestamp = datetime.now().strftime(self.timestamp_format)
            prompt_name = report.prompt_name or "unknown"
            file_path = self.output_directory / (
                f"aggregated_{prompt_name}_{report.num_iterations}runs_{timestamp}.json"
            )
        else:
            file_path = Path(file_path)

        # Convert report to dict
        report_dict = {
            "test_metadata": {
                "timestamp": report.test_timestamp.isoformat(),
                "prompt_name": report.prompt_name,
                "prompt_version": report.prompt_version,
                "num_iterations": report.num_iterations,
            },
            "aggregated_metrics": {
                "mean_accuracy": report.mean_accuracy,
                "std_accuracy": report.std_accuracy,
            },
            "per_category_metrics": {
                category: {
                    "mean_precision": metrics.mean_precision,
                    "std_precision": metrics.std_precision,
                    "mean_recall": metrics.mean_recall,
                    "std_recall": metrics.std_recall,
                    "mean_f1_score": metrics.mean_f1_score,
                    "std_f1_score": metrics.std_f1_score,
                    "support": metrics.support,
                }
                for category, metrics in report.per_category_metrics.items()
            },
            "confusion_matrices": {
                "aggregated": report.aggregated_confusion_matrix,
                "std_dev": report.std_confusion_matrix,
                "individual": report.confusion_matrices,
            },
            "individual_reports": [
                {
                    "iteration": i + 1,
                    "accuracy": r.overall_accuracy,
                    "timestamp": r.test_timestamp.isoformat(),
                }
                for i, r in enumerate(report.individual_reports)
            ],
        }

        # Write to file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)

        return str(file_path)

    def export_aggregated_comparison(
        self, report: AggregatedComparisonReport, file_path: str = None
    ) -> str:
        """
        Export aggregated comparison report to JSON file.

        Args:
            report: AggregatedComparisonReport to export
            file_path: Optional file path. If not provided, auto-generates.

        Returns:
            Path to exported file
        """
        if file_path is None:
            timestamp = datetime.now().strftime(self.timestamp_format)
            prompts_str = "_vs_".join(report.prompts_compared[:2])
            file_path = self.output_directory / (
                f"aggregated_comparison_{prompts_str}_{report.num_iterations}runs_{timestamp}.json"
            )
        else:
            file_path = Path(file_path)

        # Convert report to dict
        report_dict = {
            "test_metadata": {
                "timestamp": report.test_timestamp.isoformat(),
                "prompts_compared": report.prompts_compared,
                "num_iterations": report.num_iterations,
                "winner": report.winner,
            },
            "aggregated_accuracy_comparison": report.aggregated_accuracy_comparison,
            "per_prompt_reports": {
                prompt_name: {
                    "mean_accuracy": report_obj.mean_accuracy,
                    "std_accuracy": report_obj.std_accuracy,
                    "per_category_metrics": {
                        cat: {
                            "mean_precision": metrics.mean_precision,
                            "std_precision": metrics.std_precision,
                            "mean_recall": metrics.mean_recall,
                            "std_recall": metrics.std_recall,
                            "mean_f1_score": metrics.mean_f1_score,
                            "std_f1_score": metrics.std_f1_score,
                            "support": metrics.support,
                        }
                        for cat, metrics in report_obj.per_category_metrics.items()
                    },
                }
                for prompt_name, report_obj in report.per_prompt_reports.items()
            },
        }

        # Write to file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)

        return str(file_path)

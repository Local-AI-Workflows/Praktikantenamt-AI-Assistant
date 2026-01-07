"""
Result export to JSON and CSV.
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Tuple

from workflow_validator.data.schemas import WorkflowValidationReport


class ResultExporter:
    """Exports validation results to JSON and CSV."""

    def __init__(self, output_directory: str, timestamp_format: str = "%Y%m%d_%H%M%S"):
        """
        Initialize result exporter.

        Args:
            output_directory: Directory for output files
            timestamp_format: Format for timestamps in filenames
        """
        self.output_directory = Path(output_directory)
        self.timestamp_format = timestamp_format
        self.output_directory.mkdir(parents=True, exist_ok=True)

    def export_workflow_validation(
        self, report: WorkflowValidationReport, output_format: str = "both"
    ) -> Tuple[str, str]:
        """
        Export workflow validation report.

        Args:
            report: Validation report to export
            output_format: "json", "csv", or "both"

        Returns:
            Tuple of (json_path, csv_path) - empty strings if not exported
        """
        timestamp = datetime.now().strftime(self.timestamp_format)

        json_path = ""
        csv_path = ""

        if output_format in ["json", "both"]:
            json_path = self._export_json(report, timestamp)

        if output_format in ["csv", "both"]:
            csv_path = self._export_csv(report, timestamp)

        return json_path, csv_path

    def _export_json(self, report: WorkflowValidationReport, timestamp: str) -> str:
        """
        Export report to JSON.

        Args:
            report: Validation report
            timestamp: Timestamp string

        Returns:
            Path to JSON file
        """
        filename = f"workflow_validation_{timestamp}.json"
        filepath = self.output_directory / filename

        # Convert report to dict
        data = report.model_dump(mode="json")

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        return str(filepath)

    def _export_csv(self, report: WorkflowValidationReport, timestamp: str) -> str:
        """
        Export email locations to CSV.

        Args:
            report: Validation report
            timestamp: Timestamp string

        Returns:
            Path to CSV file
        """
        filename = f"email_locations_{timestamp}.csv"
        filepath = self.output_directory / filename

        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)

            # Header
            writer.writerow(
                [
                    "uuid",
                    "email_id",
                    "found_in_folder",
                    "expected_category",
                    "predicted_category",
                    "is_correct",
                    "validation_timestamp",
                ]
            )

            # Data rows
            for location in report.email_locations:
                writer.writerow(
                    [
                        str(location.uuid),
                        location.email_id,
                        location.found_in_folder or "NOT_FOUND",
                        location.expected_category,
                        location.predicted_category or "NOT_FOUND",
                        location.is_correct,
                        location.validation_timestamp.isoformat(),
                    ]
                )

        return str(filepath)

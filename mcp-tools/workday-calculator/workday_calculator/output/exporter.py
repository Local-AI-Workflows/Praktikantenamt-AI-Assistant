"""
Export functionality for workday calculation results.
"""

import csv
import json
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional, Tuple

from workday_calculator.data.schemas import Holiday, WorkdayResult


class ResultExporter:
    """Exports workday calculation results to various formats."""

    def __init__(
        self,
        output_directory: str = "results",
        timestamp_format: str = "%Y%m%d_%H%M%S",
    ):
        """
        Initialize the result exporter.

        Args:
            output_directory: Directory for output files.
            timestamp_format: Format string for timestamps in filenames.
        """
        self.output_directory = output_directory
        self.timestamp_format = timestamp_format

    def _ensure_output_dir(self) -> Path:
        """Ensure output directory exists and return path."""
        output_path = Path(self.output_directory)
        output_path.mkdir(parents=True, exist_ok=True)
        return output_path

    def _generate_filename(self, prefix: str, extension: str) -> str:
        """Generate a filename with timestamp."""
        timestamp = datetime.now().strftime(self.timestamp_format)
        return f"{prefix}_{timestamp}.{extension}"

    def export_json(
        self, result: WorkdayResult, output_path: Optional[str] = None
    ) -> str:
        """
        Export result to JSON file.

        Args:
            result: WorkdayResult to export.
            output_path: Optional specific output path.

        Returns:
            Path to the exported file.
        """
        if output_path:
            file_path = Path(output_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            output_dir = self._ensure_output_dir()
            filename = self._generate_filename("workdays", "json")
            file_path = output_dir / filename

        # Convert result to JSON-serializable dict
        result_dict = self._result_to_dict(result)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(result_dict, f, indent=2, ensure_ascii=False)

        return str(file_path)

    def export_csv(
        self, result: WorkdayResult, output_path: Optional[str] = None
    ) -> str:
        """
        Export result to CSV file.

        Args:
            result: WorkdayResult to export.
            output_path: Optional specific output path.

        Returns:
            Path to the exported file.
        """
        if output_path:
            file_path = Path(output_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            output_dir = self._ensure_output_dir()
            filename = self._generate_filename("workdays", "csv")
            file_path = output_dir / filename

        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # Write header
            writer.writerow([
                "Start Date",
                "End Date",
                "Bundesland",
                "Bundesland Name",
                "Calendar Days",
                "Weekend Days",
                "Saturdays",
                "Sundays",
                "Holidays Count",
                "Working Days",
                "Confidence",
                "Resolution Method",
            ])

            # Write data
            writer.writerow([
                result.start_date.isoformat(),
                result.end_date.isoformat(),
                result.location.bundesland.value,
                result.location.bundesland_name,
                result.calendar_days,
                result.weekend_days,
                result.weekends_detail.get("saturdays", 0),
                result.weekends_detail.get("sundays", 0),
                result.holidays_count,
                result.working_days,
                result.confidence,
                result.location.resolution_method,
            ])

        return str(file_path)

    def export_holidays_csv(
        self, holidays: List[Holiday], output_path: Optional[str] = None
    ) -> str:
        """
        Export holidays list to CSV file.

        Args:
            holidays: List of holidays to export.
            output_path: Optional specific output path.

        Returns:
            Path to the exported file.
        """
        if output_path:
            file_path = Path(output_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            output_dir = self._ensure_output_dir()
            filename = self._generate_filename("holidays", "csv")
            file_path = output_dir / filename

        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # Write header
            writer.writerow(["Date", "Name", "Is National"])

            # Write data
            for holiday in holidays:
                writer.writerow([
                    holiday.date.isoformat(),
                    holiday.name,
                    holiday.is_national,
                ])

        return str(file_path)

    def export_both(
        self, result: WorkdayResult
    ) -> Tuple[str, str]:
        """
        Export result to both JSON and CSV.

        Args:
            result: WorkdayResult to export.

        Returns:
            Tuple of (json_path, csv_path).
        """
        json_path = self.export_json(result)
        csv_path = self.export_csv(result)
        return json_path, csv_path

    def _result_to_dict(self, result: WorkdayResult) -> dict:
        """
        Convert WorkdayResult to a JSON-serializable dictionary.

        Args:
            result: WorkdayResult to convert.

        Returns:
            Dictionary representation.
        """
        return {
            "start_date": result.start_date.isoformat(),
            "end_date": result.end_date.isoformat(),
            "location": {
                "bundesland": result.location.bundesland.value,
                "bundesland_name": result.location.bundesland_name,
                "confidence": result.location.confidence,
                "resolution_method": result.location.resolution_method,
            },
            "calculation": {
                "calendar_days": result.calendar_days,
                "weekend_days": result.weekend_days,
                "weekends_detail": result.weekends_detail,
                "holidays_count": result.holidays_count,
                "working_days": result.working_days,
            },
            "holidays": [
                {
                    "date": h.date.isoformat(),
                    "name": h.name,
                    "is_national": h.is_national,
                }
                for h in result.holidays
            ],
            "metadata": {
                "calculation_timestamp": result.calculation_timestamp.isoformat(),
                "confidence": result.confidence,
                "warnings": result.warnings,
            },
        }

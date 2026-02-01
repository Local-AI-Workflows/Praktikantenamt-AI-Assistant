"""Export functionality for lookup results."""

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from company_lookup.data.schemas import CompanyInfo, CompanyListStats, LookupResult

logger = logging.getLogger(__name__)


class ResultExporter:
    """Exports lookup results to various formats."""

    def __init__(self, output_directory: str = "results"):
        """Initialize the exporter.

        Args:
            output_directory: Directory for output files.
        """
        self.output_directory = Path(output_directory)
        self.output_directory.mkdir(parents=True, exist_ok=True)

    def export_result(
        self,
        result: LookupResult,
        format: str = "json",
        filename: Optional[str] = None,
    ) -> str:
        """Export a lookup result to file.

        Args:
            result: The result to export.
            format: Output format ('json' or 'csv').
            filename: Custom filename (auto-generated if not provided).

        Returns:
            Path to the exported file.
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_query = "".join(c if c.isalnum() else "_" for c in result.query[:20])
            filename = f"lookup_{safe_query}_{timestamp}"

        if format.lower() == "json":
            return self._export_result_json(result, filename)
        elif format.lower() == "csv":
            return self._export_result_csv(result, filename)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _export_result_json(self, result: LookupResult, filename: str) -> str:
        """Export result to JSON.

        Args:
            result: The result to export.
            filename: Base filename (without extension).

        Returns:
            Path to the exported file.
        """
        filepath = self.output_directory / f"{filename}.json"

        data = {
            "query": result.query,
            "status": result.status.value,
            "confidence": result.confidence,
            "best_match": (
                {
                    "company_name": result.best_match.matched_name,
                    "similarity_score": result.best_match.similarity_score,
                    "status": result.best_match.status.value,
                    "is_exact_match": result.best_match.is_exact_match,
                    "notes": result.best_match.notes,
                }
                if result.best_match
                else None
            ),
            "all_matches": [
                {
                    "company_name": m.matched_name,
                    "similarity_score": m.similarity_score,
                    "status": m.status.value,
                    "is_exact_match": m.is_exact_match,
                    "notes": m.notes,
                }
                for m in result.all_matches
            ],
            "warnings": result.warnings,
            "timestamp": result.lookup_timestamp.isoformat(),
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Exported result to: {filepath}")
        return str(filepath)

    def _export_result_csv(self, result: LookupResult, filename: str) -> str:
        """Export result to CSV.

        Args:
            result: The result to export.
            filename: Base filename (without extension).

        Returns:
            Path to the exported file.
        """
        filepath = self.output_directory / f"{filename}.csv"

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Query",
                "Status",
                "Confidence",
                "Best Match",
                "Best Match Score",
                "Is Exact Match",
                "Warnings",
                "Timestamp",
            ])
            writer.writerow([
                result.query,
                result.status.value,
                f"{result.confidence:.2f}",
                result.best_match.matched_name if result.best_match else "",
                f"{result.best_match.similarity_score:.1f}" if result.best_match else "",
                str(result.best_match.is_exact_match) if result.best_match else "",
                "; ".join(result.warnings),
                result.lookup_timestamp.isoformat(),
            ])

        logger.info(f"Exported result to: {filepath}")
        return str(filepath)

    def export_batch_results(
        self,
        results: list[LookupResult],
        format: str = "json",
        filename: Optional[str] = None,
    ) -> str:
        """Export multiple lookup results.

        Args:
            results: List of results to export.
            format: Output format ('json' or 'csv').
            filename: Custom filename (auto-generated if not provided).

        Returns:
            Path to the exported file.
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"batch_lookup_{timestamp}"

        if format.lower() == "json":
            return self._export_batch_json(results, filename)
        elif format.lower() == "csv":
            return self._export_batch_csv(results, filename)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _export_batch_json(self, results: list[LookupResult], filename: str) -> str:
        """Export batch results to JSON.

        Args:
            results: List of results to export.
            filename: Base filename (without extension).

        Returns:
            Path to the exported file.
        """
        filepath = self.output_directory / f"{filename}.json"

        data = {
            "total_queries": len(results),
            "summary": {
                "whitelisted": sum(1 for r in results if r.is_approved),
                "blacklisted": sum(1 for r in results if r.is_blocked),
                "unknown": sum(1 for r in results if r.status.value == "unknown"),
            },
            "results": [
                {
                    "query": r.query,
                    "status": r.status.value,
                    "confidence": r.confidence,
                    "best_match": r.best_match.matched_name if r.best_match else None,
                    "best_match_score": r.best_match.similarity_score if r.best_match else None,
                    "warnings": r.warnings,
                }
                for r in results
            ],
            "export_timestamp": datetime.now().isoformat(),
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Exported {len(results)} results to: {filepath}")
        return str(filepath)

    def _export_batch_csv(self, results: list[LookupResult], filename: str) -> str:
        """Export batch results to CSV.

        Args:
            results: List of results to export.
            filename: Base filename (without extension).

        Returns:
            Path to the exported file.
        """
        filepath = self.output_directory / f"{filename}.csv"

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Query",
                "Status",
                "Confidence",
                "Best Match",
                "Best Match Score",
                "Is Exact Match",
                "Warnings",
            ])

            for result in results:
                writer.writerow([
                    result.query,
                    result.status.value,
                    f"{result.confidence:.2f}",
                    result.best_match.matched_name if result.best_match else "",
                    f"{result.best_match.similarity_score:.1f}" if result.best_match else "",
                    str(result.best_match.is_exact_match) if result.best_match else "",
                    "; ".join(result.warnings),
                ])

        logger.info(f"Exported {len(results)} results to: {filepath}")
        return str(filepath)

    def export_company_list(
        self,
        companies: list[CompanyInfo],
        format: str = "json",
        filename: Optional[str] = None,
    ) -> str:
        """Export a list of companies.

        Args:
            companies: List of companies to export.
            format: Output format ('json' or 'csv').
            filename: Custom filename (auto-generated if not provided).

        Returns:
            Path to the exported file.
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"companies_{timestamp}"

        filepath = self.output_directory / f"{filename}.{format}"

        if format.lower() == "json":
            data = [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "category": c.category,
                    "notes": c.notes,
                    "added_date": c.added_date.isoformat() if c.added_date else None,
                }
                for c in companies
            ]
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        elif format.lower() == "csv":
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Name", "Status", "Category", "Notes", "Added Date"])
                for c in companies:
                    writer.writerow([
                        c.name,
                        c.status.value,
                        c.category or "",
                        c.notes or "",
                        c.added_date.isoformat() if c.added_date else "",
                    ])
        else:
            raise ValueError(f"Unsupported format: {format}")

        logger.info(f"Exported {len(companies)} companies to: {filepath}")
        return str(filepath)

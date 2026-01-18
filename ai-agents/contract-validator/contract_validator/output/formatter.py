"""
Console output formatting using Rich library.
"""

from typing import List

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from contract_validator.data.schemas import (
    ComparisonReport,
    ExtractionMetrics,
    ExtractionResult,
    ValidationReport,
    ValidationResult,
)


class ConsoleFormatter:
    """Formats output for console display."""

    def __init__(self):
        """Initialize console formatter."""
        self.console = Console()

    def print_validation_report(self, report: ValidationReport) -> None:
        """
        Print validation report to console.

        Args:
            report: ValidationReport to display
        """
        self.console.print()
        self.console.rule("[bold blue]Contract Validation Report[/bold blue]")
        self.console.print()

        # Overall info
        self.console.print(f"[bold]Prompt:[/bold] {report.prompt_name}")
        self.console.print(f"[bold]Timestamp:[/bold] {report.test_timestamp}")
        self.console.print(f"[bold]Total Contracts:[/bold] {report.total_contracts}")
        self.console.print()

        # Extraction metrics
        self.console.print("[bold]Extraction Metrics:[/bold]")
        self._print_extraction_metrics(report.extraction_metrics)
        self.console.print()

        # Validation accuracy
        accuracy_color = (
            "green" if report.validation_accuracy >= 0.8
            else "yellow" if report.validation_accuracy >= 0.6
            else "red"
        )
        self.console.print(
            f"[bold]Validation Accuracy:[/bold] [{accuracy_color}]{report.validation_accuracy:.2%}[/{accuracy_color}]"
        )
        self.console.print()

        # Per-status accuracy
        if report.per_status_accuracy:
            self.console.print("[bold]Per-Status Accuracy:[/bold]")
            self._print_per_status_accuracy(report.per_status_accuracy)
            self.console.print()

        # Extraction errors
        extraction_errors = [r for r in report.results if not r.all_correct]
        if extraction_errors:
            self.console.print(
                f"[bold]Extraction Errors:[/bold] {len(extraction_errors)} contracts"
            )
            self._print_extraction_errors(extraction_errors[:10])
            if len(extraction_errors) > 10:
                self.console.print(
                    f"... and {len(extraction_errors) - 10} more (see output file)"
                )
            self.console.print()

        # Validation errors
        validation_errors = [r for r in report.validation_results if not r.is_correct]
        if validation_errors:
            self.console.print(
                f"[bold]Validation Errors:[/bold] {len(validation_errors)} contracts"
            )
            self._print_validation_errors(validation_errors[:10])
            if len(validation_errors) > 10:
                self.console.print(
                    f"... and {len(validation_errors) - 10} more (see output file)"
                )
            self.console.print()

    def print_comparison_report(self, report: ComparisonReport) -> None:
        """
        Print comparison report to console.

        Args:
            report: ComparisonReport to display
        """
        self.console.print()
        self.console.rule("[bold blue]Prompt Comparison Report[/bold blue]")
        self.console.print()

        self.console.print(
            f"[bold]Prompts Compared:[/bold] {', '.join(report.prompts_compared)}"
        )
        self.console.print(f"[bold]Timestamp:[/bold] {report.test_timestamp}")
        self.console.print()

        # Extraction accuracy comparison table
        self.console.print("[bold]Extraction Accuracy Comparison:[/bold]")
        comparison_table = Table(show_header=True, header_style="bold magenta")
        comparison_table.add_column("Prompt", style="cyan")
        comparison_table.add_column("Extraction Accuracy", justify="right")
        comparison_table.add_column("Validation Accuracy", justify="right")
        comparison_table.add_column("Winner", justify="center")

        for prompt_name in report.prompts_compared:
            extraction_acc = report.extraction_accuracy_comparison.get(prompt_name, 0.0)
            validation_acc = report.validation_accuracy_comparison.get(prompt_name, 0.0)
            is_winner = prompt_name == report.winner

            ext_color = (
                "green" if extraction_acc >= 0.8
                else "yellow" if extraction_acc >= 0.6
                else "red"
            )
            val_color = (
                "green" if validation_acc >= 0.8
                else "yellow" if validation_acc >= 0.6
                else "red"
            )

            comparison_table.add_row(
                prompt_name,
                f"[{ext_color}]{extraction_acc:.2%}[/{ext_color}]",
                f"[{val_color}]{validation_acc:.2%}[/{val_color}]",
                "*" if is_winner else "",
            )

        self.console.print(comparison_table)
        self.console.print()

        # Per-format comparison
        if report.per_format_comparison:
            self.console.print("[bold]Per-Format Accuracy:[/bold]")
            self._print_per_format_comparison(report.per_format_comparison)
            self.console.print()

    def _print_extraction_metrics(self, metrics: ExtractionMetrics) -> None:
        """Print extraction metrics as a table."""
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Field", style="cyan")
        table.add_column("Accuracy", justify="right")

        fields = [
            ("Student Name", metrics.student_name_accuracy),
            ("Matrikelnummer", metrics.matrikelnummer_accuracy),
            ("Company Name", metrics.company_name_accuracy),
            ("Start Date", metrics.start_date_accuracy),
            ("End Date", metrics.end_date_accuracy),
            ("Overall", metrics.overall_accuracy),
        ]

        for field, accuracy in fields:
            color = (
                "green" if accuracy >= 0.8
                else "yellow" if accuracy >= 0.6
                else "red"
            )
            table.add_row(field, f"[{color}]{accuracy:.2%}[/{color}]")

        self.console.print(table)

    def _print_per_status_accuracy(self, per_status: dict) -> None:
        """Print per-status accuracy as a table."""
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Status", style="cyan")
        table.add_column("Accuracy", justify="right")

        for status, accuracy in per_status.items():
            color = (
                "green" if accuracy >= 0.8
                else "yellow" if accuracy >= 0.6
                else "red"
            )
            table.add_row(status, f"[{color}]{accuracy:.2%}[/{color}]")

        self.console.print(table)

    def _print_per_format_comparison(self, per_format: dict) -> None:
        """Print per-format accuracy comparison."""
        # Get all formats
        all_formats = set()
        for prompt_data in per_format.values():
            all_formats.update(prompt_data.keys())

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Format", style="cyan")
        for prompt_name in per_format.keys():
            table.add_column(prompt_name, justify="right")

        for fmt in sorted(all_formats):
            row = [fmt]
            for prompt_name, prompt_data in per_format.items():
                accuracy = prompt_data.get(fmt, 0.0)
                color = (
                    "green" if accuracy >= 0.8
                    else "yellow" if accuracy >= 0.6
                    else "red"
                )
                row.append(f"[{color}]{accuracy:.2%}[/{color}]")
            table.add_row(*row)

        self.console.print(table)

    def _print_extraction_errors(self, errors: List[ExtractionResult]) -> None:
        """Print extraction error details."""
        for result in errors:
            incorrect_fields = []
            if not result.student_name_correct:
                incorrect_fields.append("student_name")
            if not result.matrikelnummer_correct:
                incorrect_fields.append("matrikelnummer")
            if not result.company_name_correct:
                incorrect_fields.append("company_name")
            if not result.start_date_correct:
                incorrect_fields.append("start_date")
            if not result.end_date_correct:
                incorrect_fields.append("end_date")

            self.console.print(
                f"  - [cyan]{result.contract_id}[/cyan]: "
                f"[red]Incorrect: {', '.join(incorrect_fields)}[/red]"
            )

    def _print_validation_errors(self, errors: List[ValidationResult]) -> None:
        """Print validation error details."""
        for result in errors:
            self.console.print(
                f"  - [cyan]{result.contract_id}[/cyan]: "
                f"Expected [green]{result.expected_status.value}[/green], "
                f"Got [red]{result.status.value}[/red]"
            )
            if result.issues:
                for issue in result.issues:
                    self.console.print(f"      [yellow]{issue}[/yellow]")

    def print_progress(self, current: int, total: int, contract_id: str = None) -> None:
        """
        Print progress update.

        Args:
            current: Current item number
            total: Total items
            contract_id: Optional contract ID being processed
        """
        status = f"Processing {contract_id}..." if contract_id else "Processing..."
        self.console.print(f"[{current}/{total}] {status}")

    def create_progress_bar(self, description: str = "Processing") -> Progress:
        """
        Create a progress bar for long-running operations.

        Args:
            description: Description to show

        Returns:
            Progress object to use with context manager
        """
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        )

    def print_generation_summary(
        self,
        total: int,
        format_dist: dict,
        status_dist: dict,
        output_path: str,
    ) -> None:
        """
        Print summary after generating contracts.

        Args:
            total: Total contracts generated
            format_dist: Distribution of formats
            status_dist: Distribution of statuses
            output_path: Path where contracts were saved
        """
        self.console.print()
        self.console.rule("[bold green]Contract Generation Complete[/bold green]")
        self.console.print()
        self.console.print(f"[bold]Total Contracts:[/bold] {total}")
        self.console.print()

        self.console.print("[bold]Format Distribution:[/bold]")
        for fmt, count in format_dist.items():
            self.console.print(f"  - {fmt}: {count}")
        self.console.print()

        self.console.print("[bold]Status Distribution:[/bold]")
        for status, count in status_dist.items():
            self.console.print(f"  - {status}: {count}")
        self.console.print()

        self.console.print(f"[bold]Output:[/bold] {output_path}")
        self.console.print()

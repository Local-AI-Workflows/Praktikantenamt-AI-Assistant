"""
Console output formatting with Rich.
"""

from rich.console import Console
from rich.table import Table

from workflow_validator.data.schemas import WorkflowValidationReport


class ConsoleFormatter:
    """Formats workflow validation reports for console display."""

    def __init__(self):
        """Initialize console formatter."""
        self.console = Console()

    def print_workflow_validation_report(
        self, report: WorkflowValidationReport
    ) -> None:
        """
        Print workflow validation report to console.

        Args:
            report: Validation report to display
        """
        self.console.print()
        self.console.print("[bold]Validation Results[/bold]")
        self.console.print(
            f"Overall Accuracy: [bold cyan]{report.overall_accuracy:.1%}[/bold cyan]"
        )
        self.console.print(
            f"Correct: [green]{report.correct_predictions}/{report.total_emails}[/green]  "
            f"Incorrect: [red]{report.incorrect_predictions}/{report.total_emails}[/red]"
        )
        self.console.print(
            f"Sent: {report.total_sent}  Found: {report.total_found}  "
            f"Not Found: {len(report.emails_not_found)}"
        )
        self.console.print()

        # Per-category metrics table
        self.console.print("[bold]Per-Category Metrics[/bold]")
        table = Table(show_header=True, header_style="bold")
        table.add_column("Category", style="cyan", width=30)
        table.add_column("Precision", justify="right")
        table.add_column("Recall", justify="right")
        table.add_column("F1", justify="right")
        table.add_column("Support", justify="right")

        for category, metrics in report.per_category_metrics.items():
            table.add_row(
                category,
                f"{metrics.precision:.2f}",
                f"{metrics.recall:.2f}",
                f"{metrics.f1_score:.2f}",
                str(metrics.support),
            )

        self.console.print(table)
        self.console.print()

        # Misrouted emails
        if report.misclassifications:
            self.console.print("[bold yellow]Misrouted Emails[/bold yellow]")
            for result in report.misclassifications[:10]:  # Show first 10
                self.console.print(
                    f"  • {result.email_id}: "
                    f"{result.expected_category} → {result.predicted_category} "
                    f"(folder: {result.found_in_folder})"
                )
            if len(report.misclassifications) > 10:
                self.console.print(
                    f"  ... and {len(report.misclassifications) - 10} more"
                )
            self.console.print()

        # Emails not found
        if report.emails_not_found:
            self.console.print("[bold red]Emails Not Found[/bold red]")
            for uuid_str in report.emails_not_found[:10]:
                self.console.print(f"  • {uuid_str}")
            if len(report.emails_not_found) > 10:
                self.console.print(f"  ... and {len(report.emails_not_found) - 10} more")
            self.console.print()

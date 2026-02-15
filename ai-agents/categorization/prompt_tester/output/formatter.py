"""
Console output formatting using Rich library.
"""

from typing import Dict, List, Union

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from prompt_tester.data.schemas import (
    AggregatedComparisonReport,
    AggregatedMetrics,
    AggregatedValidationReport,
    ComparisonReport,
    ValidationReport,
)


class ConsoleFormatter:
    """Formats output for console display."""

    def __init__(self, categories: List[str] = None):
        """
        Initialize console formatter.

        Args:
            categories: List of category names for confusion matrix labeling
        """
        self.console = Console()
        self.categories = categories or [
            "contract_submission",
            "international_office_question",
            "internship_postponement",
            "uncategorized",
        ]

    def print_validation_report(self, report: ValidationReport) -> None:
        """
        Print validation report to console.

        Args:
            report: ValidationReport to display
        """
        self.console.print()
        self.console.rule("[bold blue]Validation Report[/bold blue]")
        self.console.print()

        # Overall metrics
        self.console.print(f"[bold]Prompt:[/bold] {report.prompt_name or 'Unknown'}")
        self.console.print(f"[bold]Version:[/bold] {report.prompt_version or 'N/A'}")
        self.console.print(f"[bold]Timestamp:[/bold] {report.test_timestamp}")
        self.console.print()

        # Accuracy
        accuracy_color = "green" if report.overall_accuracy >= 0.8 else "yellow" if report.overall_accuracy >= 0.6 else "red"
        self.console.print(
            f"[bold]Overall Accuracy:[/bold] [{accuracy_color}]{report.overall_accuracy:.2%}[/{accuracy_color}] "
            f"({report.correct_predictions}/{report.total_emails} correct)"
        )
        self.console.print()

        # Per-category metrics table
        if report.per_category_metrics:
            self.console.print("[bold]Per-Category Metrics:[/bold]")
            self._print_metrics_table(report.per_category_metrics)
            self.console.print()

        # Confusion matrix
        if report.confusion_matrix:
            self.console.print("[bold]Confusion Matrix:[/bold]")
            self._print_confusion_matrix(report.confusion_matrix)
            self.console.print()

        # Misclassifications
        if report.misclassifications:
            self.console.print(
                f"[bold]Misclassifications:[/bold] {len(report.misclassifications)} errors"
            )
            self._print_misclassifications(report.misclassifications[:10])  # Show first 10
            if len(report.misclassifications) > 10:
                self.console.print(
                    f"... and {len(report.misclassifications) - 10} more (see output file for full list)"
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

        self.console.print(f"[bold]Prompts Compared:[/bold] {', '.join(report.prompts_compared)}")
        self.console.print(f"[bold]Timestamp:[/bold] {report.test_timestamp}")
        self.console.print()

        # Accuracy comparison table
        self.console.print("[bold]Accuracy Comparison:[/bold]")
        comparison_table = Table(show_header=True, header_style="bold magenta")
        comparison_table.add_column("Prompt", style="cyan")
        comparison_table.add_column("Accuracy", justify="right")
        comparison_table.add_column("Winner", justify="center")

        for prompt_name, accuracy in sorted(
            report.accuracy_comparison.items(), key=lambda x: x[1], reverse=True
        ):
            is_winner = prompt_name == report.winner
            accuracy_color = "green" if accuracy >= 0.8 else "yellow" if accuracy >= 0.6 else "red"
            comparison_table.add_row(
                prompt_name,
                f"[{accuracy_color}]{accuracy:.2%}[/{accuracy_color}]",
                "🏆" if is_winner else "",
            )

        self.console.print(comparison_table)
        self.console.print()

        # Disagreements
        if report.disagreements:
            self.console.print(
                f"[bold]Disagreements:[/bold] {len(report.disagreements)} cases where prompts differed"
            )
            self._print_disagreements(report.disagreements[:5])  # Show first 5
            if len(report.disagreements) > 5:
                self.console.print(
                    f"... and {len(report.disagreements) - 5} more disagreements"
                )
            self.console.print()

    def _print_metrics_table(self, metrics_dict: dict) -> None:
        """Print per-category metrics as a table."""
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Category", style="cyan")
        table.add_column("Precision", justify="right")
        table.add_column("Recall", justify="right")
        table.add_column("F1-Score", justify="right")
        table.add_column("Support", justify="right")

        for category, metrics in metrics_dict.items():
            table.add_row(
                category,
                f"{metrics.precision:.2%}",
                f"{metrics.recall:.2%}",
                f"{metrics.f1_score:.2%}",
                str(metrics.support),
            )

        self.console.print(table)

    def _print_confusion_matrix(self, matrix: List[List[int]]) -> None:
        """Print confusion matrix as a table."""
        self._print_confusion_matrix_table(matrix, self.categories)

    def _print_misclassifications(self, misclassifications: list) -> None:
        """Print misclassification details."""
        for result in misclassifications:
            self.console.print(
                f"  • [cyan]{result.email_id}[/cyan]: "
                f"Expected [green]{result.expected_category}[/green], "
                f"Got [red]{result.predicted_category}[/red]"
            )

    def _print_disagreements(self, disagreements: list) -> None:
        """Print disagreement details."""
        for disagreement in disagreements:
            self.console.print(
                f"  • [cyan]{disagreement.email_id}[/cyan]: "
                f"Prompt A: {disagreement.prompt_a_prediction} "
                f"{'✓' if disagreement.prompt_a_correct else '✗'}, "
                f"Prompt B: {disagreement.prompt_b_prediction} "
                f"{'✓' if disagreement.prompt_b_correct else '✗'} "
                f"(Expected: {disagreement.expected_category})"
            )

    def print_progress(self, current: int, total: int, email_id: str = None) -> None:
        """
        Print progress update.

        Args:
            current: Current item number
            total: Total items
            email_id: Optional email ID being processed
        """
        status = f"Processing {email_id}..." if email_id else "Processing..."
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

    def _print_confusion_matrix_table(
        self, matrix: List[List[Union[int, float]]], categories: List[str]
    ) -> None:
        """Print confusion matrix as a formatted table."""
        # Create table with row and column labels
        table = Table(
            show_header=True,
            header_style="bold magenta",
            title="Rows=Actual, Cols=Predicted",
        )
        table.add_column("Actual \\ Predicted", style="cyan")

        for category in categories:
            table.add_column(category[:10], justify="right")  # Truncate long names

        for i, row_category in enumerate(categories):
            row_values = [
                f"{val:.1f}" if isinstance(val, float) else str(val) for val in matrix[i]
            ]
            table.add_row(row_category[:10], *row_values)

        self.console.print(table)

    def _print_aggregated_metrics_table(
        self, metrics_dict: Dict[str, AggregatedMetrics]
    ) -> None:
        """Print aggregated per-category metrics as a table."""
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Category", style="cyan")
        table.add_column("Precision", justify="right")
        table.add_column("Recall", justify="right")
        table.add_column("F1-Score", justify="right")
        table.add_column("Support", justify="right")

        for category, metrics in metrics_dict.items():
            table.add_row(
                category,
                f"{metrics.mean_precision:.2%} ± {metrics.std_precision:.2%}",
                f"{metrics.mean_recall:.2%} ± {metrics.std_recall:.2%}",
                f"{metrics.mean_f1_score:.2%} ± {metrics.std_f1_score:.2%}",
                str(metrics.support),
            )

        self.console.print(table)

    def print_aggregated_report(self, report: AggregatedValidationReport) -> None:
        """
        Print aggregated validation report to console.

        Args:
            report: AggregatedValidationReport to display
        """
        self.console.print()
        self.console.rule("[bold blue]Aggregated Validation Report[/bold blue]")
        self.console.print()

        # Overall metrics
        self.console.print(f"[bold]Prompt:[/bold] {report.prompt_name or 'Unknown'}")
        self.console.print(f"[bold]Iterations:[/bold] {report.num_iterations}")
        self.console.print(f"[bold]Timestamp:[/bold] {report.test_timestamp}")
        self.console.print()

        # Accuracy with std dev
        accuracy_color = (
            "green"
            if report.mean_accuracy >= 0.8
            else "yellow"
            if report.mean_accuracy >= 0.6
            else "red"
        )
        self.console.print(
            f"[bold]Overall Accuracy:[/bold] [{accuracy_color}]{report.mean_accuracy:.2%} ±  {report.std_accuracy:.2%}[/{accuracy_color}]"
        )
        self.console.print()

        # Per-category metrics table with std dev
        if report.per_category_metrics:
            self.console.print("[bold]Per-Category Metrics (Mean ± Std Dev):[/bold]")
            self._print_aggregated_metrics_table(report.per_category_metrics)
            self.console.print()

        # Aggregated confusion matrix as nice table
        if report.aggregated_confusion_matrix:
            self.console.print("[bold]Aggregated Confusion Matrix:[/bold]")
            self._print_confusion_matrix_table(
                report.aggregated_confusion_matrix, self.categories
            )
            self.console.print()

    def print_aggregated_comparison_report(
        self, report: AggregatedComparisonReport
    ) -> None:
        """Print aggregated comparison report to console."""
        self.console.print()
        self.console.rule("[bold blue]Aggregated Prompt Comparison Report[/bold blue]")
        self.console.print()

        self.console.print(
            f"[bold]Prompts Compared:[/bold] {', '.join(report.prompts_compared)}"
        )
        self.console.print(
            f"[bold]Iterations per Prompt:[/bold] {report.num_iterations}"
        )
        self.console.print()

        # Accuracy comparison table with std dev
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Prompt", style="cyan")
        table.add_column("Mean Accuracy", justify="right")
        table.add_column("Std Dev", justify="right")
        table.add_column("Winner", justify="center")

        for prompt_name in sorted(
            report.aggregated_accuracy_comparison.keys(),
            key=lambda x: report.aggregated_accuracy_comparison[x]["mean"],
            reverse=True,
        ):
            metrics = report.aggregated_accuracy_comparison[prompt_name]
            is_winner = prompt_name == report.winner
            accuracy_color = (
                "green"
                if metrics["mean"] >= 0.8
                else "yellow"
                if metrics["mean"] >= 0.6
                else "red"
            )

            table.add_row(
                prompt_name,
                f"[{accuracy_color}]{metrics['mean']:.2%}[/{accuracy_color}]",
                f"{metrics['std']:.2%}",
                "🏆" if is_winner else "",
            )

        self.console.print(table)

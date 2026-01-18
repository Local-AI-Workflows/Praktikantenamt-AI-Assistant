"""
Console output formatting using Rich library.
"""

from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from response_generator.data.schemas import (
    ComparisonReport,
    EvaluationReport,
    EvaluationResult,
    GeneratedResponse,
    ResponseSuggestion,
    ResponseTemplate,
)


class ConsoleFormatter:
    """Formats output for console display."""

    def __init__(self):
        """Initialize console formatter."""
        self.console = Console()

    def print_response_suggestion(self, suggestion: ResponseSuggestion) -> None:
        """
        Print a response suggestion to console.

        Args:
            suggestion: ResponseSuggestion to display
        """
        self.console.print()
        self.console.rule(f"[bold blue]Response Suggestions for {suggestion.email_id}[/bold blue]")
        self.console.print()

        self.console.print(f"[bold]Email ID:[/bold] {suggestion.email_id}")
        self.console.print(f"[bold]Category:[/bold] {suggestion.category.value}")
        self.console.print(f"[bold]Recommended:[/bold] {suggestion.recommended_response_id}")
        self.console.print()

        for response in suggestion.responses:
            self._print_response(response, is_recommended=(response.id == suggestion.recommended_response_id))

    def _print_response(self, response: GeneratedResponse, is_recommended: bool = False) -> None:
        """Print a single generated response."""
        title = f"[{'green' if is_recommended else 'cyan'}]{response.tone.value.upper()}[/]"
        if is_recommended:
            title += " [yellow](Empfohlen)[/yellow]"

        content = (
            f"[bold]Betreff:[/bold] {response.subject}\n\n"
            f"{response.body}\n\n"
            f"[dim]Confidence: {response.confidence:.2%} | "
            f"Template: {response.template_used} | "
            f"Personalization: {'Ja' if response.personalization_applied else 'Nein'} | "
            f"Zeit: {response.generation_time:.2f}s[/dim]"
        )

        self.console.print(Panel(content, title=title, expand=False))
        self.console.print()

    def print_evaluation_report(self, report: EvaluationReport) -> None:
        """
        Print evaluation report to console.

        Args:
            report: EvaluationReport to display
        """
        self.console.print()
        self.console.rule("[bold blue]Evaluation Report[/bold blue]")
        self.console.print()

        # Summary
        self.console.print(f"[bold]Prompt/Template:[/bold] {report.prompt_name}")
        self.console.print(f"[bold]Timestamp:[/bold] {report.test_timestamp}")
        self.console.print(f"[bold]Total Emails:[/bold] {report.total_emails}")
        self.console.print(f"[bold]Total Responses:[/bold] {report.total_responses}")
        self.console.print()

        # Overall metrics
        quality_color = "green" if report.average_quality >= 0.7 else "yellow" if report.average_quality >= 0.5 else "red"
        self.console.print(
            f"[bold]Average Quality:[/bold] [{quality_color}]{report.average_quality:.2%}[/{quality_color}]"
        )
        self.console.print(f"[bold]Average Confidence:[/bold] {report.average_confidence:.2%}")

        pass_color = "green" if report.pass_rate >= 0.8 else "yellow" if report.pass_rate >= 0.6 else "red"
        self.console.print(
            f"[bold]Pass Rate:[/bold] [{pass_color}]{report.pass_rate:.2%}[/{pass_color}]"
        )
        self.console.print()

        # Per-category stats
        if report.per_category_stats:
            self.console.print("[bold]Per-Category Statistics:[/bold]")
            self._print_category_stats(report.per_category_stats)
            self.console.print()

        # Per-tone stats
        if report.per_tone_stats:
            self.console.print("[bold]Per-Tone Statistics:[/bold]")
            self._print_tone_stats(report.per_tone_stats)
            self.console.print()

        # Failed evaluations
        failed = [r for r in report.results if not r.passed]
        if failed:
            self.console.print(f"[bold]Failed Evaluations:[/bold] {len(failed)} responses")
            self._print_failed_evaluations(failed[:5])
            if len(failed) > 5:
                self.console.print(f"... and {len(failed) - 5} more (see output file)")
            self.console.print()

    def _print_category_stats(self, stats: dict) -> None:
        """Print per-category statistics table."""
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Category", style="cyan")
        table.add_column("Count", justify="right")
        table.add_column("Avg Quality", justify="right")
        table.add_column("Pass Rate", justify="right")

        for category, data in stats.items():
            quality = data.get("average_quality", 0)
            quality_str = f"{quality:.2%}"
            pass_rate = data.get("pass_rate", 0)
            pass_rate_str = f"{pass_rate:.2%}"

            table.add_row(
                category,
                str(int(data.get("count", 0))),
                quality_str,
                pass_rate_str,
            )

        self.console.print(table)

    def _print_tone_stats(self, stats: dict) -> None:
        """Print per-tone statistics table."""
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Tone", style="cyan")
        table.add_column("Count", justify="right")
        table.add_column("Avg Quality", justify="right")
        table.add_column("Pass Rate", justify="right")

        for tone, data in stats.items():
            quality = data.get("average_quality", 0)
            quality_str = f"{quality:.2%}"
            pass_rate = data.get("pass_rate", 0)
            pass_rate_str = f"{pass_rate:.2%}"

            table.add_row(
                tone,
                str(int(data.get("count", 0))),
                quality_str,
                pass_rate_str,
            )

        self.console.print(table)

    def _print_failed_evaluations(self, results: List[EvaluationResult]) -> None:
        """Print details of failed evaluations."""
        for result in results:
            self.console.print(
                f"  - [cyan]{result.email_id}[/cyan] ({result.generated_response.tone.value}): "
                f"Quality {result.metrics.overall_score:.2%}"
            )
            for feedback in result.feedback[:2]:
                self.console.print(f"    [dim]{feedback}[/dim]")

    def print_comparison_report(self, report: ComparisonReport) -> None:
        """
        Print comparison report to console.

        Args:
            report: ComparisonReport to display
        """
        self.console.print()
        self.console.rule("[bold blue]Template Comparison Report[/bold blue]")
        self.console.print()

        self.console.print(f"[bold]Templates Compared:[/bold] {len(report.templates_compared)}")
        self.console.print(f"[bold]Timestamp:[/bold] {report.test_timestamp}")
        self.console.print()

        # Quality comparison table
        self.console.print("[bold]Quality Comparison:[/bold]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Template", style="cyan")
        table.add_column("Avg Quality", justify="right")
        table.add_column("Winner", justify="center")

        for template, quality in sorted(
            report.quality_comparison.items(), key=lambda x: x[1], reverse=True
        ):
            is_winner = template == report.winner
            quality_color = "green" if quality >= 0.7 else "yellow" if quality >= 0.5 else "red"
            table.add_row(
                template,
                f"[{quality_color}]{quality:.2%}[/{quality_color}]",
                "[green]***[/green]" if is_winner else "",
            )

        self.console.print(table)
        self.console.print()

        # Per-category comparison
        if report.per_category_comparison:
            self.console.print("[bold]Per-Category Quality:[/bold]")
            cat_table = Table(show_header=True, header_style="bold magenta")
            cat_table.add_column("Category", style="cyan")

            templates = list(report.per_category_comparison.keys())
            for template in templates:
                cat_table.add_column(template, justify="right")

            # Get all categories
            all_categories = set()
            for template_data in report.per_category_comparison.values():
                all_categories.update(template_data.keys())

            for category in sorted(all_categories):
                row = [category]
                for template in templates:
                    quality = report.per_category_comparison.get(template, {}).get(category, 0)
                    row.append(f"{quality:.2%}")
                cat_table.add_row(*row)

            self.console.print(cat_table)
            self.console.print()

        if report.winner:
            self.console.print(f"[bold green]Winner: {report.winner}[/bold green]")
            self.console.print()

    def print_template_list(self, templates: List[tuple]) -> None:
        """
        Print list of available templates.

        Args:
            templates: List of (category, tone) tuples
        """
        self.console.print()
        self.console.rule("[bold blue]Available Templates[/bold blue]")
        self.console.print()

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Category", style="cyan")
        table.add_column("Tone", style="green")

        for category, tone in sorted(templates, key=lambda x: (x[0].value, x[1].value)):
            table.add_row(category.value, tone.value)

        self.console.print(table)
        self.console.print()
        self.console.print(f"Total: {len(templates)} templates")
        self.console.print()

    def print_progress(self, current: int, total: int, email_id: Optional[str] = None) -> None:
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

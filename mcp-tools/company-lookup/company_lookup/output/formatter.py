"""Console output formatting using Rich.

Supports bilingual operation (English/German) via the i18n module.
"""

from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from company_lookup.data.schemas import (
    CompanyInfo,
    CompanyListStats,
    CompanyStatus,
    LookupResult,
    MatchResult,
)
from company_lookup.i18n import t


class ConsoleFormatter:
    """Formats output for console display using Rich."""

    def __init__(self, console: Optional[Console] = None):
        """Initialize the formatter.

        Args:
            console: Rich Console instance (created if not provided).
        """
        self.console = console or Console()

    def _status_color(self, status: CompanyStatus) -> str:
        """Get color for a status."""
        return {
            CompanyStatus.WHITELISTED: "green",
            CompanyStatus.BLACKLISTED: "red",
            CompanyStatus.UNKNOWN: "yellow",
        }.get(status, "white")

    def _status_emoji(self, status: CompanyStatus) -> str:
        """Get emoji for a status."""
        return {
            CompanyStatus.WHITELISTED: "[green]✓[/green]",
            CompanyStatus.BLACKLISTED: "[red]✗[/red]",
            CompanyStatus.UNKNOWN: "[yellow]?[/yellow]",
        }.get(status, "")

    def print_lookup_result(self, result: LookupResult) -> None:
        """Print a lookup result.

        Args:
            result: The lookup result to display.
        """
        status_color = self._status_color(result.status)
        status_emoji = self._status_emoji(result.status)

        # Create header panel
        header_text = Text()
        header_text.append(f"{t('fmt.query')}: ", style="bold")
        header_text.append(f"{result.query}\n")
        header_text.append(f"{t('fmt.status')}: ", style="bold")
        header_text.append(f"{result.status.value.upper()} ", style=f"bold {status_color}")
        header_text.append(status_emoji)
        header_text.append(f"\n{t('fmt.confidence')}: ", style="bold")
        header_text.append(f"{result.confidence:.0%}", style=status_color)

        self.console.print(Panel(header_text, title=t("fmt.panel.title"), border_style=status_color))

        # Print best match if available
        if result.best_match:
            self.print_match(result.best_match, title=t("fmt.match.title"))

        # Print other matches if available
        if len(result.all_matches) > 1:
            self._print_matches_table(result.all_matches[1:], title=t("fmt.matches.title"))

        # Print warnings
        if result.warnings:
            self.console.print()
            for warning in result.warnings:
                self.console.print(f"[yellow]⚠[/yellow] {warning}")

    def print_match(self, match: MatchResult, title: Optional[str] = None) -> None:
        """Print a single match result.

        Args:
            match: The match to display.
            title: Title for the panel.
        """
        if title is None:
            title = t("fmt.match.title")

        status_color = self._status_color(match.status)

        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column(t("fmt.field"), style="bold")
        table.add_column(t("fmt.value"))

        table.add_row(t("fmt.company"), match.matched_name)
        table.add_row(
            t("fmt.status"),
            f"[{status_color}]{match.status.value}[/{status_color}]"
        )
        table.add_row(t("fmt.score"), f"{match.similarity_score:.1f}%")
        if match.is_exact_match:
            table.add_row(t("fmt.match_type"), f"[green]{t('fmt.exact_match')}[/green]")
        if match.notes:
            table.add_row(t("fmt.notes"), match.notes)

        self.console.print(Panel(table, title=title))

    def _print_matches_table(self, matches: list[MatchResult], title: Optional[str] = None) -> None:
        """Print a table of matches.

        Args:
            matches: List of matches to display.
            title: Title for the table.
        """
        if title is None:
            title = t("fmt.matches.title")

        table = Table(title=title)
        table.add_column("#", style="dim")
        table.add_column(t("fmt.company_name"))
        table.add_column(t("fmt.status"))
        table.add_column(t("fmt.score"))
        table.add_column(t("fmt.notes"), max_width=30)

        for idx, match in enumerate(matches, start=1):
            status_color = self._status_color(match.status)
            table.add_row(
                str(idx),
                match.matched_name,
                f"[{status_color}]{match.status.value}[/{status_color}]",
                f"{match.similarity_score:.1f}%",
                match.notes or "-",
            )

        self.console.print(table)

    def print_company_list(
        self,
        companies: list[CompanyInfo],
        title: Optional[str] = None,
        status_filter: Optional[CompanyStatus] = None,
    ) -> None:
        """Print a list of companies.

        Args:
            companies: List of companies to display.
            title: Title for the table.
            status_filter: Filter display to this status only.
        """
        if status_filter:
            companies = [c for c in companies if c.status == status_filter]

        if title is None:
            title = t("fmt.companies_title", filter=t("status.all"))

        table = Table(title=title)
        table.add_column("#", style="dim")
        table.add_column(t("fmt.company_name"))
        table.add_column(t("fmt.status"))
        table.add_column(t("fmt.category"))
        table.add_column(t("fmt.notes"), max_width=30)

        for idx, company in enumerate(companies, start=1):
            status_color = self._status_color(company.status)
            table.add_row(
                str(idx),
                company.name,
                f"[{status_color}]{company.status.value}[/{status_color}]",
                company.category or "-",
                company.notes or "-",
            )

        self.console.print(table)

    def print_stats(self, stats: CompanyListStats) -> None:
        """Print statistics about the company lists.

        Args:
            stats: Statistics to display.
        """
        table = Table(title=t("fmt.stats.title"), show_header=False)
        table.add_column(t("fmt.metric"), style="bold")
        table.add_column(t("fmt.value"))

        table.add_row(t("fmt.stats.total"), str(stats.total_companies))
        table.add_row(t("fmt.stats.whitelisted"), f"[green]{stats.whitelisted_count}[/green]")
        table.add_row(t("fmt.stats.blacklisted"), f"[red]{stats.blacklisted_count}[/red]")

        if stats.categories:
            table.add_row(t("fmt.stats.categories"), ", ".join(stats.categories))

        if stats.last_updated:
            table.add_row(t("fmt.stats.last_updated"), stats.last_updated.strftime("%Y-%m-%d %H:%M:%S"))

        if stats.source_file:
            table.add_row(t("fmt.stats.source_file"), stats.source_file)

        self.console.print(table)

    def print_success(self, message: str) -> None:
        """Print a success message.

        Args:
            message: Message to display.
        """
        self.console.print(f"[green]✓[/green] {message}")

    def print_error(self, message: str) -> None:
        """Print an error message.

        Args:
            message: Message to display.
        """
        self.console.print(f"[red]✗[/red] {message}")

    def print_warning(self, message: str) -> None:
        """Print a warning message.

        Args:
            message: Message to display.
        """
        self.console.print(f"[yellow]⚠[/yellow] {message}")

    def print_info(self, message: str) -> None:
        """Print an info message.

        Args:
            message: Message to display.
        """
        self.console.print(f"[blue]ℹ[/blue] {message}")

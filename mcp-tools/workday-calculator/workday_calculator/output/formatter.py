"""
Console output formatting using Rich.
"""

from typing import List

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from workday_calculator.data.schemas import Bundesland, Holiday, WorkdayResult
from workday_calculator.data.bundesland_data import BUNDESLAND_NAMES


class ConsoleFormatter:
    """Formats output for console display using Rich."""

    def __init__(self):
        """Initialize the console formatter."""
        self.console = Console()

    def print_result(self, result: WorkdayResult) -> None:
        """
        Print a workday calculation result.

        Args:
            result: WorkdayResult to display.
        """
        # Create main result panel
        self.console.print()
        self.console.rule("[bold blue]Workday Calculation Result[/bold blue]")
        self.console.print()

        # Summary table
        summary_table = Table(show_header=False, box=None)
        summary_table.add_column("Label", style="cyan", width=20)
        summary_table.add_column("Value", style="white")

        summary_table.add_row(
            "Period:",
            f"{result.start_date.strftime('%d.%m.%Y')} - {result.end_date.strftime('%d.%m.%Y')}",
        )
        summary_table.add_row(
            "Location:",
            f"{result.location.bundesland_name} ({result.location.bundesland.value})",
        )
        summary_table.add_row(
            "Resolution Method:",
            result.location.resolution_method.capitalize(),
        )
        summary_table.add_row(
            "Confidence:",
            f"{result.location.confidence:.0%}",
        )

        self.console.print(Panel(summary_table, title="[bold]Location & Period[/bold]"))

        # Calculation result table
        calc_table = Table(show_header=False, box=None)
        calc_table.add_column("Label", style="cyan", width=20)
        calc_table.add_column("Value", style="white", justify="right", width=10)

        calc_table.add_row("Calendar Days:", str(result.calendar_days))
        calc_table.add_row(
            "Weekend Days:",
            f"- {result.weekend_days} ({result.weekends_detail.get('saturdays', 0)} Sat, {result.weekends_detail.get('sundays', 0)} Sun)",
        )
        calc_table.add_row("Holidays (on workdays):", f"- {result.holidays_count}")
        calc_table.add_row("", "─" * 15)
        calc_table.add_row(
            Text("Working Days:", style="bold green"),
            Text(str(result.working_days), style="bold green"),
        )

        self.console.print(Panel(calc_table, title="[bold]Calculation[/bold]"))

        # Holidays table
        if result.holidays:
            self.print_holidays(result.holidays)

        # Warnings
        if result.warnings:
            self.console.print()
            for warning in result.warnings:
                self.console.print(f"[yellow]Warning:[/yellow] {warning}")

        self.console.print()

    def print_holidays(self, holidays: List[Holiday]) -> None:
        """
        Print a table of holidays.

        Args:
            holidays: List of holidays to display.
        """
        holiday_table = Table(title="[bold]Holidays in Period[/bold]")
        holiday_table.add_column("Date", style="cyan", width=12)
        holiday_table.add_column("Day", style="dim", width=12)
        holiday_table.add_column("Name", style="white")

        weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        for holiday in holidays:
            weekday = weekday_names[holiday.date.weekday()]
            holiday_table.add_row(
                holiday.date.strftime("%d.%m.%Y"),
                weekday,
                holiday.name,
            )

        self.console.print(holiday_table)

    def print_holidays_for_year(self, year: int, bundesland: Bundesland, holidays: List[Holiday]) -> None:
        """
        Print all holidays for a year and Bundesland.

        Args:
            year: Year.
            bundesland: Federal state.
            holidays: List of holidays.
        """
        self.console.print()
        self.console.rule(
            f"[bold blue]Holidays {year} - {BUNDESLAND_NAMES[bundesland]}[/bold blue]"
        )
        self.console.print()

        if holidays:
            self.print_holidays(holidays)
        else:
            self.console.print("[dim]No holidays found for this period.[/dim]")

        self.console.print()

    def print_bundeslaender(self) -> None:
        """Print a table of all German federal states."""
        self.console.print()
        self.console.rule("[bold blue]German Federal States (Bundeslaender)[/bold blue]")
        self.console.print()

        table = Table()
        table.add_column("Code", style="cyan", width=6)
        table.add_column("Name", style="white")

        for bundesland in Bundesland:
            table.add_row(bundesland.value, BUNDESLAND_NAMES[bundesland])

        self.console.print(table)
        self.console.print()

    def print_error(self, message: str) -> None:
        """
        Print an error message.

        Args:
            message: Error message to display.
        """
        self.console.print(f"[bold red]Error:[/bold red] {message}")

    def print_success(self, message: str) -> None:
        """
        Print a success message.

        Args:
            message: Success message to display.
        """
        self.console.print(f"[bold green]Success:[/bold green] {message}")

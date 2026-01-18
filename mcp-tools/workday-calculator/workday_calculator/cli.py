"""
CLI interface for workday calculator.
"""

import sys
from datetime import date, datetime

import click

from workday_calculator.config.manager import ConfigManager
from workday_calculator.core.calculator import WorkdayCalculator
from workday_calculator.core.holiday_provider import HolidayProvider
from workday_calculator.core.location_resolver import LocationResolver
from workday_calculator.data.schemas import Bundesland, LocationInput, WorkdayRequest
from workday_calculator.data.bundesland_data import BUNDESLAND_NAMES
from workday_calculator.output.formatter import ConsoleFormatter
from workday_calculator.output.exporter import ResultExporter


def parse_date(date_str: str) -> date:
    """Parse date string in various formats."""
    formats = ["%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(
        f"Invalid date format: {date_str}. Use YYYY-MM-DD, DD.MM.YYYY, or DD/MM/YYYY"
    )


@click.group()
@click.version_option(version="0.1.0", prog_name="workday-calc")
def main():
    """Workday Calculator - Calculate working days considering German holidays."""
    pass


@main.command()
@click.option(
    "--start", "-s",
    required=True,
    help="Start date (YYYY-MM-DD, DD.MM.YYYY, or DD/MM/YYYY)",
)
@click.option(
    "--end", "-e",
    required=True,
    help="End date (YYYY-MM-DD, DD.MM.YYYY, or DD/MM/YYYY)",
)
@click.option(
    "--plz", "-p",
    help="German postal code (5 digits)",
)
@click.option(
    "--bundesland", "-b",
    type=click.Choice([b.value for b in Bundesland], case_sensitive=False),
    help="Bundesland code (e.g., HH, BY, NW)",
)
@click.option(
    "--address", "-a",
    help="Address for geocoding",
)
@click.option(
    "--include-saturdays",
    is_flag=True,
    default=False,
    help="Count Saturdays as working days",
)
@click.option(
    "--output", "-o",
    type=click.Path(),
    help="Output file path (optional)",
)
@click.option(
    "--format", "-f",
    type=click.Choice(["json", "csv", "both", "console"]),
    default="console",
    help="Output format (default: console)",
)
@click.option(
    "--config", "-c",
    type=click.Path(exists=True),
    help="Path to config file (optional)",
)
def calculate(start, end, plz, bundesland, address, include_saturdays, output, format, config):
    """Calculate working days between two dates."""
    formatter = ConsoleFormatter()

    try:
        # Parse dates
        start_date = parse_date(start)
        end_date = parse_date(end)

        if end_date < start_date:
            formatter.print_error("End date must be after start date")
            sys.exit(1)

        # Load configuration
        config_manager = ConfigManager(config)
        cfg = config_manager.load_config()

        # Create location input
        location = LocationInput(
            postal_code=plz,
            bundesland=Bundesland(bundesland.upper()) if bundesland else None,
            address=address,
        )

        # Check if we have enough location info
        if not (plz or bundesland or address):
            if cfg.default_bundesland:
                location.bundesland = cfg.default_bundesland
            else:
                formatter.print_error(
                    "Please provide location: --plz, --bundesland, or --address"
                )
                sys.exit(1)

        # Create calculator
        holiday_provider = HolidayProvider(language=cfg.holiday_language)
        location_resolver = LocationResolver(
            geocoding_enabled=cfg.geocoding_enabled,
            timeout=cfg.geocoding_timeout,
        )
        calculator = WorkdayCalculator(holiday_provider, location_resolver)

        # Create request and calculate
        request = WorkdayRequest(
            start_date=start_date,
            end_date=end_date,
            location=location,
            include_saturdays=include_saturdays,
        )

        result = calculator.calculate(request)

        # Output result
        if format == "console" or format == "both":
            formatter.print_result(result)

        # Export if requested
        if format in ("json", "csv", "both"):
            exporter = ResultExporter(
                output_directory=cfg.output_directory,
            )

            if format == "json":
                path = exporter.export_json(result, output)
                formatter.print_success(f"Result saved to {path}")
            elif format == "csv":
                path = exporter.export_csv(result, output)
                formatter.print_success(f"Result saved to {path}")
            else:  # both
                json_path, csv_path = exporter.export_both(result)
                formatter.print_success(f"Results saved to:\n  - {json_path}\n  - {csv_path}")

    except ValueError as e:
        formatter.print_error(str(e))
        sys.exit(1)
    except Exception as e:
        formatter.print_error(f"Unexpected error: {e}")
        sys.exit(1)


@main.command()
@click.option(
    "--year", "-y",
    type=int,
    default=None,
    help="Year to show holidays for (default: current year)",
)
@click.option(
    "--bundesland", "-b",
    type=click.Choice([b.value for b in Bundesland], case_sensitive=False),
    required=True,
    help="Bundesland code (e.g., HH, BY, NW)",
)
@click.option(
    "--output", "-o",
    type=click.Path(),
    help="Output CSV file path (optional)",
)
@click.option(
    "--config", "-c",
    type=click.Path(exists=True),
    help="Path to config file (optional)",
)
def holidays(year, bundesland, output, config):
    """List holidays for a specific year and Bundesland."""
    formatter = ConsoleFormatter()

    try:
        # Default to current year
        if year is None:
            year = date.today().year

        # Load configuration
        config_manager = ConfigManager(config)
        cfg = config_manager.load_config()

        # Get holidays
        bundesland_enum = Bundesland(bundesland.upper())
        holiday_provider = HolidayProvider(language=cfg.holiday_language)
        holiday_list = holiday_provider.get_holidays_for_year(year, bundesland_enum)

        # Display
        formatter.print_holidays_for_year(year, bundesland_enum, holiday_list)

        # Export if requested
        if output:
            exporter = ResultExporter(output_directory=cfg.output_directory)
            path = exporter.export_holidays_csv(holiday_list, output)
            formatter.print_success(f"Holidays saved to {path}")

    except Exception as e:
        formatter.print_error(f"Error: {e}")
        sys.exit(1)


@main.command()
def bundeslaender():
    """List all German federal states (Bundeslaender) with their codes."""
    formatter = ConsoleFormatter()
    formatter.print_bundeslaender()


@main.command()
@click.option(
    "--host", "-h",
    default=None,
    help="Host to bind to (default: from config or 0.0.0.0)",
)
@click.option(
    "--port", "-p",
    type=int,
    default=None,
    help="Port to bind to (default: from config or 8000)",
)
@click.option(
    "--config", "-c",
    type=click.Path(exists=True),
    help="Path to config file (optional)",
)
def serve(host, port, config):
    """Start the FastAPI server."""
    formatter = ConsoleFormatter()

    try:
        import uvicorn

        # Load configuration
        config_manager = ConfigManager(config)
        cfg = config_manager.load_config()

        # Use provided values or fall back to config
        api_host = host or cfg.api_host
        api_port = port or cfg.api_port

        formatter.console.print(f"Starting API server at http://{api_host}:{api_port}")
        formatter.console.print("Press Ctrl+C to stop")
        formatter.console.print()

        uvicorn.run(
            "workday_calculator.api:app",
            host=api_host,
            port=api_port,
            reload=False,
        )

    except ImportError:
        formatter.print_error("uvicorn is required for the API server. Install it with: pip install uvicorn")
        sys.exit(1)
    except Exception as e:
        formatter.print_error(f"Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

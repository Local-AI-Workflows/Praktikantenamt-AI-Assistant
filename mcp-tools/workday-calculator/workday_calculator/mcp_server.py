"""
MCP Server for the Workday Calculator.

This module provides an MCP (Model Context Protocol) server that exposes
the workday calculator functionality to Claude Desktop and other MCP clients.

Supports two transport modes:
- stdio: For local Claude Desktop integration
- sse: For HTTP-based integration (Docker, remote servers)
"""

import argparse
import os
from datetime import date
from typing import Optional

from mcp.server.fastmcp import FastMCP

from workday_calculator.config.manager import ConfigManager
from workday_calculator.core.calculator import WorkdayCalculator
from workday_calculator.core.holiday_provider import HolidayProvider
from workday_calculator.core.location_resolver import LocationResolver
from workday_calculator.data.schemas import (
    Bundesland,
    LocationInput,
    WorkdayRequest,
)
from workday_calculator.data.bundesland_data import BUNDESLAND_NAMES

# Load configuration
config_manager = ConfigManager()
config = config_manager.load_config()

# Initialize components
holiday_provider = HolidayProvider(language=config.holiday_language)
location_resolver = LocationResolver(
    geocoding_enabled=config.geocoding_enabled,
    timeout=config.geocoding_timeout,
)
calculator = WorkdayCalculator(holiday_provider, location_resolver)


def create_mcp_server(host: str = "127.0.0.1", port: int = 8000) -> FastMCP:
    """Create and configure the MCP server with tools."""
    mcp = FastMCP("Workday Calculator", host=host, port=port)

    @mcp.tool()
    def calculate_workdays(
        start_date: str,
        end_date: str,
        postal_code: Optional[str] = None,
        bundesland: Optional[str] = None,
        address: Optional[str] = None,
        include_saturdays: bool = False,
    ) -> dict:
        """
        Calculate working days between two dates for a German location.

        This tool calculates the number of working days (excluding weekends and
        public holidays) between a start and end date for a specific German
        federal state (Bundesland).

        Args:
            start_date: Start date in format YYYY-MM-DD (e.g., "2026-03-01")
            end_date: End date in format YYYY-MM-DD (e.g., "2026-08-31")
            postal_code: German postal code (PLZ, 5 digits, e.g., "20095" for Hamburg)
            bundesland: Bundesland code (e.g., "HH" for Hamburg, "BY" for Bayern)
            address: Full address for geocoding (optional fallback)
            include_saturdays: Whether to count Saturdays as work days (default: False)

        Returns:
            Dictionary with calculation results including:
            - working_days: Number of working days
            - calendar_days: Total calendar days in the period
            - weekend_days: Number of weekend days
            - holidays_count: Number of public holidays on workdays
            - holidays: List of holidays with dates and names
            - bundesland: Resolved federal state code
            - bundesland_name: Full name of the federal state

        Examples:
            Calculate workdays for Hamburg from March to August 2026:
            >>> calculate_workdays("2026-03-01", "2026-08-31", postal_code="20095")

            Calculate workdays for Bayern using Bundesland code:
            >>> calculate_workdays("2026-03-01", "2026-08-31", bundesland="BY")
        """
        # Parse dates
        try:
            start = date.fromisoformat(start_date)
            end = date.fromisoformat(end_date)
        except ValueError as e:
            return {"error": f"Invalid date format. Use YYYY-MM-DD. Details: {str(e)}"}

        # Validate dates
        if end < start:
            return {"error": "end_date must be after or equal to start_date"}

        # Validate location
        if not (postal_code or bundesland or address):
            return {"error": "Provide at least one of: postal_code, bundesland, or address"}

        try:
            # Build location input
            bundesland_enum = None
            if bundesland:
                try:
                    bundesland_enum = Bundesland(bundesland.upper())
                except ValueError:
                    valid_codes = ", ".join(b.value for b in Bundesland)
                    return {"error": f"Invalid bundesland code: {bundesland}. Valid codes: {valid_codes}"}

            location = LocationInput(
                postal_code=postal_code,
                bundesland=bundesland_enum,
                address=address,
            )

            # Create workday request
            workday_request = WorkdayRequest(
                start_date=start,
                end_date=end,
                location=location,
                include_saturdays=include_saturdays,
            )

            # Calculate
            result = calculator.calculate(workday_request)

            return {
                "working_days": result.working_days,
                "calendar_days": result.calendar_days,
                "weekend_days": result.weekend_days,
                "saturdays": result.weekends_detail.get("saturdays", 0),
                "sundays": result.weekends_detail.get("sundays", 0),
                "holidays_count": result.holidays_count,
                "holidays": [
                    {"date": h.holiday_date.isoformat(), "name": h.name, "is_national": h.is_national}
                    for h in result.holidays
                ],
                "start_date": result.start_date.isoformat(),
                "end_date": result.end_date.isoformat(),
                "bundesland": result.location.bundesland.value,
                "bundesland_name": result.location.bundesland_name,
                "confidence": result.confidence,
                "resolution_method": result.location.resolution_method,
                "warnings": result.warnings,
            }

        except ValueError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"Calculation error: {str(e)}"}

    @mcp.tool()
    def get_holidays(year: int, bundesland: str) -> dict:
        """
        Get all public holidays for a specific year and German federal state.

        Args:
            year: Year to get holidays for (e.g., 2026)
            bundesland: Bundesland code (e.g., "HH" for Hamburg, "BY" for Bayern,
                        "NW" for Nordrhein-Westfalen)

        Returns:
            Dictionary with:
            - year: The requested year
            - bundesland: The Bundesland code
            - bundesland_name: Full name of the Bundesland
            - holidays: List of holidays with date, name, and national flag

        Examples:
            Get holidays for Bayern in 2026:
            >>> get_holidays(2026, "BY")

            Get holidays for Hamburg in 2026:
            >>> get_holidays(2026, "HH")
        """
        # Validate bundesland
        try:
            bundesland_enum = Bundesland(bundesland.upper())
        except ValueError:
            valid_codes = ", ".join(b.value for b in Bundesland)
            return {"error": f"Invalid bundesland code: {bundesland}. Valid codes: {valid_codes}"}

        # Validate year
        if year < 1900 or year > 2100:
            return {"error": "Year must be between 1900 and 2100"}

        try:
            holidays = holiday_provider.get_holidays_for_year(year, bundesland_enum)

            return {
                "year": year,
                "bundesland": bundesland_enum.value,
                "bundesland_name": BUNDESLAND_NAMES[bundesland_enum],
                "holiday_count": len(holidays),
                "holidays": [
                    {
                        "date": h.holiday_date.isoformat(),
                        "name": h.name,
                        "is_national": h.is_national,
                    }
                    for h in holidays
                ],
            }

        except Exception as e:
            return {"error": f"Error fetching holidays: {str(e)}"}

    @mcp.tool()
    def list_bundeslaender() -> dict:
        """
        List all German federal states (Bundesländer) with their codes.

        Returns a list of all 16 German federal states with their
        abbreviation codes and full names.

        Returns:
            Dictionary with list of all Bundesländer including:
            - code: Two-letter abbreviation (e.g., "BY", "HH", "NW")
            - name: Full German name (e.g., "Bayern", "Hamburg", "Nordrhein-Westfalen")

        Example codes:
            - BB: Brandenburg
            - BE: Berlin
            - BW: Baden-Württemberg
            - BY: Bayern
            - HB: Bremen
            - HE: Hessen
            - HH: Hamburg
            - MV: Mecklenburg-Vorpommern
            - NI: Niedersachsen
            - NW: Nordrhein-Westfalen
            - RP: Rheinland-Pfalz
            - SH: Schleswig-Holstein
            - SL: Saarland
            - SN: Sachsen
            - ST: Sachsen-Anhalt
            - TH: Thüringen
        """
        return {
            "count": len(Bundesland),
            "bundeslaender": [
                {"code": bl.value, "name": BUNDESLAND_NAMES[bl]}
                for bl in Bundesland
            ],
        }

    return mcp


def main():
    """Run the MCP server with configurable transport.

    Transport can be set via:
    - Command line: --transport sse --port 8080
    - Environment: MCP_TRANSPORT=sse MCP_PORT=8080 MCP_HOST=0.0.0.0
    """
    parser = argparse.ArgumentParser(description="Workday Calculator MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default=os.environ.get("MCP_TRANSPORT", "stdio"),
        help="Transport mode: stdio (default) or sse for HTTP",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("MCP_HOST", os.environ.get("FASTMCP_HOST", "0.0.0.0")),
        help="Host to bind to (SSE mode only, default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("MCP_PORT", os.environ.get("FASTMCP_PORT", "8080"))),
        help="Port to listen on (SSE mode only, default: 8080)",
    )

    args = parser.parse_args()

    # Create MCP server with configured host/port
    mcp = create_mcp_server(host=args.host, port=args.port)

    if args.transport == "sse":
        # Run with SSE transport for HTTP access
        mcp.run(transport="sse")
    else:
        # Run with stdio transport for Claude Desktop
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

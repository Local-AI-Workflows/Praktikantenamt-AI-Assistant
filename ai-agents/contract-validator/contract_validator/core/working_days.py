"""
Working days calculation utilities.

This module provides a simple working days calculator as a placeholder
for future MCP tool integration. The current implementation counts
weekdays (Monday-Friday) without considering public holidays.
"""

from datetime import date, timedelta
from typing import Optional


def calculate_working_days(
    start: date,
    end: date,
    location: Optional[str] = None,
) -> int:
    """
    Calculate the number of working days between two dates.

    This is a placeholder implementation that counts weekdays (Mon-Fri).
    In the future, this will integrate with an MCP workday-calculator
    tool that considers public holidays based on location.

    Args:
        start: Start date (inclusive)
        end: End date (inclusive)
        location: Location for holiday calculation (not yet implemented)

    Returns:
        Number of working days between start and end (inclusive)

    Note:
        - Currently ignores public holidays
        - TODO: Integrate with MCP workday-calculator tool
        - TODO: Support German federal state holidays
    """
    # TODO: Call MCP workday-calculator when available
    # Example future integration:
    # try:
    #     return mcp_client.call("workday-calculator", {
    #         "start_date": start.isoformat(),
    #         "end_date": end.isoformat(),
    #         "location": location or "DE",
    #     })
    # except MCPError:
    #     # Fall back to simple calculation
    #     pass

    # Simple calculation: count weekdays (Mon-Fri)
    days = 0
    current = start
    while current <= end:
        if current.weekday() < 5:  # Monday = 0, Friday = 4
            days += 1
        current += timedelta(days=1)
    return days


def is_valid_duration(
    start: date,
    end: date,
    min_working_days: int = 95,
    location: Optional[str] = None,
) -> bool:
    """
    Check if the internship duration meets the minimum requirement.

    Args:
        start: Start date
        end: End date
        min_working_days: Minimum required working days (default: 95)
        location: Location for holiday calculation (not yet implemented)

    Returns:
        True if duration meets or exceeds minimum, False otherwise
    """
    working_days = calculate_working_days(start, end, location)
    return working_days >= min_working_days


def get_duration_info(
    start: date,
    end: date,
    min_working_days: int = 95,
    location: Optional[str] = None,
) -> dict:
    """
    Get detailed duration information for an internship.

    Args:
        start: Start date
        end: End date
        min_working_days: Minimum required working days
        location: Location for holiday calculation (not yet implemented)

    Returns:
        Dictionary with duration details:
        - calendar_days: Total calendar days
        - working_days: Calculated working days
        - min_required: Minimum required days
        - is_valid: Whether duration is valid
        - shortfall: Days short of minimum (0 if valid)
    """
    calendar_days = (end - start).days + 1
    working_days = calculate_working_days(start, end, location)
    is_valid = working_days >= min_working_days
    shortfall = max(0, min_working_days - working_days)

    return {
        "calendar_days": calendar_days,
        "working_days": working_days,
        "min_required": min_working_days,
        "is_valid": is_valid,
        "shortfall": shortfall,
    }

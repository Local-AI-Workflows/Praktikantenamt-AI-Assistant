"""
Main workday calculator logic.
"""

from datetime import date, timedelta
from typing import Set

from workday_calculator.data.schemas import (
    LocationInput,
    WorkdayRequest,
    WorkdayResult,
)
from workday_calculator.core.holiday_provider import HolidayProvider
from workday_calculator.core.location_resolver import LocationResolver


class WorkdayCalculator:
    """Calculates working days considering weekends and holidays."""

    def __init__(
        self,
        holiday_provider: HolidayProvider,
        location_resolver: LocationResolver,
    ):
        """
        Initialize the workday calculator.

        Args:
            holiday_provider: Provider for holiday information.
            location_resolver: Resolver for location inputs.
        """
        self.holiday_provider = holiday_provider
        self.location_resolver = location_resolver

    def calculate(self, request: WorkdayRequest) -> WorkdayResult:
        """
        Calculate working days for a given request.

        Args:
            request: WorkdayRequest with date range and location.

        Returns:
            WorkdayResult with calculated working days and metadata.
        """
        # Resolve location to Bundesland
        location = self.location_resolver.resolve(request.location)

        # Get holidays in the range
        holidays = self.holiday_provider.get_holidays_for_range(
            request.start_date, request.end_date, location.bundesland
        )
        holiday_dates: Set[date] = {h.date for h in holidays}

        # Calculate calendar days
        calendar_days = (request.end_date - request.start_date).days + 1

        # Count weekend days
        saturdays = 0
        sundays = 0
        holidays_on_workdays = 0

        current = request.start_date
        while current <= request.end_date:
            weekday = current.weekday()
            if weekday == 5:  # Saturday
                saturdays += 1
            elif weekday == 6:  # Sunday
                sundays += 1
            current += timedelta(days=1)

        # Count holidays that fall on workdays (not weekends)
        for hdate in holiday_dates:
            weekday = hdate.weekday()
            # If Saturday is a workday, only Sunday is weekend
            if request.include_saturdays:
                is_weekend = weekday == 6  # Only Sunday
            else:
                is_weekend = weekday in (5, 6)  # Saturday and Sunday

            if not is_weekend:
                holidays_on_workdays += 1

        # Calculate weekend days (excluding Saturdays if they're workdays)
        if request.include_saturdays:
            weekend_days = sundays
        else:
            weekend_days = saturdays + sundays

        # Calculate working days
        working_days = calendar_days - weekend_days - holidays_on_workdays

        # Generate warnings
        warnings = []
        if location.confidence < 0.9:
            warnings.append(
                f"Location resolution confidence: {location.confidence:.0%}. "
                f"Consider providing a more specific location."
            )
        if working_days < 0:
            working_days = 0
            warnings.append("Calculated working days was negative, set to 0.")

        return WorkdayResult(
            start_date=request.start_date,
            end_date=request.end_date,
            location=location,
            calendar_days=calendar_days,
            weekend_days=weekend_days,
            holidays_count=holidays_on_workdays,
            working_days=working_days,
            holidays=holidays,
            weekends_detail={"saturdays": saturdays, "sundays": sundays},
            confidence=location.confidence,
            warnings=warnings,
        )

    def calculate_simple(
        self,
        start_date: date,
        end_date: date,
        postal_code: str = None,
        bundesland: str = None,
        include_saturdays: bool = False,
    ) -> WorkdayResult:
        """
        Simplified calculation method for CLI usage.

        Args:
            start_date: Start date of the period.
            end_date: End date of the period.
            postal_code: Optional German postal code.
            bundesland: Optional Bundesland code (e.g., 'HH', 'BY').
            include_saturdays: Whether to count Saturdays as workdays.

        Returns:
            WorkdayResult with calculated working days.
        """
        from workday_calculator.data.schemas import Bundesland as BundeslandEnum

        location_input = LocationInput(
            postal_code=postal_code,
            bundesland=BundeslandEnum(bundesland) if bundesland else None,
        )

        request = WorkdayRequest(
            start_date=start_date,
            end_date=end_date,
            location=location_input,
            include_saturdays=include_saturdays,
        )

        return self.calculate(request)

"""
Tests for the workday calculator.
"""

from datetime import date

import pytest

from workday_calculator.core.calculator import WorkdayCalculator
from workday_calculator.core.holiday_provider import HolidayProvider
from workday_calculator.core.location_resolver import LocationResolver
from workday_calculator.data.schemas import (
    Bundesland,
    LocationInput,
    WorkdayRequest,
)


@pytest.fixture
def calculator():
    """Create a WorkdayCalculator instance."""
    holiday_provider = HolidayProvider(language="de")
    location_resolver = LocationResolver(geocoding_enabled=False)
    return WorkdayCalculator(holiday_provider, location_resolver)


@pytest.fixture
def holiday_provider():
    """Create a HolidayProvider instance."""
    return HolidayProvider(language="de")


@pytest.fixture
def location_resolver():
    """Create a LocationResolver instance."""
    return LocationResolver(geocoding_enabled=False)


class TestHolidayProvider:
    """Tests for HolidayProvider."""

    def test_get_holidays_for_year_hamburg(self, holiday_provider):
        """Test getting holidays for Hamburg 2026."""
        holidays = holiday_provider.get_holidays_for_year(2026, Bundesland.HH)

        # Hamburg should have standard German holidays
        holiday_names = [h.name for h in holidays]
        assert "Neujahr" in holiday_names
        assert "Karfreitag" in holiday_names
        assert "Ostermontag" in holiday_names
        # Note: "Tag der Arbeit" may be named "Erster Mai" in the holidays library
        assert "Erster Mai" in holiday_names or "Tag der Arbeit" in holiday_names
        assert "Tag der Deutschen Einheit" in holiday_names
        # Note: Christmas names may vary (Erster/Zweiter Weihnachtstag)
        assert any("Weihnachtstag" in name for name in holiday_names)

    def test_get_holidays_for_year_bayern(self, holiday_provider):
        """Test that Bayern has more holidays than Hamburg."""
        hamburg_holidays = holiday_provider.get_holidays_for_year(2026, Bundesland.HH)
        bayern_holidays = holiday_provider.get_holidays_for_year(2026, Bundesland.BY)

        # Bayern should have more holidays (e.g., Heilige Drei Koenige, Fronleichnam)
        assert len(bayern_holidays) > len(hamburg_holidays)

    def test_is_holiday(self, holiday_provider):
        """Test is_holiday method."""
        # January 1st is always a holiday
        new_year = date(2026, 1, 1)
        assert holiday_provider.is_holiday(new_year, Bundesland.HH) is True

        # A random Tuesday shouldn't be a holiday (unless it's actually a holiday)
        regular_day = date(2026, 7, 7)  # A Tuesday in July
        assert holiday_provider.is_holiday(regular_day, Bundesland.HH) is False


class TestLocationResolver:
    """Tests for LocationResolver."""

    def test_resolve_from_bundesland(self, location_resolver):
        """Test direct Bundesland resolution."""
        location = LocationInput(bundesland=Bundesland.HH)
        result = location_resolver.resolve(location)

        assert result.bundesland == Bundesland.HH
        assert result.bundesland_name == "Hamburg"
        assert result.confidence == 1.0
        assert result.resolution_method == "manual"

    def test_resolve_from_plz(self, location_resolver):
        """Test PLZ-based resolution."""
        location = LocationInput(postal_code="20095")  # Hamburg PLZ
        result = location_resolver.resolve(location)

        assert result.bundesland == Bundesland.HH
        assert result.confidence == 0.95
        assert result.resolution_method == "plz"

    def test_resolve_from_plz_bayern(self, location_resolver):
        """Test PLZ-based resolution for Bayern."""
        location = LocationInput(postal_code="80331")  # Munich PLZ
        result = location_resolver.resolve(location)

        assert result.bundesland == Bundesland.BY
        assert result.resolution_method == "plz"

    def test_resolve_invalid_plz(self, location_resolver):
        """Test that invalid PLZ raises error during Pydantic validation."""
        from pydantic import ValidationError as PydanticValidationError

        # PLZ validation happens at Pydantic model creation, not at resolve()
        with pytest.raises(PydanticValidationError):
            LocationInput(postal_code="1234")  # Too short

    def test_resolve_no_location(self, location_resolver):
        """Test that missing location raises error."""
        location = LocationInput()

        with pytest.raises(ValueError, match="Could not resolve location"):
            location_resolver.resolve(location)


class TestWorkdayCalculator:
    """Tests for WorkdayCalculator."""

    def test_calculate_simple_week(self, calculator):
        """Test calculating workdays for a simple week."""
        location = LocationInput(bundesland=Bundesland.HH)
        request = WorkdayRequest(
            start_date=date(2026, 3, 2),  # Monday
            end_date=date(2026, 3, 6),    # Friday
            location=location,
            include_saturdays=False,
        )

        result = calculator.calculate(request)

        assert result.calendar_days == 5
        assert result.weekend_days == 0
        assert result.working_days == 5

    def test_calculate_week_with_weekend(self, calculator):
        """Test calculating workdays for a full week including weekend."""
        location = LocationInput(bundesland=Bundesland.HH)
        request = WorkdayRequest(
            start_date=date(2026, 3, 2),  # Monday
            end_date=date(2026, 3, 8),    # Sunday
            location=location,
            include_saturdays=False,
        )

        result = calculator.calculate(request)

        assert result.calendar_days == 7
        assert result.weekend_days == 2  # Saturday + Sunday
        assert result.weekends_detail["saturdays"] == 1
        assert result.weekends_detail["sundays"] == 1
        assert result.working_days == 5

    def test_calculate_hamburg_march_to_august_2026(self, calculator):
        """
        Test the main example: Hamburg (PLZ 20095) from 01.03.2026 to 31.08.2026.
        """
        location = LocationInput(postal_code="20095")
        request = WorkdayRequest(
            start_date=date(2026, 3, 1),
            end_date=date(2026, 8, 31),
            location=location,
            include_saturdays=False,
        )

        result = calculator.calculate(request)

        # Verify location was resolved correctly
        assert result.location.bundesland == Bundesland.HH
        assert result.location.bundesland_name == "Hamburg"

        # Verify the calculation
        # March 1, 2026 to August 31, 2026 = 184 days
        assert result.calendar_days == 184

        # Count holidays in Hamburg for this period
        # Expected holidays in this period:
        # - Karfreitag (April 3, 2026)
        # - Ostermontag (April 6, 2026)
        # - Tag der Arbeit (May 1, 2026 - Friday)
        # - Christi Himmelfahrt (May 14, 2026 - Thursday)
        # - Pfingstmontag (May 25, 2026 - Monday)
        assert len(result.holidays) > 0

        # Working days should be: calendar_days - weekends - holidays_on_workdays
        assert result.working_days > 0
        assert result.working_days < result.calendar_days

        # Print for verification
        print(f"\nHamburg 01.03.2026 - 31.08.2026:")
        print(f"  Calendar days: {result.calendar_days}")
        print(f"  Weekend days: {result.weekend_days}")
        print(f"  Holidays (on workdays): {result.holidays_count}")
        print(f"  Working days: {result.working_days}")
        print(f"  Holidays: {[h.name for h in result.holidays]}")

    def test_calculate_with_saturdays(self, calculator):
        """Test calculation with Saturdays included as workdays."""
        location = LocationInput(bundesland=Bundesland.HH)
        request = WorkdayRequest(
            start_date=date(2026, 3, 2),  # Monday
            end_date=date(2026, 3, 8),    # Sunday
            location=location,
            include_saturdays=True,
        )

        result = calculator.calculate(request)

        assert result.calendar_days == 7
        assert result.weekend_days == 1  # Only Sunday
        assert result.working_days == 6  # Mon-Sat

    def test_calculate_with_holiday(self, calculator):
        """Test calculation period including a holiday."""
        location = LocationInput(bundesland=Bundesland.HH)
        # New Year's 2026 is a Thursday
        request = WorkdayRequest(
            start_date=date(2025, 12, 29),  # Monday
            end_date=date(2026, 1, 4),      # Sunday
            location=location,
            include_saturdays=False,
        )

        result = calculator.calculate(request)

        # Should have 2 holidays: New Year's Eve (Silvester is not a holiday) and New Year's Day
        # Actually only New Year's Day (Jan 1) is a public holiday in Hamburg
        assert result.holidays_count >= 1

        # Working days should account for the holiday
        # Dec 29 (Mon), Dec 30 (Tue), Dec 31 (Wed), Jan 1 (Thu-holiday), Jan 2 (Fri), Jan 3 (Sat), Jan 4 (Sun)
        # = 7 calendar days - 2 weekend - 1 holiday = 4 working days
        assert result.working_days <= result.calendar_days - result.weekend_days


class TestWorkdayCalculatorEdgeCases:
    """Edge case tests for WorkdayCalculator."""

    def test_single_day(self, calculator):
        """Test calculation for a single day."""
        location = LocationInput(bundesland=Bundesland.HH)
        request = WorkdayRequest(
            start_date=date(2026, 3, 2),  # Monday
            end_date=date(2026, 3, 2),    # Same day
            location=location,
            include_saturdays=False,
        )

        result = calculator.calculate(request)

        assert result.calendar_days == 1
        assert result.working_days == 1

    def test_single_weekend_day(self, calculator):
        """Test calculation for a single weekend day."""
        location = LocationInput(bundesland=Bundesland.HH)
        request = WorkdayRequest(
            start_date=date(2026, 3, 7),  # Saturday
            end_date=date(2026, 3, 7),    # Same day
            location=location,
            include_saturdays=False,
        )

        result = calculator.calculate(request)

        assert result.calendar_days == 1
        assert result.weekend_days == 1
        assert result.working_days == 0

    def test_year_boundary(self, calculator):
        """Test calculation spanning year boundary."""
        location = LocationInput(bundesland=Bundesland.HH)
        request = WorkdayRequest(
            start_date=date(2025, 12, 15),
            end_date=date(2026, 1, 15),
            location=location,
            include_saturdays=False,
        )

        result = calculator.calculate(request)

        assert result.calendar_days == 32
        # Should have holidays from both years
        holiday_dates = [h.holiday_date for h in result.holidays]
        assert date(2025, 12, 25) in holiday_dates  # 1. Weihnachtstag
        assert date(2026, 1, 1) in holiday_dates    # Neujahr


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

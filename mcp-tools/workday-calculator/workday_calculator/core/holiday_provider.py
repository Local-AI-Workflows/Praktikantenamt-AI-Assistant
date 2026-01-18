"""
Holiday provider using the holidays library for German federal states.
"""

from datetime import date, timedelta
from typing import Dict, List, Set

import holidays

from workday_calculator.data.schemas import Bundesland, Holiday
from workday_calculator.data.bundesland_data import BUNDESLAND_NAMES


class HolidayProvider:
    """Provides holiday information for German federal states."""

    def __init__(self, language: str = "de"):
        """
        Initialize the holiday provider.

        Args:
            language: Language for holiday names ('de' or 'en').
        """
        self.language = language
        self._cache: Dict[tuple, List[Holiday]] = {}

    def get_holidays_for_range(
        self, start: date, end: date, bundesland: Bundesland
    ) -> List[Holiday]:
        """
        Get all holidays within a date range for a specific Bundesland.

        Args:
            start: Start date of the range.
            end: End date of the range.
            bundesland: German federal state.

        Returns:
            List of Holiday objects within the range.
        """
        cache_key = (start, end, bundesland, self.language)
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Determine which years to fetch
        years = set(range(start.year, end.year + 1))
        subdiv = bundesland.value

        # Create holidays object for the Bundesland
        de_holidays = holidays.Germany(
            subdiv=subdiv, language=self.language, years=years
        )

        result = []
        current = start
        while current <= end:
            if current in de_holidays:
                holiday_name = de_holidays.get(current)
                result.append(
                    Holiday(
                        holiday_date=current,
                        name=holiday_name if self.language == "de" else holiday_name,
                        name_english=holiday_name if self.language == "en" else None,
                        is_national=self._is_national_holiday(current, de_holidays),
                    )
                )
            current += timedelta(days=1)

        self._cache[cache_key] = result
        return result

    def get_holiday_dates(
        self, start: date, end: date, bundesland: Bundesland
    ) -> Set[date]:
        """
        Get a set of holiday dates within a range.

        Args:
            start: Start date of the range.
            end: End date of the range.
            bundesland: German federal state.

        Returns:
            Set of dates that are holidays.
        """
        holiday_list = self.get_holidays_for_range(start, end, bundesland)
        return {h.holiday_date for h in holiday_list}

    def is_holiday(self, check_date: date, bundesland: Bundesland) -> bool:
        """
        Check if a specific date is a holiday.

        Args:
            check_date: Date to check.
            bundesland: German federal state.

        Returns:
            True if the date is a holiday, False otherwise.
        """
        return len(self.get_holidays_for_range(check_date, check_date, bundesland)) > 0

    def get_holidays_for_year(self, year: int, bundesland: Bundesland) -> List[Holiday]:
        """
        Get all holidays for a specific year.

        Args:
            year: Year to get holidays for.
            bundesland: German federal state.

        Returns:
            List of Holiday objects for the year.
        """
        start = date(year, 1, 1)
        end = date(year, 12, 31)
        return self.get_holidays_for_range(start, end, bundesland)

    def _is_national_holiday(self, check_date: date, state_holidays: holidays.HolidayBase) -> bool:
        """
        Determine if a holiday is national (observed in all states).

        Args:
            check_date: Date to check.
            state_holidays: Holidays object for a specific state.

        Returns:
            True if it's a national holiday, False if state-specific.
        """
        # Check if the holiday exists in a state with minimal holidays (like Hamburg)
        national_check = holidays.Germany(subdiv="HH", years=check_date.year)
        return check_date in national_check

    def clear_cache(self) -> None:
        """Clear the holiday cache."""
        self._cache.clear()

"""
Location resolver for determining Bundesland from various inputs.
"""

import re
from typing import Optional

from workday_calculator.data.schemas import Bundesland, LocationInput, LocationResult
from workday_calculator.data.bundesland_data import (
    BUNDESLAND_NAMES,
    PLZ_RANGES,
    STATE_NAME_MAPPING,
)


class LocationResolver:
    """Resolves location inputs to a specific Bundesland."""

    def __init__(self, geocoding_enabled: bool = True, timeout: int = 10):
        """
        Initialize the location resolver.

        Args:
            geocoding_enabled: Whether to enable geocoding for address resolution.
            timeout: Timeout for geocoding requests in seconds.
        """
        self.geocoding_enabled = geocoding_enabled
        self.timeout = timeout

    def resolve(self, location: LocationInput) -> LocationResult:
        """
        Resolve a location input to a Bundesland.

        Priority order:
        1. Direct bundesland specification
        2. Postal code (PLZ)
        3. Geocoding from address (if enabled)

        Args:
            location: Location input to resolve.

        Returns:
            LocationResult with resolved Bundesland and metadata.

        Raises:
            ValueError: If location cannot be resolved.
        """
        # Priority 1: Direct bundesland specification
        if location.bundesland:
            return self._create_result(location.bundesland, 1.0, "manual")

        # Priority 2: PLZ-based resolution
        plz = location.postal_code or self._extract_plz(location.address)
        if plz:
            bundesland = self._resolve_from_plz(plz)
            if bundesland:
                return self._create_result(bundesland, 0.95, "plz")

        # Priority 3: City name matching
        if location.city:
            bundesland = self._resolve_from_city(location.city)
            if bundesland:
                return self._create_result(bundesland, 0.85, "city")

        # Priority 4: Geocoding (if enabled)
        if self.geocoding_enabled and location.address:
            bundesland = self._resolve_from_geocoding(location.address)
            if bundesland:
                return self._create_result(bundesland, 0.85, "geocoding")

        raise ValueError(
            "Could not resolve location. Provide PLZ, address, or bundesland directly."
        )

    def _resolve_from_plz(self, plz: str) -> Optional[Bundesland]:
        """
        Resolve Bundesland from postal code.

        Args:
            plz: German postal code (5 digits).

        Returns:
            Bundesland if found, None otherwise.
        """
        if len(plz) < 2:
            return None
        prefix = plz[:2]
        return PLZ_RANGES.get(prefix)

    def _resolve_from_city(self, city: str) -> Optional[Bundesland]:
        """
        Resolve Bundesland from city name.

        Uses known city mappings for major cities.

        Args:
            city: City name.

        Returns:
            Bundesland if found, None otherwise.
        """
        city_lower = city.lower().strip()

        # Major city mappings
        city_mapping = {
            "hamburg": Bundesland.HH,
            "berlin": Bundesland.BE,
            "bremen": Bundesland.HB,
            "muenchen": Bundesland.BY,
            "munich": Bundesland.BY,
            "koeln": Bundesland.NW,
            "cologne": Bundesland.NW,
            "frankfurt": Bundesland.HE,
            "stuttgart": Bundesland.BW,
            "duesseldorf": Bundesland.NW,
            "dortmund": Bundesland.NW,
            "essen": Bundesland.NW,
            "leipzig": Bundesland.SN,
            "dresden": Bundesland.SN,
            "hannover": Bundesland.NI,
            "nuernberg": Bundesland.BY,
            "nuremberg": Bundesland.BY,
        }

        return city_mapping.get(city_lower)

    def _resolve_from_geocoding(self, address: str) -> Optional[Bundesland]:
        """
        Resolve Bundesland using geocoding.

        Args:
            address: Address string to geocode.

        Returns:
            Bundesland if found, None otherwise.
        """
        try:
            from geopy.geocoders import Nominatim

            geolocator = Nominatim(user_agent="workday-calculator", timeout=self.timeout)
            location = geolocator.geocode(
                address + ", Deutschland", addressdetails=True
            )
            if location and "address" in location.raw:
                state = location.raw["address"].get("state", "")
                return self._name_to_bundesland(state)
        except Exception:
            # Geocoding failed, return None
            pass
        return None

    def _extract_plz(self, text: Optional[str]) -> Optional[str]:
        """
        Extract a German postal code from text.

        Args:
            text: Text that may contain a PLZ.

        Returns:
            5-digit PLZ if found, None otherwise.
        """
        if not text:
            return None
        match = re.search(r"\b(\d{5})\b", text)
        return match.group(1) if match else None

    def _name_to_bundesland(self, name: str) -> Optional[Bundesland]:
        """
        Convert a state name to Bundesland enum.

        Args:
            name: State name in German or English.

        Returns:
            Bundesland if matched, None otherwise.
        """
        name_lower = name.lower().strip()
        return STATE_NAME_MAPPING.get(name_lower)

    def _create_result(
        self, bundesland: Bundesland, confidence: float, method: str
    ) -> LocationResult:
        """
        Create a LocationResult object.

        Args:
            bundesland: Resolved Bundesland.
            confidence: Confidence score (0.0 to 1.0).
            method: Resolution method used.

        Returns:
            LocationResult object.
        """
        return LocationResult(
            bundesland=bundesland,
            bundesland_name=BUNDESLAND_NAMES[bundesland],
            confidence=confidence,
            resolution_method=method,
        )

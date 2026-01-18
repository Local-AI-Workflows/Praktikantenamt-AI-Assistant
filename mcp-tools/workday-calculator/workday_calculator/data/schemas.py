"""
Data models for the workday calculator using Pydantic.
"""

from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class Bundesland(str, Enum):
    """German federal states (Bundeslaender)."""

    BB = "BB"  # Brandenburg
    BE = "BE"  # Berlin
    BW = "BW"  # Baden-Wuerttemberg
    BY = "BY"  # Bayern
    HB = "HB"  # Bremen
    HE = "HE"  # Hessen
    HH = "HH"  # Hamburg
    MV = "MV"  # Mecklenburg-Vorpommern
    NI = "NI"  # Niedersachsen
    NW = "NW"  # Nordrhein-Westfalen
    RP = "RP"  # Rheinland-Pfalz
    SH = "SH"  # Schleswig-Holstein
    SL = "SL"  # Saarland
    SN = "SN"  # Sachsen
    ST = "ST"  # Sachsen-Anhalt
    TH = "TH"  # Thueringen


class LocationInput(BaseModel):
    """Input model for location specification."""

    address: Optional[str] = Field(default=None, description="Full address for geocoding")
    postal_code: Optional[str] = Field(default=None, description="German postal code (PLZ)")
    city: Optional[str] = Field(default=None, description="City name")
    bundesland: Optional[Bundesland] = Field(default=None, description="Direct Bundesland specification")

    @field_validator("postal_code")
    @classmethod
    def validate_plz(cls, v: Optional[str]) -> Optional[str]:
        """Validate German postal code format (5 digits)."""
        if v and (not v.isdigit() or len(v) != 5):
            raise ValueError("PLZ must be 5 digits")
        return v


class Holiday(BaseModel):
    """Represents a public holiday."""

    holiday_date: date = Field(..., description="Date of the holiday")
    name: str = Field(..., description="Name of the holiday in German")
    name_english: Optional[str] = Field(default=None, description="Name in English")
    is_national: bool = Field(default=True, description="Whether it's a national holiday")


class WorkdayRequest(BaseModel):
    """Request model for workday calculation."""

    start_date: date = Field(..., description="Start date of the period")
    end_date: date = Field(..., description="End date of the period")
    location: LocationInput = Field(..., description="Location for holiday determination")
    include_saturdays: bool = Field(default=False, description="Whether to count Saturdays as work days")

    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, v: date, info) -> date:
        """Ensure end_date is after start_date."""
        if "start_date" in info.data and v < info.data["start_date"]:
            raise ValueError("end_date must be after or equal to start_date")
        return v


class LocationResult(BaseModel):
    """Result of location resolution."""

    bundesland: Bundesland = Field(..., description="Resolved Bundesland")
    bundesland_name: str = Field(..., description="Full name of the Bundesland")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score of resolution")
    resolution_method: str = Field(..., description="Method used: plz, geocoding, or manual")


class WorkdayResult(BaseModel):
    """Complete result of workday calculation."""

    start_date: date = Field(..., description="Start date of the period")
    end_date: date = Field(..., description="End date of the period")
    location: LocationResult = Field(..., description="Resolved location information")
    calendar_days: int = Field(..., ge=0, description="Total calendar days in range")
    weekend_days: int = Field(..., ge=0, description="Number of weekend days (excluding work Saturdays)")
    holidays_count: int = Field(..., ge=0, description="Number of holidays on workdays")
    working_days: int = Field(..., ge=0, description="Calculated working days")
    holidays: List[Holiday] = Field(default_factory=list, description="List of holidays in the range")
    weekends_detail: Dict[str, int] = Field(
        default_factory=dict, description="Breakdown of Saturdays and Sundays"
    )
    calculation_timestamp: datetime = Field(
        default_factory=datetime.now, description="When the calculation was performed"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence of calculation")
    warnings: List[str] = Field(default_factory=list, description="Any warnings generated")


class Config(BaseModel):
    """Configuration for the workday calculator."""

    default_bundesland: Optional[Bundesland] = Field(
        default=None, description="Default Bundesland if not specified"
    )
    geocoding_enabled: bool = Field(default=True, description="Enable geocoding for address resolution")
    geocoding_timeout: int = Field(default=10, ge=1, le=60, description="Geocoding timeout in seconds")
    holiday_language: str = Field(default="de", description="Language for holiday names")
    output_format: str = Field(default="json", description="Default output format: json or csv")
    output_directory: str = Field(default="results", description="Directory for output files")
    api_host: str = Field(default="0.0.0.0", description="API server host")
    api_port: int = Field(default=8000, ge=1, le=65535, description="API server port")

"""
FastAPI REST API for the workday calculator.
"""

from datetime import date
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from workday_calculator.config.manager import ConfigManager
from workday_calculator.core.calculator import WorkdayCalculator
from workday_calculator.core.holiday_provider import HolidayProvider
from workday_calculator.core.location_resolver import LocationResolver
from workday_calculator.data.schemas import (
    Bundesland,
    Holiday,
    LocationInput,
    WorkdayRequest,
    WorkdayResult,
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


# API Models
class CalculateRequest(BaseModel):
    """Request model for workday calculation."""

    start_date: date = Field(..., description="Start date of the period")
    end_date: date = Field(..., description="End date of the period")
    postal_code: Optional[str] = Field(None, description="German postal code (PLZ)")
    bundesland: Optional[str] = Field(None, description="Bundesland code (e.g., HH, BY)")
    address: Optional[str] = Field(None, description="Address for geocoding")
    include_saturdays: bool = Field(False, description="Count Saturdays as work days")


class CalculateResponse(BaseModel):
    """Response model for workday calculation."""

    start_date: date
    end_date: date
    bundesland: str
    bundesland_name: str
    calendar_days: int
    weekend_days: int
    saturdays: int
    sundays: int
    holidays_count: int
    working_days: int
    holidays: List[dict]
    confidence: float
    resolution_method: str
    warnings: List[str]


class HolidayResponse(BaseModel):
    """Response model for a single holiday."""

    date: date
    name: str
    is_national: bool


class BundeslandInfo(BaseModel):
    """Information about a Bundesland."""

    code: str
    name: str


# FastAPI app
app = FastAPI(
    title="Workday Calculator API",
    description="Calculate working days considering German federal state holidays",
    version="0.1.0",
)


@app.get("/")
async def root():
    """API root endpoint with basic info."""
    return {
        "name": "Workday Calculator API",
        "version": "0.1.0",
        "endpoints": {
            "POST /calculate": "Calculate working days",
            "GET /holidays/{year}/{bundesland}": "Get holidays for a year",
            "GET /bundeslaender": "List all federal states",
        },
    }


@app.post("/calculate", response_model=CalculateResponse)
async def calculate_workdays(request: CalculateRequest):
    """
    Calculate working days between two dates.

    Provide location via:
    - postal_code (PLZ): 5-digit German postal code
    - bundesland: Federal state code (e.g., HH, BY, NW)
    - address: Full address for geocoding
    """
    # Validate dates
    if request.end_date < request.start_date:
        raise HTTPException(
            status_code=400,
            detail="end_date must be after or equal to start_date",
        )

    # Validate location
    if not (request.postal_code or request.bundesland or request.address):
        raise HTTPException(
            status_code=400,
            detail="Provide at least one of: postal_code, bundesland, or address",
        )

    try:
        # Build location input
        bundesland_enum = None
        if request.bundesland:
            try:
                bundesland_enum = Bundesland(request.bundesland.upper())
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid bundesland code: {request.bundesland}. Use one of: {', '.join(b.value for b in Bundesland)}",
                )

        location = LocationInput(
            postal_code=request.postal_code,
            bundesland=bundesland_enum,
            address=request.address,
        )

        # Create workday request
        workday_request = WorkdayRequest(
            start_date=request.start_date,
            end_date=request.end_date,
            location=location,
            include_saturdays=request.include_saturdays,
        )

        # Calculate
        result = calculator.calculate(workday_request)

        return CalculateResponse(
            start_date=result.start_date,
            end_date=result.end_date,
            bundesland=result.location.bundesland.value,
            bundesland_name=result.location.bundesland_name,
            calendar_days=result.calendar_days,
            weekend_days=result.weekend_days,
            saturdays=result.weekends_detail.get("saturdays", 0),
            sundays=result.weekends_detail.get("sundays", 0),
            holidays_count=result.holidays_count,
            working_days=result.working_days,
            holidays=[
                {"date": h.date.isoformat(), "name": h.name, "is_national": h.is_national}
                for h in result.holidays
            ],
            confidence=result.confidence,
            resolution_method=result.location.resolution_method,
            warnings=result.warnings,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation error: {str(e)}")


@app.get("/holidays/{year}/{bundesland}", response_model=List[HolidayResponse])
async def get_holidays(
    year: int,
    bundesland: str,
):
    """
    Get all holidays for a specific year and Bundesland.

    Args:
        year: Year (e.g., 2024, 2025)
        bundesland: Bundesland code (e.g., HH, BY, NW)
    """
    # Validate bundesland
    try:
        bundesland_enum = Bundesland(bundesland.upper())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid bundesland code: {bundesland}. Use one of: {', '.join(b.value for b in Bundesland)}",
        )

    # Validate year
    if year < 1900 or year > 2100:
        raise HTTPException(
            status_code=400,
            detail="Year must be between 1900 and 2100",
        )

    try:
        holidays = holiday_provider.get_holidays_for_year(year, bundesland_enum)

        return [
            HolidayResponse(
                date=h.date,
                name=h.name,
                is_national=h.is_national,
            )
            for h in holidays
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching holidays: {str(e)}")


@app.get("/bundeslaender", response_model=List[BundeslandInfo])
async def list_bundeslaender():
    """
    List all German federal states with their codes.
    """
    return [
        BundeslandInfo(code=bundesland.value, name=BUNDESLAND_NAMES[bundesland])
        for bundesland in Bundesland
    ]


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}

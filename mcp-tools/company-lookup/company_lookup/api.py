"""FastAPI REST API for company lookup.

Supports bilingual operation (English/German) via:
- COMPANY_LOOKUP_LANGUAGE environment variable
- LANG environment variable
- Default: English
"""

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from company_lookup.config.manager import ConfigManager
from company_lookup.core.lookup_engine import LookupEngine
from company_lookup.data.schemas import CompanyStatus, Config, LookupRequest
from company_lookup.i18n import get_translator, t

logger = logging.getLogger(__name__)

# Global engine instance
_engine: Optional[LookupEngine] = None


def get_engine() -> LookupEngine:
    """Get the global lookup engine instance."""
    global _engine
    if _engine is None:
        raise HTTPException(
            status_code=503,
            detail=t("api.error.engine_not_initialized"),
        )
    return _engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    global _engine

    # Try to initialize from environment variable
    excel_file = os.environ.get("COMPANY_LOOKUP_EXCEL_FILE")
    if excel_file:
        try:
            config = ConfigManager().load()
            config.excel_file_path = excel_file
            _engine = LookupEngine(config=config)
            _engine.initialize(excel_file)
            logger.info(f"Initialized engine with: {excel_file}")
        except Exception as e:
            logger.warning(f"Failed to initialize engine: {e}")

    yield

    # Cleanup
    _engine = None


# Get translator for API descriptions
_api_translator = get_translator()

app = FastAPI(
    title=_api_translator("api.title"),
    description=_api_translator("api.description"),
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class LookupRequestModel(BaseModel):
    """Request model for company lookup."""

    company_name: str = Field(..., description="Company name to look up")
    threshold: float = Field(80.0, ge=0, le=100, description="Fuzzy matching threshold")
    max_results: int = Field(5, ge=1, le=20, description="Maximum results to return")
    include_partial: bool = Field(True, description="Include partial matches")


class MatchModel(BaseModel):
    """Model for a single match result."""

    company_name: str
    similarity_score: float
    status: str
    is_exact_match: bool
    notes: Optional[str] = None


class LookupResponseModel(BaseModel):
    """Response model for company lookup."""

    query: str
    status: str
    confidence: float
    is_approved: bool
    is_blocked: bool
    best_match: Optional[MatchModel] = None
    all_matches: list[MatchModel] = []
    warnings: list[str] = []
    timestamp: datetime


class CompanyModel(BaseModel):
    """Model for a company entry."""

    name: str
    status: str
    category: Optional[str] = None
    notes: Optional[str] = None


class StatsModel(BaseModel):
    """Model for company list statistics."""

    total_companies: int
    whitelisted_count: int
    blacklisted_count: int
    categories: list[str]
    last_updated: Optional[datetime] = None
    source_file: Optional[str] = None


class BatchLookupRequest(BaseModel):
    """Request model for batch lookup."""

    company_names: list[str] = Field(..., description="List of company names to look up")
    threshold: float = Field(80.0, ge=0, le=100, description="Fuzzy matching threshold")


class BatchLookupResponse(BaseModel):
    """Response model for batch lookup."""

    total_queries: int
    whitelisted: int
    blacklisted: int
    unknown: int
    results: list[LookupResponseModel]


@app.get("/")
async def root():
    """API information endpoint."""
    return {
        "name": t("api.title"),
        "version": "0.1.0",
        "description": t("api.description"),
        "endpoints": {
            "/lookup": "POST - " + t("api.lookup.description"),
            "/lookup/batch": "POST - " + t("api.batch.description"),
            "/companies": "GET - " + t("api.list_all.description"),
            "/companies/whitelist": "GET - " + t("api.list_whitelist.description"),
            "/companies/blacklist": "GET - " + t("api.list_blacklist.description"),
            "/stats": "GET - " + t("api.stats.description"),
            "/upload": "POST - " + t("api.upload.description"),
            "/health": "GET - " + t("api.health.description"),
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    global _engine
    return {
        "status": "healthy",
        "engine_initialized": _engine is not None and _engine.is_initialized,
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/lookup", response_model=LookupResponseModel)
async def lookup_company(request: LookupRequestModel):
    """Look up a company name in the whitelist/blacklist.

    Returns the company status (whitelisted, blacklisted, or unknown)
    along with confidence score and matching details.
    """
    engine = get_engine()

    lookup_request = LookupRequest(
        company_name=request.company_name,
        fuzzy_threshold=request.threshold,
        max_results=request.max_results,
        include_partial_matches=request.include_partial,
    )

    result = engine.lookup(lookup_request)

    return LookupResponseModel(
        query=result.query,
        status=result.status.value,
        confidence=result.confidence,
        is_approved=result.is_approved,
        is_blocked=result.is_blocked,
        best_match=(
            MatchModel(
                company_name=result.best_match.matched_name,
                similarity_score=result.best_match.similarity_score,
                status=result.best_match.status.value,
                is_exact_match=result.best_match.is_exact_match,
                notes=result.best_match.notes,
            )
            if result.best_match
            else None
        ),
        all_matches=[
            MatchModel(
                company_name=m.matched_name,
                similarity_score=m.similarity_score,
                status=m.status.value,
                is_exact_match=m.is_exact_match,
                notes=m.notes,
            )
            for m in result.all_matches
        ],
        warnings=result.warnings,
        timestamp=result.lookup_timestamp,
    )


@app.post("/lookup/batch", response_model=BatchLookupResponse)
async def batch_lookup(request: BatchLookupRequest):
    """Look up multiple company names at once.

    Returns aggregated results for all companies.
    """
    engine = get_engine()

    results = []
    for company_name in request.company_names:
        lookup_request = LookupRequest(
            company_name=company_name,
            fuzzy_threshold=request.threshold,
            max_results=3,
            include_partial_matches=False,
        )
        result = engine.lookup(lookup_request)

        results.append(
            LookupResponseModel(
                query=result.query,
                status=result.status.value,
                confidence=result.confidence,
                is_approved=result.is_approved,
                is_blocked=result.is_blocked,
                best_match=(
                    MatchModel(
                        company_name=result.best_match.matched_name,
                        similarity_score=result.best_match.similarity_score,
                        status=result.best_match.status.value,
                        is_exact_match=result.best_match.is_exact_match,
                        notes=result.best_match.notes,
                    )
                    if result.best_match
                    else None
                ),
                all_matches=[],
                warnings=result.warnings,
                timestamp=result.lookup_timestamp,
            )
        )

    whitelisted = sum(1 for r in results if r.is_approved)
    blacklisted = sum(1 for r in results if r.is_blocked)

    return BatchLookupResponse(
        total_queries=len(results),
        whitelisted=whitelisted,
        blacklisted=blacklisted,
        unknown=len(results) - whitelisted - blacklisted,
        results=results,
    )


@app.get("/companies", response_model=list[CompanyModel])
async def list_all_companies():
    """List all companies in the database."""
    engine = get_engine()
    companies = engine.get_all_companies()

    return [
        CompanyModel(
            name=c.name,
            status=c.status.value,
            category=c.category,
            notes=c.notes,
        )
        for c in companies
    ]


@app.get("/companies/whitelist", response_model=list[CompanyModel])
async def list_whitelisted():
    """List all whitelisted companies."""
    engine = get_engine()
    companies = engine.get_all_companies(CompanyStatus.WHITELISTED)

    return [
        CompanyModel(
            name=c.name,
            status=c.status.value,
            category=c.category,
            notes=c.notes,
        )
        for c in companies
    ]


@app.get("/companies/blacklist", response_model=list[CompanyModel])
async def list_blacklisted():
    """List all blacklisted companies."""
    engine = get_engine()
    companies = engine.get_all_companies(CompanyStatus.BLACKLISTED)

    return [
        CompanyModel(
            name=c.name,
            status=c.status.value,
            category=c.category,
            notes=c.notes,
        )
        for c in companies
    ]


@app.get("/stats", response_model=StatsModel)
async def get_stats():
    """Get statistics about the company lists."""
    engine = get_engine()
    stats = engine.get_stats()

    return StatsModel(
        total_companies=stats.total_companies,
        whitelisted_count=stats.whitelisted_count,
        blacklisted_count=stats.blacklisted_count,
        categories=stats.categories,
        last_updated=stats.last_updated,
        source_file=stats.source_file,
    )


@app.post("/upload")
async def upload_excel(file: UploadFile = File(...)):
    """Upload an Excel file with company lists.

    The file should have 'Whitelist' and 'Blacklist' sheets
    with a 'Company Name' column.
    """
    global _engine

    if not file.filename or not file.filename.endswith((".xlsx", ".xls", ".xlsm")):
        raise HTTPException(
            status_code=400,
            detail=t("api.error.invalid_file_format"),
        )

    # Save uploaded file temporarily
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        config = ConfigManager().load()
        config.excel_file_path = tmp_path
        _engine = LookupEngine(config=config)
        _engine.initialize(tmp_path)

        stats = _engine.get_stats()

        return {
            "message": t("api.success.upload"),
            "filename": file.filename,
            "stats": {
                "total_companies": stats.total_companies,
                "whitelisted": stats.whitelisted_count,
                "blacklisted": stats.blacklisted_count,
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=t("api.error.process_failed", error=str(e)),
        )


@app.post("/reload")
async def reload_data():
    """Reload company data from the Excel file."""
    engine = get_engine()

    try:
        count = engine.reload()
        return {
            "message": t("api.success.reload"),
            "companies_loaded": count,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=t("api.error.reload_failed", error=str(e)),
        )

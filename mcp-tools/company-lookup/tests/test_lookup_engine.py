"""Tests for the lookup engine module."""

import os
import tempfile
from pathlib import Path

import pytest
from openpyxl import Workbook

from company_lookup.core.lookup_engine import LookupEngine
from company_lookup.data.schemas import CompanyStatus, Config, LookupRequest


@pytest.fixture
def sample_excel_file():
    """Create a temporary Excel file with sample data."""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        workbook = Workbook()

        # Create Whitelist sheet
        ws_whitelist = workbook.active
        ws_whitelist.title = "Whitelist"
        ws_whitelist.append(["Company Name", "Category", "Notes"])
        ws_whitelist.append(["Siemens AG", "Technology", "Major German corporation"])
        ws_whitelist.append(["BMW Group", "Automotive", "Car manufacturer"])
        ws_whitelist.append(["SAP SE", "Software", "Enterprise software"])
        ws_whitelist.append(["Volkswagen AG", "Automotive", "Auto manufacturer"])
        ws_whitelist.append(["Bosch GmbH", "Technology", "Engineering company"])

        # Create Blacklist sheet
        ws_blacklist = workbook.create_sheet("Blacklist")
        ws_blacklist.append(["Company Name", "Category", "Notes"])
        ws_blacklist.append(["Fake Company GmbH", "Unknown", "Known scam company"])
        ws_blacklist.append(["Scam Industries Ltd", "Unknown", "Fraudulent business"])

        workbook.save(tmp.name)
        tmp_path = tmp.name

    yield tmp_path

    # Cleanup
    os.unlink(tmp_path)


@pytest.fixture
def engine(sample_excel_file):
    """Create an initialized LookupEngine."""
    config = Config(excel_file_path=sample_excel_file)
    engine = LookupEngine(config=config)
    engine.initialize(sample_excel_file)
    return engine


class TestInitialization:
    """Tests for engine initialization."""

    def test_initialize_with_valid_file(self, sample_excel_file):
        """Test initialization with a valid Excel file."""
        engine = LookupEngine()
        engine.initialize(sample_excel_file)
        assert engine.is_initialized

    def test_initialize_with_invalid_file(self):
        """Test initialization with non-existent file."""
        engine = LookupEngine()
        with pytest.raises(FileNotFoundError):
            engine.initialize("/nonexistent/file.xlsx")

    def test_initialize_without_file_path(self):
        """Test initialization without file path."""
        engine = LookupEngine()
        with pytest.raises(ValueError):
            engine.initialize(None)


class TestLookup:
    """Tests for the lookup method."""

    def test_exact_match_whitelisted(self, engine):
        """Test lookup with exact match on whitelist."""
        request = LookupRequest(company_name="Siemens AG")
        result = engine.lookup(request)

        assert result.status == CompanyStatus.WHITELISTED
        assert result.confidence == 1.0
        assert result.is_approved
        assert not result.is_blocked

    def test_exact_match_blacklisted(self, engine):
        """Test lookup with exact match on blacklist."""
        request = LookupRequest(company_name="Fake Company GmbH")
        result = engine.lookup(request)

        assert result.status == CompanyStatus.BLACKLISTED
        assert result.is_blocked
        assert not result.is_approved

    def test_fuzzy_match(self, engine):
        """Test lookup with fuzzy matching."""
        request = LookupRequest(company_name="Seimens", fuzzy_threshold=70.0)
        result = engine.lookup(request)

        assert result.status == CompanyStatus.WHITELISTED
        assert result.best_match is not None
        assert "Siemens" in result.best_match.matched_name

    def test_unknown_company(self, engine):
        """Test lookup with unknown company."""
        request = LookupRequest(company_name="Completely Unknown Corp", fuzzy_threshold=90.0)
        result = engine.lookup(request)

        assert result.status == CompanyStatus.UNKNOWN
        assert result.confidence == 0.0

    def test_lookup_returns_warnings(self, engine):
        """Test that warnings are included in results."""
        request = LookupRequest(company_name="Seimens", fuzzy_threshold=70.0)
        result = engine.lookup(request)

        # Should have fuzzy match warning
        assert len(result.warnings) > 0

    def test_multiple_matches(self, engine):
        """Test that multiple matches are returned."""
        request = LookupRequest(
            company_name="Company", fuzzy_threshold=30.0, max_results=5
        )
        result = engine.lookup(request)

        assert len(result.all_matches) > 0


class TestSimpleLookup:
    """Tests for the simplified lookup methods."""

    def test_lookup_simple(self, engine):
        """Test simplified lookup with lower threshold for short names."""
        # Short abbreviations like "BMW" need lower threshold (default 80% is too strict)
        result = engine.lookup_simple("BMW", threshold=70.0)
        assert result.status == CompanyStatus.WHITELISTED

    def test_is_approved_true(self, engine):
        """Test is_approved returns True for whitelisted."""
        assert engine.is_approved("BMW Group")

    def test_is_approved_false(self, engine):
        """Test is_approved returns False for unknown."""
        assert not engine.is_approved("Unknown Corp")

    def test_is_blocked_true(self, engine):
        """Test is_blocked returns True for blacklisted."""
        assert engine.is_blocked("Fake Company GmbH")

    def test_is_blocked_false(self, engine):
        """Test is_blocked returns False for whitelisted."""
        assert not engine.is_blocked("Siemens AG")


class TestStats:
    """Tests for statistics methods."""

    def test_get_stats(self, engine):
        """Test getting statistics."""
        stats = engine.get_stats()

        assert stats.total_companies == 7  # 5 whitelist + 2 blacklist
        assert stats.whitelisted_count == 5
        assert stats.blacklisted_count == 2
        assert stats.source_file is not None

    def test_stats_has_categories(self, engine):
        """Test that categories are tracked."""
        stats = engine.get_stats()
        assert len(stats.categories) > 0


class TestCompanyListing:
    """Tests for company listing methods."""

    def test_get_all_companies(self, engine):
        """Test getting all companies."""
        companies = engine.get_all_companies()
        assert len(companies) == 7

    def test_get_whitelisted_only(self, engine):
        """Test getting only whitelisted companies."""
        companies = engine.get_all_companies(CompanyStatus.WHITELISTED)
        assert len(companies) == 5
        assert all(c.status == CompanyStatus.WHITELISTED for c in companies)

    def test_get_blacklisted_only(self, engine):
        """Test getting only blacklisted companies."""
        companies = engine.get_all_companies(CompanyStatus.BLACKLISTED)
        assert len(companies) == 2
        assert all(c.status == CompanyStatus.BLACKLISTED for c in companies)


class TestAddCompany:
    """Tests for adding companies at runtime."""

    def test_add_whitelisted_company(self, engine):
        """Test adding a whitelisted company."""
        company = engine.add_company(
            name="New Tech Corp",
            status=CompanyStatus.WHITELISTED,
            notes="Newly approved",
        )

        assert company.name == "New Tech Corp"
        assert company.status == CompanyStatus.WHITELISTED

        # Verify it can be found
        result = engine.lookup_simple("New Tech Corp")
        assert result.is_approved

    def test_add_blacklisted_company(self, engine):
        """Test adding a blacklisted company."""
        engine.add_company(
            name="Bad Actor Inc",
            status=CompanyStatus.BLACKLISTED,
        )

        result = engine.lookup_simple("Bad Actor Inc")
        assert result.is_blocked


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_query(self, engine):
        """Test lookup with empty query."""
        with pytest.raises(ValueError):
            request = LookupRequest(company_name="")
            engine.lookup(request)

    def test_whitespace_only_query(self, engine):
        """Test lookup with whitespace-only query."""
        with pytest.raises(ValueError):
            request = LookupRequest(company_name="   ")
            engine.lookup(request)

    def test_very_long_company_name(self, engine):
        """Test lookup with very long company name."""
        long_name = "A" * 500 + " GmbH"
        request = LookupRequest(company_name=long_name)
        result = engine.lookup(request)
        assert result.status == CompanyStatus.UNKNOWN

    def test_special_characters_in_name(self, engine):
        """Test lookup with special characters."""
        request = LookupRequest(company_name="Test & Partners GmbH")
        result = engine.lookup(request)
        # Should not raise an error
        assert result is not None

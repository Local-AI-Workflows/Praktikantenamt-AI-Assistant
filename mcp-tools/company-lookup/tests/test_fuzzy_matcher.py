"""Tests for the fuzzy matcher module."""

import pytest

from company_lookup.core.fuzzy_matcher import FuzzyMatcher
from company_lookup.data.schemas import CompanyInfo, CompanyStatus


@pytest.fixture
def matcher():
    """Create a FuzzyMatcher instance."""
    return FuzzyMatcher(case_sensitive=False)


@pytest.fixture
def sample_companies():
    """Create sample company data for testing."""
    return {
        "siemens ag": CompanyInfo(
            name="Siemens AG",
            status=CompanyStatus.WHITELISTED,
            category="Technology",
        ),
        "bmw group": CompanyInfo(
            name="BMW Group",
            status=CompanyStatus.WHITELISTED,
            category="Automotive",
        ),
        "sap se": CompanyInfo(
            name="SAP SE",
            status=CompanyStatus.WHITELISTED,
            category="Software",
        ),
        "fake company gmbh": CompanyInfo(
            name="Fake Company GmbH",
            status=CompanyStatus.BLACKLISTED,
            notes="Known scam",
        ),
        "volkswagen ag": CompanyInfo(
            name="Volkswagen AG",
            status=CompanyStatus.WHITELISTED,
            category="Automotive",
        ),
    }


class TestNormalization:
    """Tests for company name normalization."""

    def test_strip_whitespace(self, matcher):
        """Test that whitespace is stripped."""
        assert matcher.normalize_company_name("  Siemens AG  ") == "siemens"

    def test_remove_gmbh_suffix(self, matcher):
        """Test that GmbH suffix is removed."""
        assert matcher.normalize_company_name("Test GmbH") == "test"

    def test_remove_ag_suffix(self, matcher):
        """Test that AG suffix is removed."""
        assert matcher.normalize_company_name("Siemens AG") == "siemens"

    def test_remove_se_suffix(self, matcher):
        """Test that SE suffix is removed."""
        assert matcher.normalize_company_name("SAP SE") == "sap"

    def test_remove_complex_suffix(self, matcher):
        """Test that complex suffixes are removed."""
        result = matcher.normalize_company_name("Test GmbH & Co. KG")
        assert "gmbh" not in result.lower()

    def test_empty_string(self, matcher):
        """Test handling of empty strings."""
        assert matcher.normalize_company_name("") == ""
        assert matcher.normalize_company_name("   ") == ""

    def test_case_insensitive(self, matcher):
        """Test case-insensitive normalization."""
        assert matcher.normalize_company_name("SIEMENS AG") == "siemens"
        assert matcher.normalize_company_name("siemens ag") == "siemens"


class TestSimilarityCalculation:
    """Tests for similarity score calculation."""

    def test_exact_match_after_normalization(self, matcher):
        """Test that normalized exact matches score 100."""
        score = matcher.calculate_similarity("Siemens AG", "Siemens AG")
        assert score == 100.0

    def test_similar_names(self, matcher):
        """Test that similar names have high scores."""
        score = matcher.calculate_similarity("Siemens", "Siemens AG")
        assert score > 80.0

    def test_different_names(self, matcher):
        """Test that different names have low scores."""
        score = matcher.calculate_similarity("Apple", "Microsoft")
        assert score < 50.0

    def test_typo_handling(self, matcher):
        """Test that typos still match reasonably."""
        score = matcher.calculate_similarity("Seimens", "Siemens")
        assert score > 70.0

    def test_word_order(self, matcher):
        """Test that word order differences are handled."""
        score = matcher.calculate_similarity("Group BMW", "BMW Group")
        assert score > 80.0


class TestFindMatches:
    """Tests for the find_matches method."""

    def test_exact_match(self, matcher, sample_companies):
        """Test finding an exact match."""
        matches = matcher.find_matches("Siemens AG", sample_companies, threshold=80.0)
        assert len(matches) >= 1
        assert matches[0].matched_name == "Siemens AG"
        assert matches[0].is_exact_match

    def test_fuzzy_match(self, matcher, sample_companies):
        """Test finding a fuzzy match."""
        matches = matcher.find_matches("Seimens", sample_companies, threshold=70.0)
        assert len(matches) >= 1
        assert "Siemens" in matches[0].matched_name

    def test_no_match_below_threshold(self, matcher, sample_companies):
        """Test that no matches are returned below threshold."""
        matches = matcher.find_matches("Completely Different", sample_companies, threshold=90.0)
        assert len(matches) == 0

    def test_max_results(self, matcher, sample_companies):
        """Test that max_results is respected."""
        matches = matcher.find_matches("Company", sample_companies, threshold=20.0, max_results=2)
        assert len(matches) <= 2

    def test_status_in_results(self, matcher, sample_companies):
        """Test that status is correctly included in results."""
        matches = matcher.find_matches("Fake Company", sample_companies, threshold=70.0)
        assert len(matches) >= 1
        assert matches[0].status == CompanyStatus.BLACKLISTED

    def test_sorted_by_score(self, matcher, sample_companies):
        """Test that results are sorted by score descending."""
        matches = matcher.find_matches("Company", sample_companies, threshold=20.0)
        if len(matches) > 1:
            for i in range(len(matches) - 1):
                assert matches[i].similarity_score >= matches[i + 1].similarity_score


class TestFindBestMatch:
    """Tests for the find_best_match method."""

    def test_returns_best_match(self, matcher, sample_companies):
        """Test that the best match is returned."""
        match = matcher.find_best_match("BMW", sample_companies, threshold=70.0)
        assert match is not None
        assert match.matched_name == "BMW Group"

    def test_returns_none_when_no_match(self, matcher, sample_companies):
        """Test that None is returned when no match found."""
        match = matcher.find_best_match("XYZ Corp", sample_companies, threshold=90.0)
        assert match is None


class TestBatchMatch:
    """Tests for the batch_match method."""

    def test_batch_multiple_queries(self, matcher, sample_companies):
        """Test batch matching with multiple queries."""
        queries = ["Siemens", "BMW", "Unknown Corp"]
        results = matcher.batch_match(queries, sample_companies, threshold=70.0)

        assert len(results) == 3
        assert "Siemens" in results
        assert results["Siemens"] is not None
        assert results["BMW"] is not None
        assert results["Unknown Corp"] is None


class TestSuggestThreshold:
    """Tests for the suggest_threshold method."""

    def test_short_name_high_threshold(self):
        """Test that short names get higher threshold."""
        threshold = FuzzyMatcher.suggest_threshold("SAP")
        assert threshold >= 90.0

    def test_medium_name_medium_threshold(self):
        """Test that medium names get medium threshold."""
        threshold = FuzzyMatcher.suggest_threshold("Siemens")
        assert 80.0 <= threshold <= 90.0

    def test_long_name_lower_threshold(self):
        """Test that long names get lower threshold."""
        threshold = FuzzyMatcher.suggest_threshold("Siemens Energy Solutions GmbH")
        assert threshold <= 85.0

"""Main lookup engine combining Excel reader and fuzzy matcher.

Supports bilingual operation (English/German) via the i18n module.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from company_lookup.core.excel_reader import ExcelReader
from company_lookup.core.fuzzy_matcher import FuzzyMatcher
from company_lookup.data.schemas import (
    CompanyInfo,
    CompanyListStats,
    CompanyStatus,
    Config,
    LookupRequest,
    LookupResult,
    MatchResult,
)
from company_lookup.i18n import t

logger = logging.getLogger(__name__)


class LookupEngine:
    """Main engine for company lookup operations."""

    def __init__(
        self,
        config: Optional[Config] = None,
        excel_reader: Optional[ExcelReader] = None,
        fuzzy_matcher: Optional[FuzzyMatcher] = None,
    ):
        """Initialize the lookup engine.

        Args:
            config: Configuration for the engine.
            excel_reader: Excel reader instance (created if not provided).
            fuzzy_matcher: Fuzzy matcher instance (created if not provided).
        """
        self.config = config or Config()
        self.excel_reader = excel_reader or ExcelReader(self.config)
        self.fuzzy_matcher = fuzzy_matcher or FuzzyMatcher(
            case_sensitive=self.config.case_sensitive
        )
        self._initialized = False

    def initialize(self, excel_file_path: Optional[str] = None) -> None:
        """Initialize the engine by loading company data.

        Args:
            excel_file_path: Path to the Excel file (overrides config).

        Raises:
            FileNotFoundError: If Excel file not found.
            ValueError: If Excel file is invalid.
        """
        file_path = excel_file_path or self.config.excel_file_path
        if not file_path:
            raise ValueError(t("engine.error.no_excel_path"))

        self.excel_reader.load_from_file(file_path)
        self._initialized = True
        logger.info(t("engine.info.initialized"))

    @property
    def is_initialized(self) -> bool:
        """Check if the engine is initialized."""
        return self._initialized and len(self.excel_reader.companies) > 0

    def lookup(self, request: LookupRequest) -> LookupResult:
        """Perform a company lookup.

        Args:
            request: The lookup request with query and parameters.

        Returns:
            LookupResult with status and matches.

        Raises:
            RuntimeError: If engine not initialized.
        """
        if not self.is_initialized:
            raise RuntimeError(t("engine.error.not_initialized"))

        query = request.company_name
        threshold = request.fuzzy_threshold
        max_results = request.max_results

        logger.debug(f"Looking up company: {query} (threshold: {threshold})")

        # Find matches
        matches = self.fuzzy_matcher.find_matches(
            query=query,
            companies=self.excel_reader.companies,
            threshold=threshold if not request.include_partial_matches else 0.0,
            max_results=max_results * 2,  # Get extra for filtering
        )

        # Filter by threshold if needed
        above_threshold = [m for m in matches if m.similarity_score >= threshold]
        below_threshold = [
            m for m in matches if m.similarity_score < threshold
        ][:max_results]

        # Determine overall status and confidence
        status, confidence, warnings = self._determine_status(
            query, above_threshold, threshold
        )

        # Prepare final matches list
        all_matches = above_threshold[:max_results]
        if request.include_partial_matches and len(all_matches) < max_results:
            remaining_slots = max_results - len(all_matches)
            all_matches.extend(below_threshold[:remaining_slots])

        result = LookupResult(
            query=query,
            status=status,
            confidence=confidence,
            best_match=above_threshold[0] if above_threshold else None,
            all_matches=all_matches,
            warnings=warnings,
            lookup_timestamp=datetime.now(),
        )

        logger.debug(f"Lookup result: status={status}, confidence={confidence}")
        return result

    def _determine_status(
        self,
        query: str,
        matches: list[MatchResult],
        threshold: float,
    ) -> tuple[CompanyStatus, float, list[str]]:
        """Determine the overall status from matches.

        Args:
            query: Original search query.
            matches: List of matches above threshold.
            threshold: The threshold used for matching.

        Returns:
            Tuple of (status, confidence, warnings).
        """
        warnings = []

        if not matches:
            return CompanyStatus.UNKNOWN, 0.0, [t("engine.warning.no_matches")]

        best_match = matches[0]

        # Check for exact match
        if best_match.is_exact_match:
            return best_match.status, 1.0, []

        # Calculate confidence based on score and gap to next match
        score = best_match.similarity_score
        confidence = score / 100.0

        # Reduce confidence if score is near threshold
        if score < threshold + 10:
            confidence *= 0.9
            warnings.append(t("engine.warning.near_threshold"))

        # Check for conflicting matches (whitelist and blacklist matches)
        statuses = set(m.status for m in matches)
        if CompanyStatus.WHITELISTED in statuses and CompanyStatus.BLACKLISTED in statuses:
            warnings.append(t("engine.warning.conflicting"))
            confidence *= 0.7

        # Check if top matches are close in score
        if len(matches) > 1:
            score_gap = best_match.similarity_score - matches[1].similarity_score
            if score_gap < 5:
                warnings.append(t("engine.warning.multiple_close"))
                confidence *= 0.9

        # Warn if company name is very different from match
        if score < 90 and not best_match.is_exact_match:
            warnings.append(
                t("engine.warning.fuzzy_match", query=query, matched=best_match.matched_name)
            )

        return best_match.status, round(confidence, 2), warnings

    def lookup_simple(
        self,
        company_name: str,
        threshold: float = 80.0,
    ) -> LookupResult:
        """Simplified lookup with default parameters.

        Args:
            company_name: The company name to look up.
            threshold: Minimum similarity score.

        Returns:
            LookupResult with status and matches.
        """
        request = LookupRequest(
            company_name=company_name,
            fuzzy_threshold=threshold,
            include_partial_matches=True,
            max_results=5,
        )
        return self.lookup(request)

    def is_approved(self, company_name: str, threshold: float = 80.0) -> bool:
        """Quick check if a company is approved (whitelisted).

        Args:
            company_name: The company name to check.
            threshold: Minimum similarity score.

        Returns:
            True if company is whitelisted with sufficient confidence.
        """
        result = self.lookup_simple(company_name, threshold)
        return result.is_approved and result.confidence >= 0.8

    def is_blocked(self, company_name: str, threshold: float = 80.0) -> bool:
        """Quick check if a company is blocked (blacklisted).

        Args:
            company_name: The company name to check.
            threshold: Minimum similarity score.

        Returns:
            True if company is blacklisted with sufficient confidence.
        """
        result = self.lookup_simple(company_name, threshold)
        return result.is_blocked and result.confidence >= 0.8

    def get_stats(self) -> CompanyListStats:
        """Get statistics about the loaded company lists.

        Returns:
            CompanyListStats with current statistics.
        """
        stats = self.excel_reader.get_stats()
        return CompanyListStats(**stats)

    def get_all_companies(self, status: Optional[CompanyStatus] = None) -> list[CompanyInfo]:
        """Get all companies, optionally filtered by status.

        Args:
            status: Filter by status (None for all).

        Returns:
            List of CompanyInfo objects.
        """
        if status is None:
            return list(self.excel_reader.companies.values())
        elif status == CompanyStatus.WHITELISTED:
            return self.excel_reader.whitelisted
        elif status == CompanyStatus.BLACKLISTED:
            return self.excel_reader.blacklisted
        else:
            return []

    def add_company(
        self,
        name: str,
        status: CompanyStatus,
        notes: Optional[str] = None,
        category: Optional[str] = None,
    ) -> CompanyInfo:
        """Add a company to the in-memory list.

        Note: This does not persist to the Excel file.

        Args:
            name: Company name.
            status: Whitelist or blacklist status.
            notes: Optional notes.
            category: Optional category.

        Returns:
            The created CompanyInfo object.
        """
        company = CompanyInfo(
            name=name,
            status=status,
            notes=notes,
            category=category,
            added_date=datetime.now(),
        )
        key = name.lower().strip()
        self.excel_reader._companies[key] = company
        logger.info(t("engine.info.added_company", name=name, status=status.value))
        return company

    def reload(self) -> int:
        """Reload company data from the Excel file.

        Returns:
            Number of companies loaded.
        """
        if not self.config.excel_file_path:
            raise ValueError(t("engine.error.no_excel_configured"))
        return self.excel_reader.load_from_file(self.config.excel_file_path)

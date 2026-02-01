"""Fuzzy matching engine for company names using rapidfuzz.

Enhanced with:
- Parenthetical content removal
- Hyphen normalization
- Adaptive weights based on query length
- Token containment boosting
"""

import logging
import re
from typing import Optional

from rapidfuzz import fuzz, process
from rapidfuzz.utils import default_process

from company_lookup.data.schemas import CompanyInfo, CompanyStatus, MatchResult

logger = logging.getLogger(__name__)


class FuzzyMatcher:
    """Fuzzy string matching for company names."""

    # Common German company suffixes to normalize
    COMPANY_SUFFIXES = [
        r"\bGmbH\b",
        r"\bAG\b",
        r"\bSE\b",
        r"\bKG\b",
        r"\bOHG\b",
        r"\be\.V\.\b",
        r"\bGmbH & Co\. KG\b",
        r"\bGmbH & Co\.KG\b",
        r"\bInc\.?\b",
        r"\bLtd\.?\b",
        r"\bLLC\b",
        r"\bCorp\.?\b",
        r"\bCorporation\b",
        r"\bCompany\b",
        r"\bCo\.?\b",
        r"\b& Co\.\b",
        r"\bUG\b",
        r"\bUG \(haftungsbeschränkt\)\b",
    ]

    # Pattern to remove parenthetical content (e.g., "BMW (Automotive)" -> "BMW")
    _PAREN_PATTERN = re.compile(r"\s*\([^)]*\)\s*")

    # Pattern to normalize various hyphen/dash characters to space
    _HYPHEN_PATTERN = re.compile(r"[-\u2010\u2011\u2012\u2013\u2014]")

    def __init__(self, case_sensitive: bool = False):
        """Initialize the fuzzy matcher.

        Args:
            case_sensitive: Whether matching should be case-sensitive.
        """
        self.case_sensitive = case_sensitive
        self._suffix_pattern = re.compile(
            "|".join(self.COMPANY_SUFFIXES), re.IGNORECASE if not case_sensitive else 0
        )

    def normalize_company_name(self, name: str) -> str:
        """Normalize a company name for better matching.

        Applies:
        - Case normalization
        - Parenthetical content removal
        - Hyphen normalization to spaces
        - Legal suffix removal
        - Whitespace cleanup

        Args:
            name: The company name to normalize.

        Returns:
            Normalized company name.
        """
        if not name:
            return ""

        # Strip whitespace
        normalized = name.strip()

        # Convert case if not case-sensitive
        if not self.case_sensitive:
            normalized = normalized.lower()

        # Remove parenthetical content (e.g., "BMW (Automotive)" -> "BMW")
        normalized = self._PAREN_PATTERN.sub(" ", normalized)

        # Normalize hyphens to spaces for better token matching
        # "Mercedes-Benz" -> "Mercedes Benz"
        normalized = self._HYPHEN_PATTERN.sub(" ", normalized)

        # Remove common suffixes for comparison
        normalized = self._suffix_pattern.sub("", normalized)

        # Clean up multiple spaces and trim
        normalized = re.sub(r"\s+", " ", normalized).strip()

        return normalized

    def calculate_similarity(self, query: str, target: str) -> float:
        """Calculate similarity between two company names.

        Uses adaptive weighting based on query characteristics:
        - Short queries (≤4 chars): Trust partial matching more
        - Single-word queries: Balance partial and token matching
        - Multi-word queries: Trust token-based matching more

        Also applies token containment boosting when query tokens
        are found within target.

        Args:
            query: The search query.
            target: The target company name.

        Returns:
            Similarity score from 0-100.
        """
        # Normalize both strings
        norm_query = self.normalize_company_name(query)
        norm_target = self.normalize_company_name(target)

        if not norm_query or not norm_target:
            return 0.0

        # Quick exact match check
        if norm_query == norm_target:
            return 100.0

        # Check prefix relationship (e.g., "Siemens" vs "Siemens AG" after normalization)
        if norm_target.startswith(norm_query) or norm_query.startswith(norm_target):
            shorter = min(len(norm_query), len(norm_target))
            longer = max(len(norm_query), len(norm_target))
            prefix_score = (shorter / longer) * 95
            if prefix_score >= 85:
                return prefix_score

        # Token analysis
        query_tokens = set(norm_query.split())
        target_tokens = set(norm_target.split())

        # Token containment: what fraction of query tokens appear in target?
        if query_tokens:
            intersection = len(query_tokens & target_tokens)
            token_containment = (intersection / len(query_tokens)) * 100
        else:
            token_containment = 0.0

        # Character-level fuzzy scores
        simple_ratio = fuzz.ratio(norm_query, norm_target)
        partial_ratio = fuzz.partial_ratio(norm_query, norm_target)
        token_sort_ratio = fuzz.token_sort_ratio(norm_query, norm_target)
        token_set_ratio = fuzz.token_set_ratio(norm_query, norm_target)

        # Adaptive weighting based on query characteristics
        query_len = len(norm_query)
        num_query_tokens = len(query_tokens)

        if query_len <= 4:
            # Very short queries: trust partial matching more
            combined_score = (
                simple_ratio * 0.10
                + partial_ratio * 0.40
                + token_sort_ratio * 0.20
                + token_set_ratio * 0.20
                + token_containment * 0.10
            )
        elif num_query_tokens == 1:
            # Single-word queries: balance partial and token matching
            combined_score = (
                simple_ratio * 0.15
                + partial_ratio * 0.30
                + token_sort_ratio * 0.25
                + token_set_ratio * 0.20
                + token_containment * 0.10
            )
        else:
            # Multi-word queries: trust token-based matching
            combined_score = (
                simple_ratio * 0.10
                + partial_ratio * 0.20
                + token_sort_ratio * 0.30
                + token_set_ratio * 0.30
                + token_containment * 0.10
            )

        # Token containment boost: if all query tokens found in target, boost score
        if token_containment >= 100 and combined_score < 90:
            combined_score = max(combined_score, 88.0)
        elif token_containment >= 50 and combined_score < 80:
            # At least half of query tokens found - moderate boost
            boost = min(10.0, (token_containment - 50) * 0.2)
            combined_score = combined_score + boost

        return min(100.0, combined_score)

    def find_matches(
        self,
        query: str,
        companies: dict[str, CompanyInfo],
        threshold: float = 80.0,
        max_results: int = 5,
    ) -> list[MatchResult]:
        """Find matching companies using fuzzy matching.

        Args:
            query: The company name to search for.
            companies: Dictionary of companies to search in.
            threshold: Minimum similarity score (0-100).
            max_results: Maximum number of results to return.

        Returns:
            List of MatchResult objects sorted by score descending.
        """
        if not query or not companies:
            return []

        results: list[MatchResult] = []
        norm_query = self.normalize_company_name(query)

        for key, company in companies.items():
            # Check for exact match first
            is_exact = (
                query.lower().strip() == company.name.lower().strip()
                if not self.case_sensitive
                else query.strip() == company.name.strip()
            )

            if is_exact:
                results.append(
                    MatchResult(
                        matched_name=company.name,
                        original_query=query,
                        similarity_score=100.0,
                        status=company.status,
                        notes=company.notes,
                        is_exact_match=True,
                    )
                )
                continue

            # Calculate fuzzy similarity
            score = self.calculate_similarity(query, company.name)

            if score >= threshold:
                results.append(
                    MatchResult(
                        matched_name=company.name,
                        original_query=query,
                        similarity_score=round(score, 2),
                        status=company.status,
                        notes=company.notes,
                        is_exact_match=False,
                    )
                )

        # Sort by score descending
        results.sort(key=lambda x: x.similarity_score, reverse=True)

        return results[:max_results]

    def find_best_match(
        self,
        query: str,
        companies: dict[str, CompanyInfo],
        threshold: float = 80.0,
    ) -> Optional[MatchResult]:
        """Find the single best matching company.

        Args:
            query: The company name to search for.
            companies: Dictionary of companies to search in.
            threshold: Minimum similarity score (0-100).

        Returns:
            Best MatchResult or None if no match found.
        """
        matches = self.find_matches(query, companies, threshold, max_results=1)
        return matches[0] if matches else None

    def batch_match(
        self,
        queries: list[str],
        companies: dict[str, CompanyInfo],
        threshold: float = 80.0,
    ) -> dict[str, Optional[MatchResult]]:
        """Perform batch matching for multiple queries.

        Args:
            queries: List of company names to search for.
            companies: Dictionary of companies to search in.
            threshold: Minimum similarity score (0-100).

        Returns:
            Dictionary mapping queries to their best match result.
        """
        results = {}
        for query in queries:
            results[query] = self.find_best_match(query, companies, threshold)
        return results

    @staticmethod
    def suggest_threshold(query: str) -> float:
        """Suggest an appropriate threshold based on query characteristics.

        Args:
            query: The search query.

        Returns:
            Suggested threshold value.
        """
        # Shorter names need higher threshold to avoid false matches
        if len(query) < 5:
            return 90.0
        elif len(query) < 10:
            return 85.0
        else:
            return 80.0

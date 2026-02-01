"""MCP Server for company lookup with SSE and stdio transport support.

Supports bilingual operation (English/German) via:
- COMPANY_LOOKUP_LANGUAGE environment variable
- LANG environment variable
- Default: English
"""

import argparse
import logging
import os
import sys
from typing import Optional

from mcp.server.fastmcp import FastMCP

from company_lookup.config.manager import ConfigManager
from company_lookup.core.lookup_engine import LookupEngine
from company_lookup.data.schemas import CompanyStatus, LookupRequest
from company_lookup.i18n import get_translator, t

logger = logging.getLogger(__name__)

# Global engine instance
_engine: Optional[LookupEngine] = None


def get_engine() -> LookupEngine:
    """Get or initialize the lookup engine."""
    global _engine

    if _engine is None:
        excel_file = os.environ.get("COMPANY_LOOKUP_EXCEL_FILE")
        if not excel_file:
            raise RuntimeError(t("mcp.error.excel_not_set"))

        config = ConfigManager().load()
        config.excel_file_path = excel_file
        _engine = LookupEngine(config=config)
        _engine.initialize(excel_file)
        logger.info(t("mcp.info.initialized", file=excel_file))

    return _engine


def create_mcp_server(host: str = "0.0.0.0", port: int = 8080) -> FastMCP:
    """Create and configure the MCP server.

    Args:
        host: Host to bind to (for SSE transport).
        port: Port to listen on (for SSE transport).

    Returns:
        Configured FastMCP server instance.
    """
    # Get translator for bilingual support
    translator = get_translator()

    mcp = FastMCP(
        translator("mcp.server_name"),
        host=host,
        port=port,
    )

    @mcp.tool(
        description=f"{translator('mcp.lookup_company.description')}\n\n{translator('mcp.lookup_company.details')}"
    )
    def lookup_company(
        company_name: str,
        threshold: float = 80.0,
        max_results: int = 5,
    ) -> dict:
        """Look up a company in the whitelist/blacklist database.

        Use this tool to check if a company is approved (whitelisted) or
        blocked (blacklisted) for internships. The tool uses fuzzy matching
        to find similar company names even with typos or variations.

        Args:
            company_name: The name of the company to look up.
            threshold: Minimum similarity score (0-100) for fuzzy matching.
                       Higher values require closer matches. Default: 80.
            max_results: Maximum number of matching companies to return.
                         Default: 5.

        Returns:
            Dictionary containing:
            - query: The original search query
            - status: "whitelisted", "blacklisted", or "unknown"
            - confidence: Confidence score (0-1) in the result
            - is_approved: True if company is approved for internships
            - is_blocked: True if company is blocked from internships
            - best_match: Details of the closest matching company (if any)
            - all_matches: List of all matches above threshold
            - warnings: Any warnings or notes about the result
        """
        try:
            engine = get_engine()

            request = LookupRequest(
                company_name=company_name,
                fuzzy_threshold=threshold,
                max_results=max_results,
                include_partial_matches=True,
            )

            result = engine.lookup(request)

            return {
                "query": result.query,
                "status": result.status.value,
                "confidence": result.confidence,
                "is_approved": result.is_approved,
                "is_blocked": result.is_blocked,
                "best_match": (
                    {
                        "company_name": result.best_match.matched_name,
                        "similarity_score": result.best_match.similarity_score,
                        "status": result.best_match.status.value,
                        "is_exact_match": result.best_match.is_exact_match,
                        "notes": result.best_match.notes,
                    }
                    if result.best_match
                    else None
                ),
                "all_matches": [
                    {
                        "company_name": m.matched_name,
                        "similarity_score": m.similarity_score,
                        "status": m.status.value,
                        "is_exact_match": m.is_exact_match,
                    }
                    for m in result.all_matches
                ],
                "warnings": result.warnings,
            }
        except Exception as e:
            logger.error(translator("mcp.error.lookup_failed", error=str(e)))
            return {
                "error": str(e),
                "query": company_name,
                "status": "error",
                "confidence": 0.0,
                "is_approved": False,
                "is_blocked": False,
            }

    @mcp.tool(
        description=f"{translator('mcp.check_approved.description')}\n\n{translator('mcp.check_approved.details')}"
    )
    def check_company_approved(company_name: str, threshold: float = 80.0) -> dict:
        """Quick check if a company is approved for internships.

        This is a simplified lookup that returns a boolean result
        indicating whether the company is on the whitelist.

        Args:
            company_name: The name of the company to check.
            threshold: Minimum similarity score for matching. Default: 80.

        Returns:
            Dictionary containing:
            - company_name: The queried company name
            - is_approved: True if company is whitelisted
            - confidence: Confidence in the result
            - matched_name: The matched company name (if any)
        """
        try:
            engine = get_engine()
            result = engine.lookup_simple(company_name, threshold)

            return {
                "company_name": company_name,
                "is_approved": result.is_approved and result.confidence >= 0.8,
                "confidence": result.confidence,
                "matched_name": result.best_match.matched_name if result.best_match else None,
            }
        except Exception as e:
            logger.error(translator("mcp.error.check_approved_failed", error=str(e)))
            return {
                "company_name": company_name,
                "is_approved": False,
                "confidence": 0.0,
                "error": str(e),
            }

    @mcp.tool(
        description=f"{translator('mcp.check_blocked.description')}\n\n{translator('mcp.check_blocked.details')}"
    )
    def check_company_blocked(company_name: str, threshold: float = 80.0) -> dict:
        """Quick check if a company is blocked from internships.

        This is a simplified lookup that returns a boolean result
        indicating whether the company is on the blacklist.

        Args:
            company_name: The name of the company to check.
            threshold: Minimum similarity score for matching. Default: 80.

        Returns:
            Dictionary containing:
            - company_name: The queried company name
            - is_blocked: True if company is blacklisted
            - confidence: Confidence in the result
            - matched_name: The matched company name (if any)
        """
        try:
            engine = get_engine()
            result = engine.lookup_simple(company_name, threshold)

            return {
                "company_name": company_name,
                "is_blocked": result.is_blocked and result.confidence >= 0.8,
                "confidence": result.confidence,
                "matched_name": result.best_match.matched_name if result.best_match else None,
            }
        except Exception as e:
            logger.error(translator("mcp.error.check_blocked_failed", error=str(e)))
            return {
                "company_name": company_name,
                "is_blocked": False,
                "confidence": 0.0,
                "error": str(e),
            }

    @mcp.tool(description=translator("mcp.list_companies.description"))
    def list_companies(status: str = "all") -> dict:
        """List companies in the database.

        Args:
            status: Filter by status - "all", "whitelist", or "blacklist".
                    Default: "all".

        Returns:
            Dictionary containing:
            - count: Number of companies returned
            - status_filter: The filter applied
            - companies: List of company names with their status
        """
        try:
            engine = get_engine()

            status_filter = None
            if status == "whitelist":
                status_filter = CompanyStatus.WHITELISTED
            elif status == "blacklist":
                status_filter = CompanyStatus.BLACKLISTED

            companies = engine.get_all_companies(status_filter)

            return {
                "count": len(companies),
                "status_filter": status,
                "companies": [
                    {
                        "name": c.name,
                        "status": c.status.value,
                        "category": c.category,
                    }
                    for c in companies
                ],
            }
        except Exception as e:
            logger.error(translator("mcp.error.list_failed", error=str(e)))
            return {
                "error": str(e),
                "count": 0,
                "companies": [],
            }

    @mcp.tool(description=translator("mcp.stats.description"))
    def get_company_stats() -> dict:
        """Get statistics about the company database.

        Returns:
            Dictionary containing:
            - total_companies: Total number of companies
            - whitelisted_count: Number of whitelisted companies
            - blacklisted_count: Number of blacklisted companies
            - categories: List of company categories
            - source_file: Path to the source Excel file
        """
        try:
            engine = get_engine()
            stats = engine.get_stats()

            return {
                "total_companies": stats.total_companies,
                "whitelisted_count": stats.whitelisted_count,
                "blacklisted_count": stats.blacklisted_count,
                "categories": stats.categories,
                "source_file": stats.source_file,
                "last_updated": (
                    stats.last_updated.isoformat() if stats.last_updated else None
                ),
            }
        except Exception as e:
            logger.error(translator("mcp.error.stats_failed", error=str(e)))
            return {
                "error": str(e),
                "total_companies": 0,
            }

    @mcp.tool(
        description=f"{translator('mcp.batch.description')}\n\n{translator('mcp.batch.details')}"
    )
    def batch_lookup(company_names: list[str], threshold: float = 80.0) -> dict:
        """Look up multiple companies at once.

        Useful for validating a list of companies from a contract
        or processing multiple inquiries.

        Args:
            company_names: List of company names to look up.
            threshold: Minimum similarity score for matching. Default: 80.

        Returns:
            Dictionary containing:
            - total: Total number of companies looked up
            - summary: Counts of whitelisted, blacklisted, and unknown
            - results: List of lookup results for each company
        """
        try:
            engine = get_engine()

            results = []
            for name in company_names:
                request = LookupRequest(
                    company_name=name,
                    fuzzy_threshold=threshold,
                    max_results=1,
                    include_partial_matches=False,
                )
                result = engine.lookup(request)
                results.append({
                    "company_name": name,
                    "status": result.status.value,
                    "confidence": result.confidence,
                    "is_approved": result.is_approved,
                    "is_blocked": result.is_blocked,
                    "matched_name": (
                        result.best_match.matched_name if result.best_match else None
                    ),
                })

            whitelisted = sum(1 for r in results if r["is_approved"])
            blacklisted = sum(1 for r in results if r["is_blocked"])

            return {
                "total": len(results),
                "summary": {
                    "whitelisted": whitelisted,
                    "blacklisted": blacklisted,
                    "unknown": len(results) - whitelisted - blacklisted,
                },
                "results": results,
            }
        except Exception as e:
            logger.error(translator("mcp.error.batch_failed", error=str(e)))
            return {
                "error": str(e),
                "total": 0,
                "results": [],
            }

    return mcp


def main():
    """Main entry point for the MCP server."""
    parser = argparse.ArgumentParser(
        description="Company Lookup MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
  COMPANY_LOOKUP_EXCEL_FILE  Path to the Excel file with company lists (required)
  MCP_TRANSPORT              Transport type: 'stdio' or 'sse' (default: stdio)
  MCP_HOST                   Host for SSE transport (default: 0.0.0.0)
  MCP_PORT                   Port for SSE transport (default: 8080)

Examples:
  # Run with stdio transport (for local Claude Desktop)
  company-lookup-mcp --transport stdio

  # Run with SSE transport (for Docker/remote access)
  company-lookup-mcp --transport sse --port 8080

  # With environment variables
  COMPANY_LOOKUP_EXCEL_FILE=/data/companies.xlsx company-lookup-mcp --transport sse
        """,
    )

    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default=os.environ.get("MCP_TRANSPORT", "stdio"),
        help="Transport type (default: stdio, or MCP_TRANSPORT env var)",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("MCP_HOST", "0.0.0.0"),
        help="Host for SSE transport (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("MCP_PORT", "8080")),
        help="Port for SSE transport (default: 8080)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )

    # Verify Excel file is configured
    excel_file = os.environ.get("COMPANY_LOOKUP_EXCEL_FILE")
    if not excel_file:
        logger.warning(t("mcp.warning.excel_not_set"))

    # Create and run server
    mcp = create_mcp_server(host=args.host, port=args.port)

    logger.info(t("mcp.info.starting", transport=args.transport))
    if args.transport == "sse":
        logger.info(t("mcp.info.sse_endpoint", host=args.host, port=args.port))

    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()

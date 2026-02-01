"""Command-line interface for company lookup.

Supports bilingual operation (English/German) via:
- --language / -l option
- COMPANY_LOOKUP_LANGUAGE environment variable
- LANG environment variable
- Default: English
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from company_lookup.config.manager import ConfigManager
from company_lookup.core.excel_reader import ExcelReader
from company_lookup.core.lookup_engine import LookupEngine
from company_lookup.data.schemas import CompanyStatus, Config, LookupRequest
from company_lookup.i18n import get_translator, set_language, t
from company_lookup.output.exporter import ResultExporter
from company_lookup.output.formatter import ConsoleFormatter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

console = Console()
formatter = ConsoleFormatter(console)


def setup_language(language: Optional[str] = None) -> None:
    """Set up the language for the CLI.

    Args:
        language: Language code ('en' or 'de'). If None, uses environment variables.
    """
    if language:
        set_language(language)
    # Otherwise, the translator will use environment variables


def get_config(config_path: Optional[str]) -> Config:
    """Load configuration from file and environment."""
    manager = ConfigManager(config_path)
    return manager.load()


@click.group()
@click.version_option(version="0.1.0")
@click.option(
    "-l", "--language",
    type=click.Choice(["en", "de"]),
    envvar="COMPANY_LOOKUP_LANGUAGE",
    help="Language for output (en=English, de=German). Default: en.",
)
@click.pass_context
def cli(ctx: click.Context, language: Optional[str]):
    """Company Lookup - Whitelist/Blacklist lookup with fuzzy matching.

    A tool for checking company names against whitelist and blacklist
    databases with intelligent fuzzy matching support.

    Firmensuche - Whitelist/Blacklist-Suche mit Fuzzy-Matching.
    """
    ctx.ensure_object(dict)
    setup_language(language)
    ctx.obj["language"] = language or get_translator().get_language()


@cli.command()
@click.option(
    "-e", "--excel", "excel_file",
    required=True,
    type=click.Path(exists=True),
    help=t("cli.lookup.option.excel"),
)
@click.option(
    "-q", "--query", "company_name",
    required=True,
    help=t("cli.lookup.option.query"),
)
@click.option(
    "-t", "--threshold",
    type=float,
    default=80.0,
    help=t("cli.lookup.option.threshold"),
)
@click.option(
    "-n", "--max-results",
    type=int,
    default=5,
    help=t("cli.lookup.option.max_results"),
)
@click.option(
    "--include-partial/--no-partial",
    default=True,
    help=t("cli.lookup.option.partial"),
)
@click.option(
    "-o", "--output",
    type=click.Path(),
    help=t("cli.lookup.option.output"),
)
@click.option(
    "-f", "--format",
    type=click.Choice(["console", "json", "csv", "both"]),
    default="console",
    help=t("cli.lookup.option.format"),
)
@click.option(
    "-c", "--config",
    type=click.Path(exists=True),
    help=t("cli.lookup.option.config"),
)
@click.option(
    "-v", "--verbose",
    is_flag=True,
    help=t("cli.lookup.option.verbose"),
)
@click.pass_context
def lookup(
    ctx: click.Context,
    excel_file: str,
    company_name: str,
    threshold: float,
    max_results: int,
    include_partial: bool,
    output: Optional[str],
    format: str,
    config: Optional[str],
    verbose: bool,
):
    """Look up a company name in the whitelist/blacklist.

    Example:
        company-lookup lookup -e companies.xlsx -q "Siemens"
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Load configuration
        cfg = get_config(config)
        cfg.excel_file_path = excel_file

        # Initialize engine
        engine = LookupEngine(config=cfg)
        engine.initialize(excel_file)

        # Perform lookup
        request = LookupRequest(
            company_name=company_name,
            fuzzy_threshold=threshold,
            max_results=max_results,
            include_partial_matches=include_partial,
        )
        result = engine.lookup(request)

        # Output results
        if format in ("console", "both"):
            formatter.print_lookup_result(result)

        if format in ("json", "csv", "both"):
            exporter = ResultExporter(cfg.output_directory)
            export_format = "json" if format == "both" else format
            filepath = exporter.export_result(result, export_format, output)
            formatter.print_success(t("cli.success.exported", path=filepath))

    except FileNotFoundError as e:
        formatter.print_error(t("cli.error.file_not_found", error=str(e)))
        sys.exit(1)
    except ValueError as e:
        formatter.print_error(t("cli.error.invalid_input", error=str(e)))
        sys.exit(1)
    except Exception as e:
        formatter.print_error(t("cli.error.generic", error=str(e)))
        if verbose:
            logger.exception("Detailed error:")
        sys.exit(1)


@cli.command()
@click.option(
    "-e", "--excel", "excel_file",
    required=True,
    type=click.Path(exists=True),
    help=t("cli.lookup.option.excel"),
)
@click.option(
    "-s", "--status",
    type=click.Choice(["all", "whitelist", "blacklist"]),
    default="all",
    help=t("cli.list.option.status"),
)
@click.option(
    "-o", "--output",
    type=click.Path(),
    help=t("cli.lookup.option.output"),
)
@click.option(
    "-f", "--format",
    type=click.Choice(["console", "json", "csv"]),
    default="console",
    help=t("cli.lookup.option.format"),
)
@click.option(
    "-c", "--config",
    type=click.Path(exists=True),
    help=t("cli.lookup.option.config"),
)
@click.pass_context
def list_companies(
    ctx: click.Context,
    excel_file: str,
    status: str,
    output: Optional[str],
    format: str,
    config: Optional[str],
):
    """List all companies in the database.

    Example:
        company-lookup list -e companies.xlsx --status whitelist
    """
    try:
        cfg = get_config(config)
        engine = LookupEngine(config=cfg)
        engine.initialize(excel_file)

        # Get companies with optional filter
        status_filter = None
        if status == "whitelist":
            status_filter = CompanyStatus.WHITELISTED
        elif status == "blacklist":
            status_filter = CompanyStatus.BLACKLISTED

        companies = engine.get_all_companies(status_filter)

        if format == "console":
            status_label = t(f"status.{status}")
            title = t("fmt.companies_title", filter=status_label)
            formatter.print_company_list(companies, title=title)
        else:
            exporter = ResultExporter(cfg.output_directory)
            filepath = exporter.export_company_list(companies, format, output)
            formatter.print_success(t("cli.success.companies_exported", path=filepath))

    except Exception as e:
        formatter.print_error(t("cli.error.generic", error=str(e)))
        sys.exit(1)


@cli.command()
@click.option(
    "-e", "--excel", "excel_file",
    required=True,
    type=click.Path(exists=True),
    help=t("cli.lookup.option.excel"),
)
@click.option(
    "-c", "--config",
    type=click.Path(exists=True),
    help=t("cli.lookup.option.config"),
)
@click.pass_context
def stats(ctx: click.Context, excel_file: str, config: Optional[str]):
    """Show statistics about the company lists.

    Example:
        company-lookup stats -e companies.xlsx
    """
    try:
        cfg = get_config(config)
        engine = LookupEngine(config=cfg)
        engine.initialize(excel_file)

        stats_data = engine.get_stats()
        formatter.print_stats(stats_data)

    except Exception as e:
        formatter.print_error(t("cli.error.generic", error=str(e)))
        sys.exit(1)


@cli.command()
@click.option(
    "-o", "--output",
    type=click.Path(),
    default="company_template.xlsx",
    help=t("cli.template.option.output"),
)
@click.pass_context
def create_template(ctx: click.Context, output: str):
    """Create a template Excel file with the expected structure.

    Example:
        company-lookup create-template -o my_companies.xlsx
    """
    try:
        ExcelReader.create_template(output)
        formatter.print_success(t("cli.template.success", path=output))
        formatter.print_info(t("cli.template.info"))

    except Exception as e:
        formatter.print_error(t("cli.error.generic", error=str(e)))
        sys.exit(1)


@cli.command()
@click.option(
    "-e", "--excel", "excel_file",
    required=True,
    type=click.Path(exists=True),
    help=t("cli.lookup.option.excel"),
)
@click.option(
    "-i", "--input", "input_file",
    required=True,
    type=click.Path(exists=True),
    help=t("cli.batch.option.input"),
)
@click.option(
    "-t", "--threshold",
    type=float,
    default=80.0,
    help=t("cli.lookup.option.threshold"),
)
@click.option(
    "-o", "--output",
    type=click.Path(),
    help=t("cli.lookup.option.output"),
)
@click.option(
    "-f", "--format",
    type=click.Choice(["json", "csv"]),
    default="json",
    help=t("cli.lookup.option.format"),
)
@click.option(
    "-c", "--config",
    type=click.Path(exists=True),
    help=t("cli.lookup.option.config"),
)
@click.option(
    "-v", "--verbose",
    is_flag=True,
    help=t("cli.lookup.option.verbose"),
)
@click.pass_context
def batch(
    ctx: click.Context,
    excel_file: str,
    input_file: str,
    threshold: float,
    output: Optional[str],
    format: str,
    config: Optional[str],
    verbose: bool,
):
    """Perform batch lookup from a file with company names.

    Example:
        company-lookup batch -e companies.xlsx -i queries.txt -f csv
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        cfg = get_config(config)
        engine = LookupEngine(config=cfg)
        engine.initialize(excel_file)

        # Read company names from file
        with open(input_file, "r", encoding="utf-8") as f:
            company_names = [line.strip() for line in f if line.strip()]

        formatter.print_info(t("cli.batch.info.processing", count=len(company_names)))

        # Perform lookups
        results = []
        for name in company_names:
            request = LookupRequest(
                company_name=name,
                fuzzy_threshold=threshold,
                max_results=3,
                include_partial_matches=False,
            )
            result = engine.lookup(request)
            results.append(result)

            if verbose:
                status_str = result.status.value
                confidence = f"{result.confidence:.0%}"
                console.print(f"  {name} -> {status_str} ({confidence})")

        # Export results
        exporter = ResultExporter(cfg.output_directory)
        filepath = exporter.export_batch_results(results, format, output)

        # Print summary
        whitelisted = sum(1 for r in results if r.is_approved)
        blacklisted = sum(1 for r in results if r.is_blocked)
        unknown = len(results) - whitelisted - blacklisted

        console.print()
        formatter.print_success(t("cli.batch.success.processed", count=len(results)))
        console.print(f"  [green]{t('status.whitelisted')}:[/green] {whitelisted}")
        console.print(f"  [red]{t('status.blacklisted')}:[/red] {blacklisted}")
        console.print(f"  [yellow]{t('status.unknown')}:[/yellow] {unknown}")
        formatter.print_success(t("cli.success.exported", path=filepath))

    except Exception as e:
        formatter.print_error(t("cli.error.generic", error=str(e)))
        if verbose:
            logger.exception("Detailed error:")
        sys.exit(1)


@cli.command()
@click.option(
    "-e", "--excel", "excel_file",
    type=click.Path(exists=True),
    help=t("cli.lookup.option.excel"),
)
@click.option(
    "-h", "--host",
    default="0.0.0.0",
    help=t("cli.serve.option.host"),
)
@click.option(
    "-p", "--port",
    type=int,
    default=8000,
    help=t("cli.serve.option.port"),
)
@click.option(
    "-c", "--config",
    type=click.Path(exists=True),
    help=t("cli.lookup.option.config"),
)
@click.pass_context
def serve(
    ctx: click.Context,
    excel_file: Optional[str],
    host: str,
    port: int,
    config: Optional[str],
):
    """Start the REST API server.

    Example:
        company-lookup serve -e companies.xlsx -p 8000
    """
    try:
        import uvicorn

        # Set environment variables for the API
        if excel_file:
            os.environ["COMPANY_LOOKUP_EXCEL_FILE"] = excel_file
        os.environ["COMPANY_LOOKUP_API_HOST"] = host
        os.environ["COMPANY_LOOKUP_API_PORT"] = str(port)

        formatter.print_info(t("cli.serve.info.starting", host=host, port=port))
        if excel_file:
            formatter.print_info(t("cli.serve.info.excel", file=excel_file))

        uvicorn.run(
            "company_lookup.api:app",
            host=host,
            port=port,
            reload=False,
        )

    except ImportError:
        formatter.print_error(t("cli.serve.error.uvicorn"))
        sys.exit(1)
    except Exception as e:
        formatter.print_error(t("cli.error.generic", error=str(e)))
        sys.exit(1)


if __name__ == "__main__":
    cli()

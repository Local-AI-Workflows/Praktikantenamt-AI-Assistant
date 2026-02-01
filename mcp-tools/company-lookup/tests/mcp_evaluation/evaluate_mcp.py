#!/usr/bin/env python3
"""
MCP Company Lookup Evaluation Script.

This script evaluates how well LLMs can interpret natural language requests
and correctly invoke the company lookup MCP tool to determine if a company
is approved (whitelisted), blocked (blacklisted), or unknown.

Supports:
- Local LLMs via Ollama
- OpenAI-compatible APIs (LM Studio, vLLM, OpenRouter)
- Anthropic Claude models

Usage:
    # Test with local Ollama models
    python evaluate_mcp.py -m llama3.2:3b qwen2.5:7b -e companies.xlsx

    # Test with Anthropic
    python evaluate_mcp.py --anthropic-model claude-3-haiku-20240307 -e companies.xlsx

    # Use default test data
    python evaluate_mcp.py -m llama3.2:3b
"""

import argparse
import json
import os
import re
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import httpx
from openpyxl import Workbook
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table

# Add parent path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from company_lookup.core.lookup_engine import LookupEngine
from company_lookup.data.schemas import CompanyStatus, Config, LookupRequest

console = Console()


@dataclass
class LLMConfig:
    """Configuration for an LLM endpoint."""

    name: str
    endpoint: str
    model: str
    api_type: str = "ollama"  # "ollama", "openai", "anthropic"
    api_key: Optional[str] = None
    timeout: int = 120
    temperature: float = 0.0


@dataclass
class TestResult:
    """Result of a single test case."""

    prompt_id: str
    prompt: str
    llm_name: str
    model: str
    success: bool
    tool_called: bool
    tool_name_correct: bool
    parameters_extracted: dict
    expected: dict
    company_name_correct: bool
    status_correct: bool
    response_time: float
    raw_response: str
    error: Optional[str] = None


@dataclass
class EvaluationReport:
    """Overall evaluation report."""

    llm_name: str
    model: str
    total_tests: int
    successful_tool_calls: int
    correct_tool_name: int
    correct_company_extraction: int
    correct_status_prediction: int
    average_response_time: float
    results: list = field(default_factory=list)


# System prompt explaining the company lookup MCP tools
SYSTEM_PROMPT = """You are an assistant with access to company lookup tools for a German university internship office (Praktikantenamt). When the user asks about checking a company, verifying if a company is approved, or looking up company status, you MUST use the appropriate tool.

Available tools:

1. lookup_company: Full lookup with fuzzy matching
   Parameters:
     - company_name (required): The name of the company to look up
     - threshold (optional): Minimum similarity score 0-100 (default: 80)
     - max_results (optional): Maximum results to return (default: 5)
   Use this for general company lookups when you need full details.

2. check_company_approved: Quick approval check
   Parameters:
     - company_name (required): The name of the company to check
     - threshold (optional): Minimum similarity score (default: 80)
   Use this when the user specifically asks if a company is APPROVED/WHITELISTED.

3. check_company_blocked: Quick block check
   Parameters:
     - company_name (required): The name of the company to check
     - threshold (optional): Minimum similarity score (default: 80)
   Use this when the user specifically asks if a company is BLOCKED/BLACKLISTED.

4. batch_lookup: Look up multiple companies
   Parameters:
     - company_names (required): List of company names
     - threshold (optional): Minimum similarity score (default: 80)
   Use this when checking multiple companies at once.

5. list_companies: List companies in database
   Parameters:
     - status (optional): Filter - "all", "whitelist", or "blacklist"
   Use this when user asks to see all companies.

6. get_company_stats: Get database statistics
   Parameters: none
   Use this when user asks how many companies are in the database.

IMPORTANT: Always respond with ONLY a JSON object in this exact format:
```json
{
  "tool": "lookup_company",
  "parameters": {
    "company_name": "Company Name Here",
    "threshold": 80
  }
}
```

Guidelines:
- Extract the company name EXACTLY as mentioned, preserving case and suffixes (AG, GmbH, SE, etc.)
- If a company name has typos, still extract it as stated - the fuzzy matching will handle it
- Use lookup_company for general queries about a company
- Use check_company_approved when user asks "is X approved?" or "can I do an internship at X?"
- Use check_company_blocked when user asks "is X blocked?" or "is X on the blacklist?"
- Use batch_lookup when multiple companies are mentioned
- Use list_companies when user wants to see all or filtered companies
- Use get_company_stats when user asks about database size/counts
- For German queries, the same tools apply
- If threshold is not mentioned, omit it (use default)
"""


def load_test_prompts(path: Path) -> dict:
    """Load test prompts from JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def call_ollama(config: LLMConfig, prompt: str) -> tuple[str, float]:
    """Call Ollama API and return response and timing."""
    start_time = time.time()

    payload = {
        "model": config.model,
        "prompt": prompt,
        "system": SYSTEM_PROMPT,
        "stream": False,
        "options": {
            "temperature": config.temperature,
        },
    }

    with httpx.Client(timeout=config.timeout) as client:
        response = client.post(
            f"{config.endpoint}/api/generate",
            json=payload,
        )
        response.raise_for_status()

    elapsed = time.time() - start_time
    result = response.json()
    return result.get("response", ""), elapsed


def call_openai_compatible(config: LLMConfig, prompt: str) -> tuple[str, float]:
    """Call OpenAI-compatible API (works with LM Studio, vLLM, OpenRouter, etc.)."""
    start_time = time.time()

    headers = {"Content-Type": "application/json"}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"

    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": config.temperature,
    }

    with httpx.Client(timeout=config.timeout) as client:
        response = client.post(
            f"{config.endpoint}/v1/chat/completions",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()

    elapsed = time.time() - start_time
    result = response.json()
    return result["choices"][0]["message"]["content"], elapsed


def call_anthropic(config: LLMConfig, prompt: str) -> tuple[str, float]:
    """Call Anthropic API."""
    start_time = time.time()

    headers = {
        "Content-Type": "application/json",
        "x-api-key": config.api_key,
        "anthropic-version": "2023-06-01",
    }

    payload = {
        "model": config.model,
        "max_tokens": 1024,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": config.temperature,
    }

    with httpx.Client(timeout=config.timeout) as client:
        response = client.post(
            "https://api.anthropic.com/v1/messages",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()

    elapsed = time.time() - start_time
    result = response.json()
    return result["content"][0]["text"], elapsed


def call_llm(config: LLMConfig, prompt: str) -> tuple[str, float]:
    """Call LLM based on API type."""
    if config.api_type == "ollama":
        return call_ollama(config, prompt)
    elif config.api_type == "openai":
        return call_openai_compatible(config, prompt)
    elif config.api_type == "anthropic":
        return call_anthropic(config, prompt)
    else:
        raise ValueError(f"Unknown API type: {config.api_type}")


def extract_tool_call(response: str) -> Optional[dict]:
    """Extract tool call JSON from LLM response."""
    # Look for JSON block in various formats
    json_patterns = [
        r"```json\s*(.*?)\s*```",
        r"```\s*(\{.*?\})\s*```",
        r'(\{[^{}]*"tool"[^{}]*"parameters"[^{}]*\{[^{}]*\}[^{}]*\})',
        r'(\{[^{}]*"parameters"[^{}]*\{[^{}]*\}[^{}]*\})',
    ]

    for pattern in json_patterns:
        matches = re.findall(pattern, response, re.DOTALL)
        for match in matches:
            try:
                if isinstance(match, str):
                    json_str = match.strip()
                    if not json_str.startswith("{"):
                        continue
                    parsed = json.loads(json_str)
                    if "tool" in parsed or "parameters" in parsed:
                        return parsed
            except json.JSONDecodeError:
                continue

    # Try to find nested JSON with parameters object
    nested_pattern = r'\{\s*"tool"\s*:\s*"[^"]+"\s*,\s*"parameters"\s*:\s*\{[^}]+\}\s*\}'
    matches = re.findall(nested_pattern, response, re.DOTALL)
    for match in matches:
        try:
            parsed = json.loads(match)
            return parsed
        except json.JSONDecodeError:
            continue

    # Try tools without parameters (like get_company_stats)
    no_params_pattern = r'\{\s*"tool"\s*:\s*"([^"]+)"\s*\}'
    match = re.search(no_params_pattern, response)
    if match:
        return {"tool": match.group(1), "parameters": {}}

    # Try to extract just the parameters if tool wrapper is missing
    params_pattern = r'"parameters"\s*:\s*(\{[^}]+\})'
    params_match = re.search(params_pattern, response)
    if params_match:
        try:
            params = json.loads(params_match.group(1))
            if "company_name" in params or "company_names" in params:
                return {"tool": "lookup_company", "parameters": params}
        except json.JSONDecodeError:
            pass

    # Try parsing the entire response as JSON
    try:
        parsed = json.loads(response.strip())
        if "tool" in parsed or "parameters" in parsed:
            return parsed
    except json.JSONDecodeError:
        pass

    # Last resort: look for company_name value
    company_pattern = r'"company_name"\s*:\s*"([^"]+)"'
    company_match = re.search(company_pattern, response)
    tool_pattern = r'"tool"\s*:\s*"([^"]+)"'
    tool_match = re.search(tool_pattern, response)

    if company_match:
        params = {"company_name": company_match.group(1)}
        tool_name = tool_match.group(1) if tool_match else "lookup_company"
        return {"tool": tool_name, "parameters": params}

    # Check for company_names (batch)
    batch_pattern = r'"company_names"\s*:\s*\[([^\]]+)\]'
    batch_match = re.search(batch_pattern, response)
    if batch_match:
        try:
            names_str = "[" + batch_match.group(1) + "]"
            names = json.loads(names_str)
            return {"tool": "batch_lookup", "parameters": {"company_names": names}}
        except json.JSONDecodeError:
            pass

    return None


def normalize_company_name(name: str) -> str:
    """Normalize company name for comparison."""
    if not name:
        return ""
    # Lowercase and remove extra whitespace
    normalized = " ".join(name.lower().split())
    # Remove common suffixes for comparison
    suffixes = [" ag", " gmbh", " se", " kg", " co", " ltd", " inc", " corp", " group"]
    for suffix in suffixes:
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)].strip()
    return normalized


def verify_result(
    extracted: dict,
    expected: dict,
    engine: LookupEngine,
) -> tuple[bool, bool, bool, Optional[str]]:
    """
    Verify extracted parameters against expected values.

    Returns: (tool_correct, company_correct, status_correct, actual_status)
    """
    params = extracted.get("parameters", extracted)
    tool_name = extracted.get("tool", "")

    # Check if tool name is correct (or acceptable alternative)
    expected_tool = expected.get("expected_tool", "lookup_company")
    acceptable_tools = expected.get("acceptable_tools", [expected_tool])

    # Add common alternatives
    if expected_tool == "lookup_company":
        acceptable_tools = ["lookup_company", "check_company_approved", "check_company_blocked"]
    elif expected_tool == "check_company_approved":
        acceptable_tools = ["check_company_approved", "lookup_company"]
    elif expected_tool == "check_company_blocked":
        acceptable_tools = ["check_company_blocked", "lookup_company"]

    tool_correct = tool_name in acceptable_tools

    # Check company name extraction
    extracted_company = params.get("company_name", "")
    expected_result = expected.get("expected_result", {})

    # For batch lookup, check company_names
    if tool_name == "batch_lookup" or expected_tool == "batch_lookup":
        extracted_names = params.get("company_names", [])
        return tool_name == "batch_lookup", len(extracted_names) > 0, True, None

    # For stats/list tools, just check tool was called correctly
    if expected_tool in ("get_company_stats", "list_companies"):
        return tool_correct, True, True, None

    # Get expected company name from test case
    expected_company = expected.get("company_name", "")

    # If no explicit company_name in expected, try to extract from prompt
    if not expected_company:
        prompt = expected.get("prompt", "")
        expected_company = extract_company_from_prompt(prompt)

    # Fuzzy comparison for company name
    extracted_norm = normalize_company_name(extracted_company)
    expected_norm = normalize_company_name(expected_company)
    company_correct = (
        extracted_norm == expected_norm
        or extracted_company.lower() == expected_company.lower()
    )

    # If not exact, check for close match
    if not company_correct and extracted_company and expected_company:
        try:
            from rapidfuzz import fuzz

            similarity = fuzz.ratio(extracted_norm, expected_norm)
            company_correct = similarity >= 80
        except ImportError:
            pass

    # Verify actual status by running lookup
    actual_status = None
    status_correct = False

    if extracted_company:
        try:
            request = LookupRequest(
                company_name=extracted_company,
                fuzzy_threshold=float(params.get("threshold", 75)),
                max_results=5,
            )
            result = engine.lookup(request)
            actual_status = result.status.value

            expected_status = expected_result.get("status")
            if expected_status:
                status_correct = actual_status == expected_status
            else:
                # Check is_approved/is_blocked
                if expected_result.get("is_approved"):
                    status_correct = result.is_approved
                elif expected_result.get("is_blocked"):
                    status_correct = result.is_blocked
                else:
                    # Unknown expected
                    status_correct = actual_status == "unknown"
        except Exception as e:
            console.print(f"[yellow]Lookup error: {e}[/yellow]")

    return tool_correct, company_correct, status_correct, actual_status


def extract_company_from_prompt(prompt: str) -> str:
    """Extract company name from prompt for validation."""
    # Try quoted names first
    quoted = re.search(r"['\"]([^'\"]+)['\"]", prompt)
    if quoted:
        return quoted.group(1)

    # Try company patterns
    patterns = [
        r"(?:at|is|check|approved|blocked)\s+([A-Z][a-zA-Z\s&]+?(?:AG|GmbH|SE|Ltd|Inc|Group))",
        r"([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*(?:\s+(?:AG|GmbH|SE|Ltd|Inc|Group))?)",
    ]

    for pattern in patterns:
        match = re.search(pattern, prompt)
        if match:
            name = match.group(1).strip()
            # Filter out common words
            if name.lower() not in ("is", "can", "check", "the", "random", "my"):
                return name

    return ""


def create_test_engine(test_data_path: Optional[Path] = None) -> tuple[LookupEngine, str]:
    """Create a lookup engine with test data.

    Returns:
        Tuple of (engine, excel_path)
    """
    # Create test Excel file
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        workbook = Workbook()

        # Whitelist sheet
        ws_whitelist = workbook.active
        ws_whitelist.title = "Whitelist"
        ws_whitelist.append(["Company Name", "Category", "Notes"])
        whitelist_companies = [
            ("Siemens AG", "Technology", "Major German corporation"),
            ("BMW Group", "Automotive", "Car manufacturer"),
            ("SAP SE", "Software", "Enterprise software"),
            ("Volkswagen AG", "Automotive", "Auto manufacturer"),
            ("Bosch GmbH", "Technology", "Engineering company"),
            ("Deutsche Bank AG", "Finance", "Investment banking"),
            ("Deutsche Telekom AG", "Telecom", "Telecom provider"),
            ("E.ON SE", "Energy", "Energy company"),
            ("Allianz SE", "Insurance", "Insurance"),
            ("BASF SE", "Chemical", "Chemicals"),
            ("Mercedes-Benz Group AG", "Automotive", "Luxury cars"),
            ("Porsche AG", "Automotive", "Sports cars"),
            ("Airbus SE", "Aerospace", "Aircraft manufacturer"),
            ("ThyssenKrupp AG", "Industrial", "Steel and engineering"),
            ("Bayer AG", "Pharma", "Pharmaceuticals"),
        ]
        for company in whitelist_companies:
            ws_whitelist.append(company)

        # Blacklist sheet
        ws_blacklist = workbook.create_sheet("Blacklist")
        ws_blacklist.append(["Company Name", "Category", "Notes"])
        blacklist_companies = [
            ("Fake Company GmbH", "Unknown", "Known scam"),
            ("Scam Industries Ltd", "Unknown", "Fraudulent"),
            ("Betrug & Partner KG", "Unknown", "Deceptive"),
            ("Phantomfirma SE", "Unknown", "Shell company"),
            ("Dubious Consulting AG", "Unknown", "Suspicious activities"),
        ]
        for company in blacklist_companies:
            ws_blacklist.append(company)

        workbook.save(tmp.name)
        excel_path = tmp.name

    config = Config(excel_file_path=excel_path)
    engine = LookupEngine(config=config)
    engine.initialize(excel_path)

    return engine, excel_path


def run_evaluation(
    configs: list[LLMConfig],
    test_data: dict,
    output_dir: Path,
    engine: Optional[LookupEngine] = None,
) -> list[EvaluationReport]:
    """Run evaluation across all LLM configs and test cases."""
    if engine is None:
        engine, _ = create_test_engine()

    reports = []

    for config in configs:
        console.print(
            Panel(
                f"[bold blue]Evaluating: {config.name}[/bold blue]\n"
                f"Model: {config.model}\n"
                f"Endpoint: {config.endpoint}",
                title="LLM Configuration",
            )
        )

        results = []
        test_cases = test_data["test_cases"]

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(f"Testing {config.name}...", total=len(test_cases))

            for test_case in test_cases:
                prompt_id = test_case["id"]
                prompt = test_case["prompt"]
                expected = test_case

                try:
                    response, elapsed = call_llm(config, prompt)
                    extracted = extract_tool_call(response)

                    tool_called = extracted is not None

                    if tool_called and extracted:
                        tool_ok, company_ok, status_ok, actual_status = verify_result(
                            extracted, expected, engine
                        )
                    else:
                        tool_ok, company_ok, status_ok, actual_status = (
                            False,
                            False,
                            False,
                            None,
                        )

                    result = TestResult(
                        prompt_id=prompt_id,
                        prompt=prompt,
                        llm_name=config.name,
                        model=config.model,
                        success=tool_called and tool_ok and company_ok,
                        tool_called=tool_called,
                        tool_name_correct=tool_ok,
                        parameters_extracted=extracted or {},
                        expected=expected,
                        company_name_correct=company_ok,
                        status_correct=status_ok,
                        response_time=elapsed,
                        raw_response=response[:500],
                    )

                except Exception as e:
                    result = TestResult(
                        prompt_id=prompt_id,
                        prompt=prompt,
                        llm_name=config.name,
                        model=config.model,
                        success=False,
                        tool_called=False,
                        tool_name_correct=False,
                        parameters_extracted={},
                        expected=expected,
                        company_name_correct=False,
                        status_correct=False,
                        response_time=0,
                        raw_response="",
                        error=str(e),
                    )

                results.append(result)
                progress.advance(task)

                # Small delay to avoid rate limiting
                time.sleep(0.5)

        # Calculate metrics
        total = len(results)
        tool_calls = sum(1 for r in results if r.tool_called)
        correct_tool = sum(1 for r in results if r.tool_name_correct)
        correct_company = sum(1 for r in results if r.company_name_correct)
        correct_status = sum(1 for r in results if r.status_correct)
        avg_time = sum(r.response_time for r in results) / total if total > 0 else 0

        report = EvaluationReport(
            llm_name=config.name,
            model=config.model,
            total_tests=total,
            successful_tool_calls=tool_calls,
            correct_tool_name=correct_tool,
            correct_company_extraction=correct_company,
            correct_status_prediction=correct_status,
            average_response_time=avg_time,
            results=results,
        )
        reports.append(report)

        # Display summary
        display_report_summary(report)

    # Save results
    save_results(reports, output_dir)

    return reports


def display_report_summary(report: EvaluationReport):
    """Display a summary table for an evaluation report."""
    table = Table(title=f"Results: {report.llm_name}", box=box.ROUNDED)

    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_column("Percentage", style="yellow")

    total = report.total_tests

    table.add_row("Total Tests", str(total), "100%")
    table.add_row(
        "Tool Called",
        str(report.successful_tool_calls),
        f"{report.successful_tool_calls/total*100:.1f}%",
    )
    table.add_row(
        "Correct Tool Name",
        str(report.correct_tool_name),
        f"{report.correct_tool_name/total*100:.1f}%",
    )
    table.add_row(
        "Company Name Correct",
        str(report.correct_company_extraction),
        f"{report.correct_company_extraction/total*100:.1f}%",
    )
    table.add_row(
        "Status Prediction Correct",
        str(report.correct_status_prediction),
        f"{report.correct_status_prediction/total*100:.1f}%",
    )
    table.add_row("Avg Response Time", f"{report.average_response_time:.2f}s", "-")

    console.print(table)
    console.print()

    # Show failures
    failures = [r for r in report.results if not r.success]
    if failures:
        console.print(f"[yellow]Failed cases ({len(failures)}):[/yellow]")
        for f in failures[:5]:  # Show first 5 failures
            console.print(f"  - {f.prompt_id}: {f.prompt[:60]}...")
            if f.error:
                console.print(f"    [red]Error: {f.error}[/red]")
            elif not f.tool_called:
                console.print("    [red]Tool not called[/red]")
            else:
                console.print(
                    f"    [red]Tool: {f.tool_name_correct}, "
                    f"Company: {f.company_name_correct}[/red]"
                )
        console.print()


def save_results(reports: list[EvaluationReport], output_dir: Path):
    """Save evaluation results to JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for report in reports:
        safe_name = report.llm_name.replace("/", "_").replace(" ", "_").replace(":", "-")
        output_file = output_dir / f"eval_{safe_name}_{timestamp}.json"

        # Convert to dict
        report_dict = {
            "llm_name": report.llm_name,
            "model": report.model,
            "timestamp": timestamp,
            "metrics": {
                "total_tests": report.total_tests,
                "successful_tool_calls": report.successful_tool_calls,
                "correct_tool_name": report.correct_tool_name,
                "correct_company_extraction": report.correct_company_extraction,
                "correct_status_prediction": report.correct_status_prediction,
                "average_response_time": report.average_response_time,
                "tool_call_rate": report.successful_tool_calls / report.total_tests,
                "company_accuracy": report.correct_company_extraction / report.total_tests,
                "status_accuracy": report.correct_status_prediction / report.total_tests,
            },
            "results": [
                {
                    "prompt_id": r.prompt_id,
                    "prompt": r.prompt,
                    "success": r.success,
                    "tool_called": r.tool_called,
                    "tool_name_correct": r.tool_name_correct,
                    "parameters_extracted": r.parameters_extracted,
                    "expected": {
                        "expected_tool": r.expected.get("expected_tool"),
                        "expected_result": r.expected.get("expected_result"),
                    },
                    "company_name_correct": r.company_name_correct,
                    "status_correct": r.status_correct,
                    "response_time": r.response_time,
                    "error": r.error,
                }
                for r in report.results
            ],
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)

        console.print(f"[green]Results saved to: {output_file}[/green]")


def display_comparison_table(reports: list[EvaluationReport]):
    """Display a comparison table across all LLMs."""
    if len(reports) < 2:
        return

    table = Table(title="LLM Comparison", box=box.DOUBLE_EDGE)

    table.add_column("LLM", style="cyan")
    table.add_column("Model", style="dim")
    table.add_column("Tool Call %", justify="right")
    table.add_column("Company Acc %", justify="right")
    table.add_column("Status Acc %", justify="right")
    table.add_column("Avg Time", justify="right")

    for report in reports:
        total = report.total_tests
        table.add_row(
            report.llm_name,
            report.model[:20],
            f"{report.successful_tool_calls/total*100:.1f}%",
            f"{report.correct_company_extraction/total*100:.1f}%",
            f"{report.correct_status_prediction/total*100:.1f}%",
            f"{report.average_response_time:.2f}s",
        )

    console.print()
    console.print(table)


# Default LLM configurations
DEFAULT_CONFIGS = [
    LLMConfig(
        name="Ollama-Llama3.2-3B",
        endpoint="http://localhost:11434",
        model="llama3.2:3b",
        api_type="ollama",
    ),
    LLMConfig(
        name="Ollama-Qwen2.5-7B",
        endpoint="http://localhost:11434",
        model="qwen2.5:7b",
        api_type="ollama",
    ),
]


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Evaluate MCP Company Lookup with different LLMs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with local Ollama models
  python evaluate_mcp.py -m llama3.2:3b qwen2.5:7b

  # Test with custom Excel file
  python evaluate_mcp.py -m llama3.2:3b -e companies.xlsx

  # Test with Anthropic Claude
  python evaluate_mcp.py --anthropic-model claude-3-haiku-20240307

  # Test with OpenAI-compatible API (OpenRouter, LM Studio)
  python evaluate_mcp.py --openai-endpoint https://openrouter.ai/api --openai-model gpt-4

  # Custom config file
  python evaluate_mcp.py -c llm_configs.json
        """,
    )
    parser.add_argument(
        "-t",
        "--test-file",
        type=Path,
        default=Path(__file__).parent / "test_prompts.json",
        help="Path to test prompts JSON file",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path(__file__).parent / "results",
        help="Output directory for results",
    )
    parser.add_argument(
        "-c", "--config", type=Path, help="Path to LLM config JSON file"
    )
    parser.add_argument(
        "--endpoint",
        type=str,
        default="http://localhost:11434",
        help="Ollama endpoint URL",
    )
    parser.add_argument(
        "-m", "--models", nargs="+", help="List of Ollama models to test"
    )
    parser.add_argument(
        "--openai-endpoint", type=str, help="OpenAI-compatible endpoint URL"
    )
    parser.add_argument(
        "--openai-model", type=str, help="OpenAI-compatible model name"
    )
    parser.add_argument(
        "--openai-api-key", type=str, help="OpenAI API key (or use OPENAI_API_KEY env)"
    )
    parser.add_argument(
        "--anthropic-model",
        type=str,
        help="Anthropic model name (requires ANTHROPIC_API_KEY env var)",
    )
    parser.add_argument(
        "-e",
        "--excel-file",
        type=Path,
        help="Path to company Excel file (uses test data if not specified)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()

    # Load test prompts
    console.print(f"[blue]Loading test prompts from: {args.test_file}[/blue]")
    test_data = load_test_prompts(args.test_file)
    console.print(f"[green]Loaded {len(test_data['test_cases'])} test cases[/green]")

    # Create lookup engine
    engine = None
    if args.excel_file:
        config = Config(excel_file_path=str(args.excel_file))
        engine = LookupEngine(config=config)
        engine.initialize(str(args.excel_file))
        console.print(f"[blue]Using Excel file: {args.excel_file}[/blue]")
    else:
        engine, excel_path = create_test_engine()
        console.print("[blue]Using built-in test data[/blue]")

    stats = engine.get_stats()
    console.print(
        f"[green]Loaded {stats.total_companies} companies "
        f"({stats.whitelisted_count} whitelist, {stats.blacklisted_count} blacklist)[/green]"
    )

    # Build LLM configs
    configs = []

    if args.config:
        # Load from config file
        with open(args.config, "r") as f:
            config_data = json.load(f)
        for cfg in config_data.get("llms", []):
            configs.append(LLMConfig(**cfg))
    elif args.models:
        # Use specified models with Ollama
        for model in args.models:
            configs.append(
                LLMConfig(
                    name=f"Ollama-{model}",
                    endpoint=args.endpoint,
                    model=model,
                    api_type="ollama",
                )
            )
    else:
        # Use default configs
        configs = DEFAULT_CONFIGS

    # Add OpenAI-compatible endpoint if specified
    if args.openai_endpoint and args.openai_model:
        api_key = args.openai_api_key or os.environ.get("OPENAI_API_KEY")
        configs.append(
            LLMConfig(
                name=f"OpenAI-{args.openai_model}",
                endpoint=args.openai_endpoint,
                model=args.openai_model,
                api_type="openai",
                api_key=api_key,
            )
        )

    # Add Anthropic if specified
    if args.anthropic_model:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            console.print("[red]ANTHROPIC_API_KEY not set[/red]")
        else:
            configs.append(
                LLMConfig(
                    name=f"Anthropic-{args.anthropic_model}",
                    endpoint="https://api.anthropic.com",
                    model=args.anthropic_model,
                    api_type="anthropic",
                    api_key=api_key,
                )
            )

    if not configs:
        console.print("[red]No LLM configurations specified[/red]")
        return 1

    console.print(f"[blue]Testing {len(configs)} LLM configuration(s)[/blue]")

    # Run evaluation
    reports = run_evaluation(configs, test_data, args.output_dir, engine)

    # Show comparison
    display_comparison_table(reports)

    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
MCP Workday Calculator Evaluation Script.

This script evaluates how well LLMs can interpret natural language requests
and correctly invoke the workday calculator MCP tool.
"""

import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel
from rich import box

# Add parent path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from workday_calculator.core.calculator import WorkdayCalculator
from workday_calculator.core.holiday_provider import HolidayProvider
from workday_calculator.core.location_resolver import LocationResolver
from workday_calculator.data.schemas import Bundesland, LocationInput, WorkdayRequest
from datetime import date


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
    parameters_extracted: dict
    expected: dict
    working_days_correct: bool
    bundesland_correct: bool
    dates_correct: bool
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
    correct_parameters: int
    correct_results: int
    average_response_time: float
    results: list = field(default_factory=list)


# System prompt that explains available MCP tools
SYSTEM_PROMPT = """You are an assistant with access to tools. When the user asks about working days, workdays, business days, or Arbeitstage in Germany, you MUST use the calculate_workdays tool.

Available tool:
- calculate_workdays: Calculate working days between two dates for a German location.
  Parameters:
    - start_date (required): Start date in format YYYY-MM-DD
    - end_date (required): End date in format YYYY-MM-DD
    - postal_code (optional): German postal code (PLZ, 5 digits)
    - bundesland (optional): Bundesland code (see list below)
    - include_saturdays (optional): Whether to count Saturdays as work days (default: False)

German Bundesland codes (USE EXACTLY THESE):
- BB = Brandenburg
- BE = Berlin
- BW = Baden-Wuerttemberg (Stuttgart)
- BY = Bayern/Bavaria (Munich/Muenchen)
- HB = Bremen (city-state)
- HE = Hessen (Frankfurt)
- HH = Hamburg (city-state)
- MV = Mecklenburg-Vorpommern (NOT "ME"!)
- NI = Niedersachsen (Hannover)
- NW = Nordrhein-Westfalen (Cologne, Dusseldorf)
- RP = Rheinland-Pfalz
- SH = Schleswig-Holstein
- SL = Saarland
- SN = Sachsen/Saxony (Dresden, Leipzig)
- ST = Sachsen-Anhalt (NOT "SA"! Magdeburg)
- TH = Thueringen/Thuringia

IMPORTANT: Always respond with ONLY a JSON object in this exact format:
```json
{
  "tool": "calculate_workdays",
  "parameters": {
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "bundesland": "XX"
  }
}
```

Rules:
- Always use YYYY-MM-DD format for dates (e.g., "2026-03-01")
- If dates are implicit (e.g., "March to August 2026"), use first and last day of those months
- For "6 months starting March 1st", calculate end date as August 31st
- Use the exact Bundesland codes from the list above
- Bremen (city) = HB, Berlin = BE, Hamburg = HH
- Sachsen-Anhalt = ST (not SA), Mecklenburg-Vorpommern = MV (not ME)
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
        }
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
    """Call OpenAI-compatible API (works with LM Studio, vLLM, etc.)."""
    start_time = time.time()

    headers = {"Content-Type": "application/json"}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"

    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
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
        "messages": [
            {"role": "user", "content": prompt}
        ],
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
    import re

    # Look for JSON block in various formats
    json_patterns = [
        r'```json\s*(.*?)\s*```',
        r'```\s*(\{.*?\})\s*```',
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

    # Try to extract just the parameters if tool wrapper is missing
    params_pattern = r'"parameters"\s*:\s*(\{[^}]+\})'
    params_match = re.search(params_pattern, response)
    if params_match:
        try:
            params = json.loads(params_match.group(1))
            if "start_date" in params and "end_date" in params:
                return {"tool": "calculate_workdays", "parameters": params}
        except json.JSONDecodeError:
            pass

    # Try parsing the entire response as JSON
    try:
        parsed = json.loads(response.strip())
        if "tool" in parsed or "parameters" in parsed:
            return parsed
    except json.JSONDecodeError:
        pass

    # Last resort: look for individual parameter values
    date_pattern = r'"(start_date|end_date)"\s*:\s*"(\d{4}-\d{2}-\d{2})"'
    bl_pattern = r'"bundesland"\s*:\s*"([A-Z]{2})"'
    plz_pattern = r'"postal_code"\s*:\s*"(\d{5})"'

    dates = dict(re.findall(date_pattern, response))
    bl_match = re.search(bl_pattern, response)
    plz_match = re.search(plz_pattern, response)

    if "start_date" in dates and "end_date" in dates and (bl_match or plz_match):
        params = {
            "start_date": dates["start_date"],
            "end_date": dates["end_date"],
        }
        if bl_match:
            params["bundesland"] = bl_match.group(1)
        if plz_match:
            params["postal_code"] = plz_match.group(1)
        return {"tool": "calculate_workdays", "parameters": params}

    return None


def verify_result(
    extracted: dict,
    expected: dict,
    calculator: WorkdayCalculator
) -> tuple[bool, bool, bool, Optional[int]]:
    """
    Verify extracted parameters against expected values.

    Returns: (dates_correct, bundesland_correct, working_days_correct, actual_working_days)
    """
    params = extracted.get("parameters", extracted)

    # Check dates
    dates_correct = (
        params.get("start_date") == expected["start_date"] and
        params.get("end_date") == expected["end_date"]
    )

    # Check bundesland (could be in bundesland or inferred from postal_code)
    extracted_bl = params.get("bundesland", "").upper()
    extracted_plz = params.get("postal_code")
    expected_bl = expected["bundesland"]

    bundesland_correct = False
    if extracted_bl == expected_bl:
        bundesland_correct = True
    elif extracted_plz:
        # Resolve PLZ to bundesland
        try:
            location_resolver = LocationResolver(geocoding_enabled=False)
            location = LocationInput(postal_code=extracted_plz)
            resolved = location_resolver.resolve(location)
            bundesland_correct = resolved.bundesland.value == expected_bl
        except Exception:
            pass

    # Calculate actual working days if parameters are valid
    actual_working_days = None
    working_days_correct = False

    if dates_correct and (extracted_bl or extracted_plz):
        try:
            start = date.fromisoformat(params["start_date"])
            end = date.fromisoformat(params["end_date"])

            bl_enum = None
            if extracted_bl:
                bl_enum = Bundesland(extracted_bl)

            location = LocationInput(
                postal_code=extracted_plz,
                bundesland=bl_enum,
            )

            request = WorkdayRequest(
                start_date=start,
                end_date=end,
                location=location,
                include_saturdays=params.get("include_saturdays", False),
            )

            result = calculator.calculate(request)
            actual_working_days = result.working_days

            # Check if within expected range
            wd_range = expected.get("working_days_range", [0, 999])
            working_days_correct = wd_range[0] <= actual_working_days <= wd_range[1]

        except Exception as e:
            console.print(f"[yellow]Calculation error: {e}[/yellow]")

    return dates_correct, bundesland_correct, working_days_correct, actual_working_days


def run_evaluation(
    configs: list[LLMConfig],
    test_data: dict,
    output_dir: Path,
) -> list[EvaluationReport]:
    """Run evaluation across all LLM configs and test cases."""

    # Initialize calculator
    holiday_provider = HolidayProvider(language="de")
    location_resolver = LocationResolver(geocoding_enabled=False)
    calculator = WorkdayCalculator(holiday_provider, location_resolver)

    reports = []

    for config in configs:
        console.print(Panel(
            f"[bold blue]Evaluating: {config.name}[/bold blue]\n"
            f"Model: {config.model}\n"
            f"Endpoint: {config.endpoint}",
            title="LLM Configuration"
        ))

        results = []
        test_cases = test_data["test_cases"]

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"Testing {config.name}...",
                total=len(test_cases)
            )

            for test_case in test_cases:
                prompt_id = test_case["id"]
                prompt = test_case["prompt"]
                expected = test_case["expected"]

                try:
                    response, elapsed = call_llm(config, prompt)
                    extracted = extract_tool_call(response)

                    tool_called = extracted is not None and extracted.get("tool") == "calculate_workdays"

                    if tool_called and extracted:
                        dates_ok, bl_ok, wd_ok, actual_wd = verify_result(
                            extracted, expected, calculator
                        )
                    else:
                        dates_ok, bl_ok, wd_ok, actual_wd = False, False, False, None

                    result = TestResult(
                        prompt_id=prompt_id,
                        prompt=prompt,
                        llm_name=config.name,
                        model=config.model,
                        success=tool_called and dates_ok and bl_ok,
                        tool_called=tool_called,
                        parameters_extracted=extracted or {},
                        expected=expected,
                        working_days_correct=wd_ok,
                        bundesland_correct=bl_ok,
                        dates_correct=dates_ok,
                        response_time=elapsed,
                        raw_response=response[:500],  # Truncate for storage
                    )

                except Exception as e:
                    result = TestResult(
                        prompt_id=prompt_id,
                        prompt=prompt,
                        llm_name=config.name,
                        model=config.model,
                        success=False,
                        tool_called=False,
                        parameters_extracted={},
                        expected=expected,
                        working_days_correct=False,
                        bundesland_correct=False,
                        dates_correct=False,
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
        correct_params = sum(1 for r in results if r.success)
        correct_results = sum(1 for r in results if r.working_days_correct)
        avg_time = sum(r.response_time for r in results) / total if total > 0 else 0

        report = EvaluationReport(
            llm_name=config.name,
            model=config.model,
            total_tests=total,
            successful_tool_calls=tool_calls,
            correct_parameters=correct_params,
            correct_results=correct_results,
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

    table.add_row(
        "Total Tests",
        str(total),
        "100%"
    )
    table.add_row(
        "Tool Called Correctly",
        str(report.successful_tool_calls),
        f"{report.successful_tool_calls/total*100:.1f}%"
    )
    table.add_row(
        "Parameters Correct",
        str(report.correct_parameters),
        f"{report.correct_parameters/total*100:.1f}%"
    )
    table.add_row(
        "Working Days Correct",
        str(report.correct_results),
        f"{report.correct_results/total*100:.1f}%"
    )
    table.add_row(
        "Avg Response Time",
        f"{report.average_response_time:.2f}s",
        "-"
    )

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
                console.print(f"    [red]Tool not called[/red]")
            else:
                console.print(f"    [red]Dates: {f.dates_correct}, BL: {f.bundesland_correct}[/red]")
        console.print()


def save_results(reports: list[EvaluationReport], output_dir: Path):
    """Save evaluation results to JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for report in reports:
        safe_name = report.llm_name.replace("/", "_").replace(" ", "_")
        output_file = output_dir / f"eval_{safe_name}_{timestamp}.json"

        # Convert to dict
        report_dict = {
            "llm_name": report.llm_name,
            "model": report.model,
            "timestamp": timestamp,
            "metrics": {
                "total_tests": report.total_tests,
                "successful_tool_calls": report.successful_tool_calls,
                "correct_parameters": report.correct_parameters,
                "correct_results": report.correct_results,
                "average_response_time": report.average_response_time,
                "tool_call_rate": report.successful_tool_calls / report.total_tests,
                "parameter_accuracy": report.correct_parameters / report.total_tests,
                "result_accuracy": report.correct_results / report.total_tests,
            },
            "results": [
                {
                    "prompt_id": r.prompt_id,
                    "prompt": r.prompt,
                    "success": r.success,
                    "tool_called": r.tool_called,
                    "parameters_extracted": r.parameters_extracted,
                    "expected": r.expected,
                    "dates_correct": r.dates_correct,
                    "bundesland_correct": r.bundesland_correct,
                    "working_days_correct": r.working_days_correct,
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
    table.add_column("Param Acc %", justify="right")
    table.add_column("Result Acc %", justify="right")
    table.add_column("Avg Time", justify="right")

    for report in reports:
        total = report.total_tests
        table.add_row(
            report.llm_name,
            report.model[:20],
            f"{report.successful_tool_calls/total*100:.1f}%",
            f"{report.correct_parameters/total*100:.1f}%",
            f"{report.correct_results/total*100:.1f}%",
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
    import argparse

    parser = argparse.ArgumentParser(
        description="Evaluate MCP Workday Calculator with different LLMs"
    )
    parser.add_argument(
        "-t", "--test-file",
        type=Path,
        default=Path(__file__).parent / "test_prompts.json",
        help="Path to test prompts JSON file"
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=Path,
        default=Path(__file__).parent / "results",
        help="Output directory for results"
    )
    parser.add_argument(
        "-c", "--config",
        type=Path,
        help="Path to LLM config JSON file"
    )
    parser.add_argument(
        "--endpoint",
        type=str,
        default="http://localhost:11434",
        help="Ollama endpoint URL"
    )
    parser.add_argument(
        "-m", "--models",
        nargs="+",
        help="List of Ollama models to test"
    )
    parser.add_argument(
        "--openai-endpoint",
        type=str,
        help="OpenAI-compatible endpoint URL"
    )
    parser.add_argument(
        "--openai-model",
        type=str,
        help="OpenAI-compatible model name"
    )
    parser.add_argument(
        "--anthropic-model",
        type=str,
        help="Anthropic model name (requires ANTHROPIC_API_KEY env var)"
    )

    args = parser.parse_args()

    # Load test prompts
    console.print(f"[blue]Loading test prompts from: {args.test_file}[/blue]")
    test_data = load_test_prompts(args.test_file)
    console.print(f"[green]Loaded {len(test_data['test_cases'])} test cases[/green]")

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
            configs.append(LLMConfig(
                name=f"Ollama-{model}",
                endpoint=args.endpoint,
                model=model,
                api_type="ollama",
            ))
    else:
        # Use default configs
        configs = DEFAULT_CONFIGS

    # Add OpenAI-compatible endpoint if specified
    if args.openai_endpoint and args.openai_model:
        configs.append(LLMConfig(
            name=f"OpenAI-{args.openai_model}",
            endpoint=args.openai_endpoint,
            model=args.openai_model,
            api_type="openai",
        ))

    # Add Anthropic if specified
    if args.anthropic_model:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            console.print("[red]ANTHROPIC_API_KEY not set[/red]")
        else:
            configs.append(LLMConfig(
                name=f"Anthropic-{args.anthropic_model}",
                endpoint="https://api.anthropic.com",
                model=args.anthropic_model,
                api_type="anthropic",
                api_key=api_key,
            ))

    if not configs:
        console.print("[red]No LLM configurations specified[/red]")
        return 1

    console.print(f"[blue]Testing {len(configs)} LLM configuration(s)[/blue]")

    # Run evaluation
    reports = run_evaluation(configs, test_data, args.output_dir)

    # Show comparison
    display_comparison_table(reports)

    return 0


if __name__ == "__main__":
    sys.exit(main())

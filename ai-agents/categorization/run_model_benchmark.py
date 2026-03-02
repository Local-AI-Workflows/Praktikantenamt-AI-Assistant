#!/usr/bin/env python3
"""
Multi-model benchmark runner for email categorization prompts.

Evaluates N models (Ollama local + OpenAI + Anthropic) over multiple iterations
and reports mean/std accuracy metrics with live progress display.

Usage:
    python run_model_benchmark.py
    python run_model_benchmark.py --config benchmark_config.yaml
    python run_model_benchmark.py --models llama3.1:8b gpt-4.1-mini
    python run_model_benchmark.py --iterations 3
    python run_model_benchmark.py --dry-run
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import yaml
from dotenv import load_dotenv
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.text import Text

# Ensure the script finds the prompt_tester package when run from this directory
sys.path.insert(0, str(Path(__file__).parent))

from prompt_tester.clients import AnthropicClient, OllamaClient, OpenAIClient
from prompt_tester.clients.base import BaseClient
from prompt_tester.core.executor import PromptExecutor
from prompt_tester.core.validator import Validator
from prompt_tester.data.benchmark_schemas import (
    BenchmarkModelResult,
    BenchmarkRankEntry,
    BenchmarkReport,
    ModelBenchmarkStatus,
    ModelConfig,
)
from prompt_tester.data.loader import DataLoader
from prompt_tester.data.schemas import Email, PromptConfig
from prompt_tester.output.exporter import ResultExporter

console = Console()


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


def load_benchmark_config(config_path: str) -> Tuple[PromptConfig, List[ModelConfig], dict]:
    """
    Parse benchmark_config.yaml into structured objects.

    Returns:
        (prompt_config, model_configs, benchmark_settings)
    """
    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    # --- Prompt ---
    prompt_section = raw.get("prompt", {})
    user_prompt_file = prompt_section.get("user_prompt", "prompts/v1_baseline.txt")
    system_prompt_file = prompt_section.get("system_prompt", "prompts/system_prompt.txt")

    user_prompt_text = DataLoader.load_prompt(user_prompt_file)
    system_prompt_text = DataLoader.load_prompt(system_prompt_file) if system_prompt_file else ""

    prompt_name = Path(user_prompt_file).stem
    prompt_config = PromptConfig(
        name=prompt_name,
        version="1.0",
        system_prompt=system_prompt_text,
        user_prompt_template=user_prompt_text,
    )

    # --- Benchmark settings ---
    bench = raw.get("benchmark", {})
    settings = {
        "num_iterations": bench.get("num_iterations", 5),
        "output_directory": bench.get("output_directory", "results"),
        "dataset": bench.get("dataset", "test_data/dummy_emails.json"),
        "ollama_endpoint": bench.get(
            "ollama_endpoint", "http://gpu-server01.ios.htwg-konstanz.de:11434"
        ),
        "categories": bench.get(
            "categories",
            [
                "contract_submission",
                "international_office_question",
                "internship_postponement",
                "uncategorized",
            ],
        ),
        "prompt_user_file": user_prompt_file,
        "prompt_system_file": system_prompt_file,
    }

    # --- Models ---
    model_configs = [ModelConfig(**m) for m in raw.get("models", [])]

    return prompt_config, model_configs, settings


# ---------------------------------------------------------------------------
# Progress display helpers
# ---------------------------------------------------------------------------


def _accuracy_color(accuracy: Optional[float]) -> str:
    """Return Rich color name based on accuracy value."""
    if accuracy is None:
        return "dim"
    if accuracy >= 0.90:
        return "green"
    if accuracy >= 0.75:
        return "yellow"
    return "red"


def _build_summary_table(
    statuses: Dict[str, ModelBenchmarkStatus], num_iterations: int
) -> Table:
    """Build the live status table shown alongside the progress bars."""
    table = Table(show_header=True, header_style="bold white", border_style="dim white")
    table.add_column("#", justify="right", style="dim", width=3)
    table.add_column("Model", style="cyan", min_width=20)
    table.add_column("Provider", style="blue", width=11)
    table.add_column("Status", width=9)
    table.add_column("Iter", justify="center", width=7)
    table.add_column("Accuracy", justify="right", width=10)
    table.add_column("Std", justify="right", width=8)
    table.add_column("ms/email", justify="right", width=9)

    # Sort: done first (by accuracy desc), then running, then pending, then error
    order = {"running": 0, "done": 1, "pending": 2, "error": 3}
    sorted_statuses = sorted(
        statuses.values(),
        key=lambda s: (
            order.get(s.status, 99),
            -(s.mean_accuracy or 0) if s.status == "done" else 0,
        ),
    )

    rank = 1
    for s in sorted_statuses:
        if s.status == "done":
            rank_str = str(rank)
            rank += 1
        else:
            rank_str = "-"

        # Status cell
        if s.status == "pending":
            status_text = Text("Pending", style="dim")
        elif s.status == "running":
            status_text = Text("Running", style="bold yellow")
        elif s.status == "done":
            status_text = Text("Done", style="bold green")
        else:
            status_text = Text("Error", style="bold red")

        # Iteration cell
        iter_str = f"{s.current_iteration}/{num_iterations}" if s.status != "pending" else "-"

        # Accuracy cell
        if s.mean_accuracy is not None:
            acc_pct = f"{s.mean_accuracy * 100:.1f}%"
            if s.status == "running":
                acc_pct += "*"
            acc_text = Text(acc_pct, style=_accuracy_color(s.mean_accuracy))
        else:
            acc_text = Text("-", style="dim")

        # Std cell
        if s.std_accuracy is not None and s.status == "done":
            std_text = Text(f"±{s.std_accuracy * 100:.1f}%", style="dim")
        else:
            std_text = Text("-", style="dim")

        # ms/email cell
        if s.mean_execution_time_ms is not None:
            ms_text = Text(f"{s.mean_execution_time_ms:.0f}", style="dim")
        else:
            ms_text = Text("-", style="dim")

        table.add_row(rank_str, s.display_name, s.provider, status_text, iter_str, acc_text, std_text, ms_text)

    return table


# ---------------------------------------------------------------------------
# BenchmarkRunner
# ---------------------------------------------------------------------------


class BenchmarkRunner:
    """Orchestrates multi-model benchmark execution with live Rich progress display."""

    def __init__(
        self,
        prompt_config: PromptConfig,
        emails: List[Email],
        categories: List[str],
        num_iterations: int = 5,
        output_directory: str = "results",
        ollama_endpoint: str = "http://localhost:11434",
    ):
        self.prompt_config = prompt_config
        self.emails = emails
        self.categories = categories
        self.num_iterations = num_iterations
        self.output_directory = output_directory
        self.ollama_endpoint = ollama_endpoint

    def _build_client(self, model_config: ModelConfig) -> BaseClient:
        """Factory: instantiate the correct client based on provider."""
        if model_config.provider == "ollama":
            endpoint = model_config.endpoint or self.ollama_endpoint
            return OllamaClient(
                endpoint=endpoint,
                model=model_config.model_id,
                timeout=model_config.timeout,
                max_retries=model_config.max_retries,
            )
        elif model_config.provider == "openai":
            return OpenAIClient(
                model=model_config.model_id,
                max_tokens=model_config.max_tokens,
                temperature=model_config.temperature,
            )
        elif model_config.provider == "anthropic":
            return AnthropicClient(
                model=model_config.model_id,
                max_tokens=model_config.max_tokens,
            )
        else:
            raise ValueError(f"Unknown provider: {model_config.provider!r}")

    def _run_single_model(
        self,
        model_config: ModelConfig,
        statuses: Dict[str, ModelBenchmarkStatus],
        progress: Progress,
        task_iter: int,
        task_email: int,
        live: Live,
    ) -> BenchmarkModelResult:
        """Run num_iterations for one model, updating live progress."""
        model_id = model_config.model_id
        label = model_config.label

        # Build client
        try:
            client = self._build_client(model_config)
        except Exception as e:
            statuses[model_id].status = "error"
            statuses[model_id].error_message = str(e)
            live.update(
                Group(
                    Panel(progress, title="[bold white]Model Benchmark Runner", border_style="blue"),
                    _build_summary_table(statuses, self.num_iterations),
                )
            )
            return BenchmarkModelResult(
                model_id=model_id,
                display_name=label,
                provider=model_config.provider,
                status="error",
                error_message=str(e),
            )

        # Health check for Ollama
        if model_config.provider == "ollama" and not client.health_check():
            msg = f"Ollama endpoint not reachable: {model_config.endpoint or self.ollama_endpoint}"
            statuses[model_id].status = "error"
            statuses[model_id].error_message = msg
            live.update(
                Group(
                    Panel(progress, title="[bold white]Model Benchmark Runner", border_style="blue"),
                    _build_summary_table(statuses, self.num_iterations),
                )
            )
            return BenchmarkModelResult(
                model_id=model_id,
                display_name=label,
                provider=model_config.provider,
                status="error",
                error_message=msg,
            )

        # --- Run iterations ---
        executor = PromptExecutor(client)
        validator = Validator(self.categories)
        iteration_reports = []
        partial_accuracies: List[float] = []

        statuses[model_id].status = "running"
        statuses[model_id].current_iteration = 0

        try:
            for iteration in range(self.num_iterations):
                results = []
                progress.reset(task_email, total=len(self.emails), visible=True)
                progress.update(task_email, description=f"  Emails  ")

                for email in self.emails:
                    result = executor.execute_single(email, self.prompt_config)
                    results.append(result)
                    progress.advance(task_email)
                    # Refresh live display every email
                    live.update(
                        Group(
                            Panel(progress, title="[bold white]Model Benchmark Runner", border_style="blue"),
                            _build_summary_table(statuses, self.num_iterations),
                        )
                    )

                report = validator.validate_results(results, prompt_name=model_id)
                iteration_reports.append(report)
                partial_accuracies.append(report.overall_accuracy)

                # Update partial accuracy in the status table
                statuses[model_id].current_iteration = iteration + 1
                statuses[model_id].mean_accuracy = float(np.mean(partial_accuracies))
                statuses[model_id].mean_execution_time_ms = report.mean_execution_time * 1000

                progress.advance(task_iter)
                live.update(
                    Group(
                        Panel(progress, title="[bold white]Model Benchmark Runner", border_style="blue"),
                        _build_summary_table(statuses, self.num_iterations),
                    )
                )

        except Exception as e:
            statuses[model_id].status = "error"
            statuses[model_id].error_message = str(e)
            live.update(
                Group(
                    Panel(progress, title="[bold white]Model Benchmark Runner", border_style="blue"),
                    _build_summary_table(statuses, self.num_iterations),
                )
            )
            return BenchmarkModelResult(
                model_id=model_id,
                display_name=label,
                provider=model_config.provider,
                status="error",
                error_message=str(e),
            )

        # Aggregate
        aggregated = validator.aggregate_reports(iteration_reports)
        statuses[model_id].status = "done"
        statuses[model_id].mean_accuracy = aggregated.mean_accuracy
        statuses[model_id].std_accuracy = aggregated.std_accuracy
        statuses[model_id].mean_execution_time_ms = aggregated.mean_execution_time * 1000

        live.update(
            Group(
                Panel(progress, title="[bold white]Model Benchmark Runner", border_style="blue"),
                _build_summary_table(statuses, self.num_iterations),
            )
        )

        return BenchmarkModelResult(
            model_id=model_id,
            display_name=label,
            provider=model_config.provider,
            status="success",
            aggregated_report=aggregated,
        )

    def run(self, model_configs: List[ModelConfig]) -> BenchmarkReport:
        """
        Run the full benchmark across all enabled models.

        Args:
            model_configs: List of model configurations to benchmark

        Returns:
            BenchmarkReport with all results and rankings
        """
        enabled = [m for m in model_configs if m.enabled]
        total_work = len(enabled) * self.num_iterations

        # Initialise statuses
        statuses: Dict[str, ModelBenchmarkStatus] = {
            m.model_id: ModelBenchmarkStatus(
                model_id=m.model_id,
                display_name=m.label,
                provider=m.provider,
                total_iterations=self.num_iterations,
            )
            for m in enabled
        }

        # Progress setup: 3 tasks
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(bar_width=28),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            console=console,
        )
        task_overall = progress.add_task("Models  ", total=len(enabled))
        task_iter = progress.add_task("Iterations", total=self.num_iterations, visible=False)
        task_email = progress.add_task("Emails  ", total=len(self.emails), visible=False)

        model_results: Dict[str, BenchmarkModelResult] = {}

        with Live(
            Group(
                Panel(progress, title="[bold white]Model Benchmark Runner", border_style="blue"),
                _build_summary_table(statuses, self.num_iterations),
            ),
            console=console,
            refresh_per_second=8,
        ) as live:
            for i, model_config in enumerate(enabled):
                label = model_config.label
                progress.update(
                    task_overall,
                    description=f"Models   [yellow]{label}[/yellow]",
                )
                progress.reset(task_iter, total=self.num_iterations, visible=True)
                progress.update(task_iter, description="Iterations")

                result = self._run_single_model(
                    model_config=model_config,
                    statuses=statuses,
                    progress=progress,
                    task_iter=task_iter,
                    task_email=task_email,
                    live=live,
                )
                model_results[model_config.model_id] = result
                progress.advance(task_overall)

            # Hide per-model tasks after all models done
            progress.update(task_iter, visible=False)
            progress.update(task_email, visible=False)
            progress.update(task_overall, description="Models   [green]Done[/green]")
            live.update(
                Group(
                    Panel(progress, title="[bold white]Model Benchmark Runner", border_style="blue"),
                    _build_summary_table(statuses, self.num_iterations),
                )
            )

        # Build rankings
        succeeded = [
            (mid, r)
            for mid, r in model_results.items()
            if r.status == "success" and r.aggregated_report is not None
        ]
        succeeded.sort(key=lambda x: x[1].aggregated_report.mean_accuracy, reverse=True)

        rankings = [
            BenchmarkRankEntry(
                rank=idx + 1,
                model_id=mid,
                display_name=r.display_name,
                provider=r.provider,
                mean_accuracy=r.aggregated_report.mean_accuracy,
                std_accuracy=r.aggregated_report.std_accuracy,
                mean_execution_time_ms=r.aggregated_report.mean_execution_time * 1000,
                mean_parse_errors=r.aggregated_report.mean_parse_errors,
            )
            for idx, (mid, r) in enumerate(succeeded)
        ]

        winner = succeeded[0][0] if succeeded else None

        return BenchmarkReport(
            benchmark_timestamp=datetime.now(),
            prompt_name=self.prompt_config.name,
            prompt_user_file="",  # filled by caller
            prompt_system_file="",  # filled by caller
            num_iterations=self.num_iterations,
            total_emails=len(self.emails),
            total_models_attempted=len(enabled),
            total_models_succeeded=len(succeeded),
            model_results=model_results,
            rankings=rankings,
            winner=winner,
        )


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def print_final_table(report: BenchmarkReport) -> None:
    """Print the final ranked comparison table after all models finish."""
    table = Table(
        title=f"\nBenchmark Results — {report.prompt_name} ({report.num_iterations} iterations, {report.total_emails} emails)",
        show_header=True,
        header_style="bold magenta",
        border_style="magenta",
    )
    table.add_column("Rank", justify="right", style="bold", width=5)
    table.add_column("Model", style="cyan", min_width=20)
    table.add_column("Provider", style="blue", width=11)
    table.add_column("Mean Accuracy", justify="right", width=14)
    table.add_column("Std Dev", justify="right", width=9)
    table.add_column("Parse Errors", justify="right", width=13)
    table.add_column("ms/email", justify="right", width=9)

    for entry in report.rankings:
        acc_color = _accuracy_color(entry.mean_accuracy)
        rank_str = f"[bold]{entry.rank}[/bold]"
        if entry.rank == 1:
            rank_str = f"[bold yellow]{entry.rank} ★[/bold yellow]"

        table.add_row(
            rank_str,
            entry.display_name,
            entry.provider,
            Text(f"{entry.mean_accuracy * 100:.2f}%", style=acc_color),
            Text(f"±{entry.std_accuracy * 100:.2f}%", style="dim"),
            Text(f"{entry.mean_parse_errors:.1f}", style="dim"),
            Text(f"{entry.mean_execution_time_ms:.0f}", style="dim"),
        )

    # Add failed models at the bottom
    for model_id, result in report.model_results.items():
        if result.status == "error":
            table.add_row(
                "—",
                result.display_name,
                result.provider,
                Text("ERROR", style="bold red"),
                "—",
                "—",
                "—",
            )

    console.print(table)


def print_dry_run(model_configs: List[ModelConfig], settings: dict) -> None:
    """Print model list and exit without calling any APIs."""
    console.print("\n[bold cyan]Dry run — models that would be benchmarked:[/bold cyan]\n")
    table = Table(show_header=True, header_style="bold white")
    table.add_column("Model ID", style="cyan")
    table.add_column("Display Name")
    table.add_column("Provider", style="blue")
    table.add_column("Enabled")
    table.add_column("Timeout / Tokens", justify="right")

    for m in model_configs:
        enabled_text = Text("Yes", style="green") if m.enabled else Text("No", style="dim red")
        extra = f"{m.timeout}s" if m.provider == "ollama" else f"{m.max_tokens} tok"
        table.add_row(m.model_id, m.label, m.provider, enabled_text, extra)

    console.print(table)
    console.print(
        f"\nDataset:     [cyan]{settings['dataset']}[/cyan]"
        f"\nIterations:  [cyan]{settings['num_iterations']}[/cyan]"
        f"\nPrompt:      [cyan]{settings['prompt_user_file']}[/cyan]"
        f"\nOutput dir:  [cyan]{settings['output_directory']}[/cyan]\n"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    # Load .env before anything else
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Multi-model benchmark runner for email categorization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_model_benchmark.py
  python run_model_benchmark.py --models llama3.1:8b gpt-4.1-mini
  python run_model_benchmark.py --iterations 3 --config benchmark_config.yaml
  python run_model_benchmark.py --dry-run
""",
    )
    parser.add_argument(
        "--config",
        default="benchmark_config.yaml",
        help="Path to benchmark config YAML (default: benchmark_config.yaml)",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        metavar="MODEL_ID",
        help="Subset of model_ids to run (e.g. llama3.1:8b gpt-4.1-mini)",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=None,
        help="Override num_iterations from config",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print model list without making any API calls",
    )
    args = parser.parse_args()

    # Load config
    config_path = args.config
    if not Path(config_path).exists():
        console.print(f"[bold red]Config file not found:[/bold red] {config_path}")
        sys.exit(1)

    prompt_config, model_configs, settings = load_benchmark_config(config_path)

    # Apply CLI overrides
    if args.iterations:
        settings["num_iterations"] = args.iterations
    if args.models:
        allowed = set(args.models)
        # Mark non-matching as disabled (don't remove, keep for display)
        for m in model_configs:
            if m.model_id not in allowed:
                m.enabled = False

    # Apply OLLAMA_ENDPOINT env override to all Ollama models without explicit endpoint
    env_ollama = os.getenv("OLLAMA_ENDPOINT")
    if env_ollama:
        settings["ollama_endpoint"] = env_ollama

    # Dry run
    if args.dry_run:
        print_dry_run(model_configs, settings)
        sys.exit(0)

    # Validate API keys
    enabled_providers = {m.provider for m in model_configs if m.enabled}
    missing_keys = []
    if "openai" in enabled_providers and not os.getenv("OPENAI_API_KEY"):
        missing_keys.append("OPENAI_API_KEY (for OpenAI models)")
    if "anthropic" in enabled_providers and not os.getenv("ANTHROPIC_API_KEY"):
        missing_keys.append("ANTHROPIC_API_KEY (for Anthropic models)")
    if missing_keys:
        console.print("[bold red]Missing API keys in .env:[/bold red]")
        for key in missing_keys:
            console.print(f"  • {key}")
        console.print("\nSet them in [cyan]ai-agents/categorization/.env[/cyan] and re-run.")
        sys.exit(1)

    # Load dataset
    dataset_path = settings["dataset"]
    if not Path(dataset_path).exists():
        console.print(f"[bold red]Dataset not found:[/bold red] {dataset_path}")
        sys.exit(1)
    emails = DataLoader.load_emails(dataset_path)

    # Summary header
    enabled_count = sum(1 for m in model_configs if m.enabled)
    console.print(
        f"\n[bold]Benchmark:[/bold] [cyan]{prompt_config.name}[/cyan]  "
        f"[bold]Models:[/bold] [cyan]{enabled_count}[/cyan]  "
        f"[bold]Iterations:[/bold] [cyan]{settings['num_iterations']}[/cyan]  "
        f"[bold]Emails:[/bold] [cyan]{len(emails)}[/cyan]\n"
    )

    # Run benchmark
    runner = BenchmarkRunner(
        prompt_config=prompt_config,
        emails=emails,
        categories=settings["categories"],
        num_iterations=settings["num_iterations"],
        output_directory=settings["output_directory"],
        ollama_endpoint=settings["ollama_endpoint"],
    )
    report = runner.run(model_configs)

    # Patch prompt file paths (runner doesn't have access to original config path strings)
    report = BenchmarkReport(
        **{
            **report.model_dump(),
            "prompt_user_file": settings["prompt_user_file"],
            "prompt_system_file": settings["prompt_system_file"],
        }
    )

    # Export
    exporter = ResultExporter(output_directory=settings["output_directory"])
    output_path = exporter.export_benchmark_report(report)

    # Final table
    print_final_table(report)
    console.print(
        f"\n[bold]Report saved:[/bold] [cyan]{output_path}[/cyan]\n"
        f"[bold]Winner:[/bold]       [green]{report.winner or 'N/A'}[/green]\n"
        f"[bold]Succeeded:[/bold]    [cyan]{report.total_models_succeeded}/{report.total_models_attempted}[/cyan] models\n"
    )


if __name__ == "__main__":
    main()

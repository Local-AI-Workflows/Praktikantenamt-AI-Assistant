"""
CLI interface for prompt testing tool.
"""

import sys
from pathlib import Path

import click

from prompt_tester.config.manager import ConfigManager
from prompt_tester.core.comparator import Comparator
from prompt_tester.core.executor import OllamaClient, PromptExecutor
from prompt_tester.core.validator import Validator
from prompt_tester.data.loader import DataLoader
from prompt_tester.output.exporter import ResultExporter
from prompt_tester.output.formatter import ConsoleFormatter


@click.group()
def main():
    """Prompt testing environment for email categorization."""
    pass


@main.command()
@click.option(
    "--prompt",
    "-p",
    required=True,
    type=click.Path(exists=True),
    help="Path to prompt file",
)
@click.option(
    "--system-prompt",
    "-s",
    type=click.Path(exists=True),
    help="Path to system prompt file (optional)",
)
@click.option(
    "--dataset",
    "-d",
    default="test_data/dummy_emails.json",
    type=click.Path(exists=True),
    help="Path to test dataset (default: test_data/dummy_emails.json)",
)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Path to config file (optional)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file path (optional, auto-generated if not provided)",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["json", "csv", "both"]),
    default="both",
    help="Output format (default: both)",
)
@click.option(
    "--iterations",
    "-i",
    default=1,
    type=int,
    help="Number of test iterations for robust evaluation (default: 1)",
)
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def test(prompt, system_prompt, dataset, config, output, format, iterations, verbose):
    """Run validation on a single prompt."""
    try:
        # Load configuration
        config_manager = ConfigManager(config)
        cfg = config_manager.load_config()

        # Initialize formatter with categories for confusion matrix
        formatter = ConsoleFormatter(cfg.categories)

        # Check Ollama health
        ollama_client = OllamaClient(
            endpoint=cfg.ollama_endpoint,
            model=cfg.ollama_model,
            timeout=cfg.ollama_timeout,
            max_retries=cfg.ollama_max_retries,
        )

        if not ollama_client.health_check():
            formatter.console.print(
                f"[bold red]Error:[/bold red] Cannot connect to Ollama at {cfg.ollama_endpoint}"
            )
            formatter.console.print("Please ensure Ollama is running and accessible.")
            sys.exit(1)

        # Load emails
        formatter.console.print(f"Loading dataset from [cyan]{dataset}[/cyan]...")
        emails = DataLoader.load_emails(dataset)
        formatter.console.print(f"Loaded {len(emails)} emails")

        # Validate dataset
        DataLoader.validate_dataset(emails, cfg.categories)

        # Load prompts
        formatter.console.print(f"Loading prompt from [cyan]{prompt}[/cyan]...")

        # Determine prompt name and version from path
        prompt_path = Path(prompt)
        prompt_name = prompt_path.stem
        prompt_version = "1.0"  # Default version

        # Create prompt config
        if system_prompt:
            prompt_config = DataLoader.create_prompt_config(
                name=prompt_name,
                version=prompt_version,
                system_prompt_path=system_prompt,
                user_prompt_path=prompt,
            )
        else:
            # Use empty system prompt if not provided
            user_prompt_text = DataLoader.load_prompt(prompt)
            from prompt_tester.data.schemas import PromptConfig
            prompt_config = PromptConfig(
                name=prompt_name,
                version=prompt_version,
                system_prompt="",
                user_prompt_template=user_prompt_text,
            )

        # Execute prompts
        executor = PromptExecutor(ollama_client)
        validator = Validator(cfg.categories)

        # Validate iterations parameter
        if iterations < 1:
            formatter.console.print("[bold red]Error:[/bold red] Iterations must be >= 1")
            sys.exit(1)

        # Run multiple iterations if requested
        if iterations > 1:
            formatter.console.print(
                f"Running {iterations} test iterations for robust evaluation..."
            )
            all_reports = []

            for iteration in range(iterations):
                formatter.console.print(
                    f"\n[bold cyan]Iteration {iteration + 1}/{iterations}[/bold cyan]"
                )

                with formatter.create_progress_bar() as progress:
                    task = progress.add_task(
                        f"Iteration {iteration + 1}...", total=len(emails)
                    )
                    results = []
                    for i, email in enumerate(emails):
                        result = executor.execute_single(email, prompt_config)
                        results.append(result)
                        progress.update(task, advance=1)
                        if verbose:
                            formatter.console.print(
                                f"  [{i+1}/{len(emails)}] {email.id}: {result.predicted_category}"
                            )

                # Validate this iteration
                report = validator.validate_results(
                    results, prompt_name=prompt_name, prompt_version=prompt_version
                )
                all_reports.append(report)

                if verbose:
                    formatter.console.print(
                        f"Iteration {iteration + 1} Accuracy: {report.overall_accuracy:.2%}"
                    )

            # Aggregate all reports
            aggregated_report = validator.aggregate_reports(all_reports)

            # Display aggregated results
            formatter.print_aggregated_report(aggregated_report)

            # Export aggregated results
            exporter = ResultExporter(
                output_directory=cfg.output_directory,
                timestamp_format=cfg.timestamp_format,
            )

            if format == "json":
                json_path = exporter.export_aggregated_json(aggregated_report, cfg, output)
                formatter.console.print(
                    f"Aggregated results saved to [cyan]{json_path}[/cyan]"
                )
            elif format == "csv":
                # For CSV, export the last iteration's results
                csv_path = exporter.export_csv(all_reports[-1].misclassifications, output)
                formatter.console.print(f"Results saved to [cyan]{csv_path}[/cyan]")
            else:  # both
                json_path = exporter.export_aggregated_json(aggregated_report, cfg, output)
                # For CSV, export the last iteration's results
                csv_path = exporter.export_csv(
                    results, output=output.replace(".json", ".csv") if output else None
                )
                formatter.console.print("Aggregated results saved to:")
                formatter.console.print(f"  • JSON: [cyan]{json_path}[/cyan]")
                formatter.console.print(f"  • CSV (last iteration): [cyan]{csv_path}[/cyan]")

        else:
            # Single iteration (existing behavior for backwards compatibility)
            formatter.console.print(f"Running categorization on {len(emails)} emails...")

            with formatter.create_progress_bar() as progress:
                task = progress.add_task("Processing emails...", total=len(emails))
                results = []
                for i, email in enumerate(emails):
                    result = executor.execute_single(email, prompt_config)
                    results.append(result)
                    progress.update(task, advance=1)
                    if verbose:
                        formatter.console.print(
                            f"  [{i+1}/{len(emails)}] {email.id}: {result.predicted_category}"
                        )

            # Validate results
            report = validator.validate_results(
                results, prompt_name=prompt_name, prompt_version=prompt_version
            )

            # Display results
            formatter.print_validation_report(report)

            # Export results
            exporter = ResultExporter(
                output_directory=cfg.output_directory,
                timestamp_format=cfg.timestamp_format,
            )

            if format == "json":
                json_path = exporter.export_json(report, cfg, output)
                formatter.console.print(f"Results saved to [cyan]{json_path}[/cyan]")
            elif format == "csv":
                csv_path = exporter.export_csv(results, output)
                formatter.console.print(f"Results saved to [cyan]{csv_path}[/cyan]")
            else:  # both
                json_path, csv_path = exporter.export_both(report, results, cfg)
                formatter.console.print(f"Results saved to:")
                formatter.console.print(f"  • JSON: [cyan]{json_path}[/cyan]")
                formatter.console.print(f"  • CSV: [cyan]{csv_path}[/cyan]")

    except Exception as e:
        formatter.console.print(f"[bold red]Error:[/bold red] {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@main.command()
@click.option(
    "--prompts",
    "-p",
    required=True,
    multiple=True,
    type=click.Path(exists=True),
    help="Paths to prompt files to compare (use multiple -p flags)",
)
@click.option(
    "--system-prompt",
    "-s",
    type=click.Path(exists=True),
    help="Path to shared system prompt file (optional)",
)
@click.option(
    "--dataset",
    "-d",
    default="test_data/dummy_emails.json",
    type=click.Path(exists=True),
    help="Path to test dataset",
)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Path to config file (optional)",
)
@click.option("--output", "-o", type=click.Path(), help="Output file path (optional)")
@click.option("--show-disagreements", is_flag=True, help="Show emails where prompts disagree")
@click.option(
    "--iterations",
    "-i",
    default=1,
    type=int,
    help="Number of test iterations per prompt for robust comparison (default: 1)",
)
def compare(prompts, system_prompt, dataset, config, output, show_disagreements, iterations):
    """Compare multiple prompts side-by-side. With a single prompt, runs aggregated evaluation."""
    try:
        # Load configuration
        config_manager = ConfigManager(config)
        cfg = config_manager.load_config()

        # Initialize formatter with categories
        formatter = ConsoleFormatter(cfg.categories)

        # Check Ollama health
        ollama_client = OllamaClient(
            endpoint=cfg.ollama_endpoint,
            model=cfg.ollama_model,
            timeout=cfg.ollama_timeout,
            max_retries=cfg.ollama_max_retries,
        )

        if not ollama_client.health_check():
            formatter.console.print(
                f"[bold red]Error:[/bold red] Cannot connect to Ollama at {cfg.ollama_endpoint}"
            )
            sys.exit(1)

        # Load emails
        formatter.console.print(f"Loading dataset from [cyan]{dataset}[/cyan]...")
        emails = DataLoader.load_emails(dataset)
        formatter.console.print(f"Loaded {len(emails)} emails")

        # Load prompt configs
        prompt_configs = []
        for prompt_path in prompts:
            prompt_name = Path(prompt_path).stem

            if system_prompt:
                prompt_config = DataLoader.create_prompt_config(
                    name=prompt_name,
                    version="1.0",
                    system_prompt_path=system_prompt,
                    user_prompt_path=prompt_path,
                )
            else:
                user_prompt_text = DataLoader.load_prompt(prompt_path)
                from prompt_tester.data.schemas import PromptConfig
                prompt_config = PromptConfig(
                    name=prompt_name,
                    version="1.0",
                    system_prompt="",
                    user_prompt_template=user_prompt_text,
                )

            prompt_configs.append(prompt_config)
            formatter.console.print(f"Loaded prompt: [cyan]{prompt_name}[/cyan]")

        # Run comparison
        executor = PromptExecutor(ollama_client)
        validator = Validator(cfg.categories)

        # Validate iterations parameter
        if iterations < 1:
            formatter.console.print("[bold red]Error:[/bold red] Iterations must be >= 1")
            sys.exit(1)

        # Single-prompt mode: run aggregated evaluation instead of comparison
        if len(prompt_configs) == 1:
            prompt_config = prompt_configs[0]
            formatter.console.print(
                f"Single prompt detected — running aggregated evaluation "
                f"({iterations} iteration{'s' if iterations > 1 else ''})..."
            )

            prompt_reports = []
            for iteration in range(iterations):
                formatter.console.print(
                    f"  Iteration {iteration + 1}/{iterations}..."
                )
                results = executor.execute_batch(emails, prompt_config)
                report = validator.validate_results(
                    results, prompt_config.name, prompt_config.version
                )
                prompt_reports.append(report)

            aggregated_report = validator.aggregate_reports(prompt_reports)
            formatter.print_aggregated_report(aggregated_report)

            exporter = ResultExporter(
                output_directory=cfg.output_directory,
                timestamp_format=cfg.timestamp_format,
            )
            json_path = exporter.export_aggregated_json(aggregated_report, cfg, output)
            formatter.console.print(
                f"Aggregated results saved to [cyan]{json_path}[/cyan]"
            )
            return

        comparator = Comparator(executor, validator)

        # Run multiple iterations if requested
        if iterations > 1:
            formatter.console.print(
                f"Comparing {len(prompts)} prompts with {iterations} iterations each..."
            )
            all_aggregated_reports = {}

            for prompt_config in prompt_configs:
                formatter.console.print(
                    f"\n[bold cyan]Testing {prompt_config.name} ({iterations} iterations)[/bold cyan]"
                )

                # Collect multiple reports for this prompt
                prompt_reports = []
                for iteration in range(iterations):
                    formatter.console.print(
                        f"  Iteration {iteration + 1}/{iterations}..."
                    )
                    results = executor.execute_batch(emails, prompt_config)
                    report = validator.validate_results(
                        results, prompt_config.name, prompt_config.version
                    )
                    prompt_reports.append(report)

                # Aggregate reports for this prompt
                aggregated = validator.aggregate_reports(prompt_reports)
                all_aggregated_reports[prompt_config.name] = aggregated
                formatter.console.print(
                    f"  Mean Accuracy: {aggregated.mean_accuracy:.2%} ± {aggregated.std_accuracy:.2%}"
                )

            # Create aggregated comparison
            aggregated_comparison = comparator.create_aggregated_comparison(
                all_aggregated_reports
            )

            # Display results
            formatter.print_aggregated_comparison_report(aggregated_comparison)

            # Export results
            exporter = ResultExporter(
                output_directory=cfg.output_directory,
                timestamp_format=cfg.timestamp_format,
            )

            comparison_path = exporter.export_aggregated_comparison(
                aggregated_comparison, cfg, output
            )
            formatter.console.print(
                f"Aggregated comparison results saved to [cyan]{comparison_path}[/cyan]"
            )

        else:
            # Single iteration (existing behavior for backwards compatibility)
            formatter.console.print(
                f"Comparing {len(prompts)} prompts on {len(emails)} emails..."
            )

            with formatter.create_progress_bar() as progress:
                task = progress.add_task(
                    "Running comparison...", total=len(prompts) * len(emails)
                )
                # Note: comparator handles the actual execution
                comparison_report = comparator.compare_prompts(prompt_configs, emails)
                progress.update(task, completed=len(prompts) * len(emails))

            # Display results
            formatter.print_comparison_report(comparison_report)

            # Export results
            exporter = ResultExporter(
                output_directory=cfg.output_directory,
                timestamp_format=cfg.timestamp_format,
            )

            comparison_path = exporter.export_comparison(comparison_report, cfg, output)
            formatter.console.print(
                f"Comparison results saved to [cyan]{comparison_path}[/cyan]"
            )

    except Exception as e:
        formatter.console.print(f"[bold red]Error:[/bold red] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


@main.command()
@click.argument("result_file", type=click.Path(exists=True))
@click.option(
    "--format",
    "-f",
    type=click.Choice(["console", "markdown", "html"]),
    default="console",
    help="Output format (default: console)",
)
@click.option("--output", "-o", type=click.Path(), help="Output file path (for markdown/html)")
def report(result_file, format, output):
    """Generate formatted report from saved results."""
    formatter = ConsoleFormatter()

    try:
        # Load JSON results
        import json
        with open(result_file, "r", encoding="utf-8") as f:
            result_data = json.load(f)

        # For now, just display as console output
        # Can be enhanced to support markdown/html
        if format == "console":
            formatter.console.print()
            formatter.console.rule("[bold blue]Test Report[/bold blue]")
            formatter.console.print()
            formatter.console.print(json.dumps(result_data, indent=2))
        else:
            formatter.console.print(
                f"[yellow]Warning:[/yellow] {format} format not yet implemented. "
                f"Displaying console format instead."
            )
            formatter.console.print()
            formatter.console.print(json.dumps(result_data, indent=2))

    except Exception as e:
        formatter.console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

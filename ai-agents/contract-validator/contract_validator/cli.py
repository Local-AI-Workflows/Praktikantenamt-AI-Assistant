"""
CLI interface for contract validation testing tool.
"""

import sys
from pathlib import Path

import click

from contract_validator.config.manager import ConfigManager
from contract_validator.core.comparator import Comparator
from contract_validator.core.executor import OllamaClient, ContractExecutor
from contract_validator.core.validator import ExtractionValidator
from contract_validator.data.loader import DataLoader
from contract_validator.data.generator import ContractGenerator
from contract_validator.output.exporter import ResultExporter
from contract_validator.output.formatter import ConsoleFormatter


@click.group()
def main():
    """Contract validation testing environment for internship contracts."""
    pass


@main.command()
@click.option(
    "--prompt",
    "-p",
    required=True,
    type=click.Path(exists=True),
    help="Path to extraction prompt file",
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
    default="test_data/dummy_contracts.json",
    type=click.Path(exists=True),
    help="Path to test dataset (default: test_data/dummy_contracts.json)",
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
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def test(prompt, system_prompt, dataset, config, output, format, verbose):
    """Run extraction validation on contracts using a prompt."""
    formatter = ConsoleFormatter()

    try:
        # Load configuration
        config_manager = ConfigManager(config)
        cfg = config_manager.load_config()

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

        # Load contracts
        formatter.console.print(f"Loading dataset from [cyan]{dataset}[/cyan]...")
        contracts = DataLoader.load_contracts(dataset)
        formatter.console.print(f"Loaded {len(contracts)} contracts")

        # Load prompts
        formatter.console.print(f"Loading prompt from [cyan]{prompt}[/cyan]...")
        prompt_path = Path(prompt)
        prompt_name = prompt_path.stem

        if system_prompt:
            prompt_config = DataLoader.create_prompt_config(
                name=prompt_name,
                version="1.0",
                system_prompt_path=system_prompt,
                user_prompt_path=prompt,
            )
        else:
            user_prompt_text = DataLoader.load_prompt(prompt)
            from contract_validator.data.schemas import PromptConfig
            prompt_config = PromptConfig(
                name=prompt_name,
                version="1.0",
                system_prompt="",
                user_prompt_template=user_prompt_text,
            )

        # Execute extraction
        executor = ContractExecutor(ollama_client)
        validator = ExtractionValidator()

        formatter.console.print(f"Running extraction on {len(contracts)} contracts...")

        with formatter.create_progress_bar() as progress:
            task = progress.add_task("Processing contracts...", total=len(contracts))
            results = []
            for i, contract in enumerate(contracts):
                result = executor.execute_single(contract, prompt_config)
                results.append(result)
                progress.update(task, advance=1)
                if verbose:
                    status = "✓" if result.extraction_successful else "✗"
                    formatter.console.print(
                        f"  [{i+1}/{len(contracts)}] {contract.id}: {status}"
                    )

        # Validate results
        report = validator.validate_results(
            results, contracts, prompt_name=prompt_name
        )

        # Display results
        formatter.print_extraction_report(report)

        # Export results
        exporter = ResultExporter(
            output_directory=cfg.output_directory,
            timestamp_format=cfg.timestamp_format,
        )

        if format == "json":
            json_path = exporter.export_json(report, output)
            formatter.console.print(f"Results saved to [cyan]{json_path}[/cyan]")
        elif format == "csv":
            csv_path = exporter.export_csv(results, output)
            formatter.console.print(f"Results saved to [cyan]{csv_path}[/cyan]")
        else:
            json_path, csv_path = exporter.export_both(report, results)
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
    default="test_data/dummy_contracts.json",
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
def compare(prompts, system_prompt, dataset, config, output):
    """Compare multiple extraction prompts side-by-side."""
    formatter = ConsoleFormatter()

    try:
        if len(prompts) < 2:
            formatter.console.print(
                "[bold red]Error:[/bold red] Need at least 2 prompts to compare"
            )
            sys.exit(1)

        # Load configuration
        config_manager = ConfigManager(config)
        cfg = config_manager.load_config()

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

        # Load contracts
        formatter.console.print(f"Loading dataset from [cyan]{dataset}[/cyan]...")
        contracts = DataLoader.load_contracts(dataset)
        formatter.console.print(f"Loaded {len(contracts)} contracts")

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
                from contract_validator.data.schemas import PromptConfig
                prompt_config = PromptConfig(
                    name=prompt_name,
                    version="1.0",
                    system_prompt="",
                    user_prompt_template=user_prompt_text,
                )

            prompt_configs.append(prompt_config)
            formatter.console.print(f"Loaded prompt: [cyan]{prompt_name}[/cyan]")

        # Run comparison
        executor = ContractExecutor(ollama_client)
        validator = ExtractionValidator()
        comparator = Comparator(executor, validator)

        formatter.console.print(
            f"Comparing {len(prompts)} prompts on {len(contracts)} contracts..."
        )

        with formatter.create_progress_bar() as progress:
            task = progress.add_task(
                "Running comparison...", total=len(prompts) * len(contracts)
            )
            comparison_report = comparator.compare_prompts(prompt_configs, contracts)
            progress.update(task, completed=len(prompts) * len(contracts))

        # Display results
        formatter.print_comparison_report(comparison_report)

        # Export results
        exporter = ResultExporter(
            output_directory=cfg.output_directory,
            timestamp_format=cfg.timestamp_format,
        )

        comparison_path = exporter.export_comparison(comparison_report, output)
        formatter.console.print(
            f"Comparison results saved to [cyan]{comparison_path}[/cyan]"
        )

    except Exception as e:
        formatter.console.print(f"[bold red]Error:[/bold red] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


@main.command()
@click.option(
    "--count",
    "-n",
    default=50,
    type=int,
    help="Number of contracts to generate (default: 50)",
)
@click.option(
    "--output",
    "-o",
    default="test_data/dummy_contracts.json",
    type=click.Path(),
    help="Output file path",
)
@click.option(
    "--seed",
    type=int,
    default=None,
    help="Random seed for reproducibility",
)
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def generate(count, output, seed, verbose):
    """Generate dummy contracts for testing."""
    formatter = ConsoleFormatter()

    try:
        formatter.console.print(f"Generating {count} dummy contracts...")

        generator = ContractGenerator(seed=seed)
        dataset = generator.generate_dataset(num_contracts=count)
        contracts = dataset.contracts

        # Save to file
        generator.save_dataset(dataset, output)

        formatter.console.print(f"[green]✓[/green] Generated {len(contracts)} contracts")
        formatter.console.print(f"Saved to [cyan]{output}[/cyan]")

        # Show distribution
        format_dist: dict = {}
        status_dist: dict = {}
        for c in contracts:
            format_dist[c.format.value] = format_dist.get(c.format.value, 0) + 1
            status_dist[c.ground_truth.expected_status.value] = (
                status_dist.get(c.ground_truth.expected_status.value, 0) + 1
            )

        formatter.console.print("\nFormat distribution:")
        for fmt, cnt in sorted(format_dist.items()):
            formatter.console.print(f"  • {fmt}: {cnt}")

        formatter.console.print("\nStatus distribution:")
        for status, cnt in sorted(status_dist.items()):
            formatter.console.print(f"  • {status}: {cnt}")

        if verbose:
            formatter.console.print("\nSample contracts:")
            for c in contracts[:3]:
                formatter.console.print(f"\n--- {c.id} ({c.format.value}) ---")
                formatter.console.print(c.text[:200] + "...")

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
    type=click.Choice(["console", "markdown"]),
    default="console",
    help="Output format (default: console)",
)
def report(result_file, format):
    """Generate formatted report from saved results."""
    formatter = ConsoleFormatter()

    try:
        import json
        with open(result_file, "r", encoding="utf-8") as f:
            result_data = json.load(f)

        formatter.console.print()
        formatter.console.rule("[bold blue]Extraction Test Report[/bold blue]")
        formatter.console.print()

        # Display key metrics
        if "overall_accuracy" in result_data:
            formatter.console.print(
                f"Overall Accuracy: [bold]{result_data['overall_accuracy']:.1%}[/bold]"
            )
        if "per_field_accuracy" in result_data:
            formatter.console.print("\nPer-Field Accuracy:")
            for field, acc in result_data["per_field_accuracy"].items():
                formatter.console.print(f"  • {field}: {acc:.1%}")

        formatter.console.print(f"\nFull results in: [cyan]{result_file}[/cyan]")

    except Exception as e:
        formatter.console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@main.command("generate-scanned-pdfs")
@click.option(
    "--dataset",
    "-d",
    default="test_data/dummy_contracts.json",
    type=click.Path(exists=True),
    help="Path to contract dataset JSON (default: test_data/dummy_contracts.json)",
)
@click.option(
    "--output-dir",
    "-o",
    default="test_data/scanned_pdfs",
    type=click.Path(),
    help="Directory to write scanned PDFs (default: test_data/scanned_pdfs)",
)
@click.option(
    "--severity",
    type=click.Choice(["low", "medium", "high", "mixed"]),
    default="mixed",
    show_default=True,
    help="Scan artifact severity. 'mixed' assigns each contract a random severity.",
)
@click.option(
    "--dpi",
    type=int,
    default=200,
    show_default=True,
    help="Render resolution in DPI (higher = better quality but slower)",
)
@click.option(
    "--seed",
    type=int,
    default=None,
    help="Random seed for reproducible artifact generation",
)
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def generate_scanned_pdfs(dataset, output_dir, severity, dpi, seed, verbose):
    """Render contracts as realistic scanned-document PDFs with image artifacts."""
    import random as _random
    from pathlib import Path as _Path

    from contract_validator.data.schemas import OcrSeverity
    from contract_validator.core.scan_renderer import render_scanned_pdf

    formatter = ConsoleFormatter()

    try:
        # Load contracts
        formatter.console.print(f"Loading dataset from [cyan]{dataset}[/cyan]...")
        contracts = DataLoader.load_contracts(dataset)
        formatter.console.print(f"Loaded {len(contracts)} contracts")

        if not contracts:
            formatter.console.print("[yellow]No contracts to process.[/yellow]")
            return

        # Prepare output directory
        out_dir = _Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        # Severity mapping
        _sev_map = {
            "low": OcrSeverity.LOW,
            "medium": OcrSeverity.MEDIUM,
            "high": OcrSeverity.HIGH,
        }
        _all_severities = list(OcrSeverity)
        rng = _random.Random(seed)

        formatter.console.print(
            f"Rendering {len(contracts)} scanned PDFs → [cyan]{out_dir}[/cyan]"
        )

        ok = 0
        failed = 0

        with formatter.create_progress_bar() as progress:
            task = progress.add_task("Rendering...", total=len(contracts))
            for contract in contracts:
                # Determine severity for this contract
                if severity == "mixed":
                    chosen_sev = rng.choice(_all_severities)
                else:
                    chosen_sev = _sev_map[severity]

                out_file = out_dir / f"{contract.id}_scanned.pdf"
                contract_seed = (seed or 0) + hash(contract.id) & 0xFFFFFF

                try:
                    render_scanned_pdf(
                        contract_text=contract.text,
                        output_path=out_file,
                        severity=chosen_sev,
                        dpi=dpi,
                        seed=contract_seed,
                    )
                    ok += 1
                    if verbose:
                        formatter.console.print(
                            f"  [green]✓[/green] {contract.id} "
                            f"({contract.format.value}, sev={chosen_sev.value}) → {out_file.name}"
                        )
                except Exception as exc:
                    failed += 1
                    formatter.console.print(
                        f"  [red]✗[/red] {contract.id}: {exc}"
                    )

                progress.update(task, advance=1)

        formatter.console.print(
            f"\n[green]✓[/green] {ok} scanned PDFs written to [cyan]{out_dir}[/cyan]"
        )
        if failed:
            formatter.console.print(f"[red]✗ {failed} contracts failed[/red]")

    except Exception as e:
        formatter.console.print(f"[bold red]Error:[/bold red] {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

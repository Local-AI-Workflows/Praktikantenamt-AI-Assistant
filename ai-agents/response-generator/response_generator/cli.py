"""
CLI interface for response generation tool.
"""

import sys
import json
from pathlib import Path

import click

from response_generator.config.manager import ConfigManager
from response_generator.core.generator import ResponseGenerator
from response_generator.core.personalizer import Personalizer
from response_generator.core.evaluator import ResponseEvaluator
from response_generator.core.comparator import TemplateComparator
from response_generator.data.loader import TemplateLoader, DataLoader
from response_generator.data.schemas import CategorizedEmail, ResponseTone
from response_generator.output.exporter import ResultExporter
from response_generator.output.formatter import ConsoleFormatter


@click.group()
def main():
    """Email response generation tool for internship office."""
    pass


@main.command()
@click.option(
    "--email",
    "-e",
    required=True,
    type=click.Path(exists=True),
    help="Path to email JSON file or dataset",
)
@click.option(
    "--tone",
    "-t",
    type=click.Choice(["formal", "informal", "both"]),
    default="both",
    help="Response tone (default: both)",
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
    help="Output file path (optional)",
)
@click.option(
    "--no-personalization",
    is_flag=True,
    help="Disable LLM personalization",
)
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def generate(email, tone, config, output, no_personalization, verbose):
    """Generate response suggestions for an email."""
    formatter = ConsoleFormatter()

    try:
        # Load configuration
        config_manager = ConfigManager(config)
        cfg = config_manager.load_config()

        # Override personalization if flag is set
        if no_personalization:
            cfg.personalization_enabled = False

        # Load templates
        template_loader = TemplateLoader()

        # Initialize personalizer (if enabled)
        personalizer = None
        if cfg.personalization_enabled:
            from response_generator.core.personalizer import OllamaClient
            ollama_client = OllamaClient(
                endpoint=cfg.ollama_endpoint,
                model=cfg.ollama_model,
                timeout=cfg.ollama_timeout,
            )
            if ollama_client.health_check():
                personalizer = Personalizer(ollama_client)
            else:
                formatter.console.print(
                    "[yellow]Warning:[/yellow] Ollama not available, "
                    "proceeding without personalization"
                )

        # Initialize generator
        generator = ResponseGenerator(
            template_loader=template_loader,
            personalizer=personalizer,
            config=cfg,
        )

        # Load email(s)
        formatter.console.print(f"Loading email from [cyan]{email}[/cyan]...")
        emails = DataLoader.load_emails(email)
        formatter.console.print(f"Loaded {len(emails)} email(s)")

        # Determine tones
        if tone == "both":
            tones = [ResponseTone.FORMAL, ResponseTone.INFORMAL]
        elif tone == "formal":
            tones = [ResponseTone.FORMAL]
        else:
            tones = [ResponseTone.INFORMAL]

        # Generate responses
        results = []
        with formatter.create_progress_bar() as progress:
            task = progress.add_task("Generating responses...", total=len(emails))

            for email_obj in emails:
                suggestion = generator.generate_response(email_obj, tones)
                results.append(suggestion)
                progress.update(task, advance=1)

                if verbose:
                    formatter.console.print(
                        f"  {email_obj.id}: Generated {len(suggestion.responses)} response(s)"
                    )

        # Display results
        for suggestion in results:
            formatter.print_response_suggestion(suggestion)

        # Export if output specified
        if output:
            exporter = ResultExporter(
                output_directory=cfg.output_directory,
                timestamp_format=cfg.timestamp_format,
            )
            output_path = exporter.export_suggestions(results, output)
            formatter.console.print(f"Results saved to [cyan]{output_path}[/cyan]")

        # Print n8n output format
        if verbose:
            formatter.console.print("\n[bold]n8n Output Format:[/bold]")
            for suggestion in results:
                formatter.console.print(json.dumps(suggestion.to_n8n_output(), indent=2))

    except Exception as e:
        formatter.console.print(f"[bold red]Error:[/bold red] {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@main.command()
@click.option(
    "--templates",
    "-t",
    default="templates",
    type=click.Path(exists=True),
    help="Path to templates directory",
)
@click.option(
    "--dataset",
    "-d",
    required=True,
    type=click.Path(exists=True),
    help="Path to test dataset with expected responses",
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
    help="Output file path (optional)",
)
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def evaluate(templates, dataset, config, output, verbose):
    """Evaluate response quality against expected responses."""
    formatter = ConsoleFormatter()

    try:
        # Load configuration
        config_manager = ConfigManager(config)
        cfg = config_manager.load_config()

        # Load templates and emails
        template_loader = TemplateLoader(templates)
        emails = DataLoader.load_emails_with_expected(dataset)

        formatter.console.print(f"Loaded {len(emails)} test emails")

        # Initialize components
        generator = ResponseGenerator(
            template_loader=template_loader,
            personalizer=None,  # No personalization for evaluation
            config=cfg,
        )
        evaluator = ResponseEvaluator()

        # Generate and evaluate
        results = []
        with formatter.create_progress_bar() as progress:
            task = progress.add_task("Evaluating responses...", total=len(emails))

            for email_data in emails:
                email_obj = email_data["email"]
                expected = email_data.get("expected_response")

                suggestion = generator.generate_response(
                    email_obj, [ResponseTone.FORMAL, ResponseTone.INFORMAL]
                )

                for response in suggestion.responses:
                    eval_result = evaluator.evaluate_response(
                        email_obj, response, expected
                    )
                    results.append(eval_result)

                progress.update(task, advance=1)

        # Generate report
        report = evaluator.generate_report(results)

        # Display results
        formatter.print_evaluation_report(report)

        # Export results
        if output:
            exporter = ResultExporter(
                output_directory=cfg.output_directory,
                timestamp_format=cfg.timestamp_format,
            )
            output_path = exporter.export_evaluation(report, output)
            formatter.console.print(f"Results saved to [cyan]{output_path}[/cyan]")

    except Exception as e:
        formatter.console.print(f"[bold red]Error:[/bold red] {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@main.command()
@click.option(
    "--templates",
    "-t",
    required=True,
    multiple=True,
    type=click.Path(exists=True),
    help="Paths to template directories to compare",
)
@click.option(
    "--dataset",
    "-d",
    required=True,
    type=click.Path(exists=True),
    help="Path to test dataset",
)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Path to config file (optional)",
)
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def compare(templates, dataset, config, output):
    """Compare multiple template sets."""
    formatter = ConsoleFormatter()

    try:
        if len(templates) < 2:
            formatter.console.print(
                "[bold red]Error:[/bold red] Need at least 2 template sets to compare"
            )
            sys.exit(1)

        # Load configuration
        config_manager = ConfigManager(config)
        cfg = config_manager.load_config()

        # Load emails
        emails = DataLoader.load_emails(dataset)
        formatter.console.print(f"Loaded {len(emails)} test emails")

        # Compare templates
        comparator = TemplateComparator()
        comparison_report = comparator.compare_templates(
            list(templates), emails, cfg
        )

        # Display results
        formatter.print_comparison_report(comparison_report)

        # Export results
        if output:
            exporter = ResultExporter(
                output_directory=cfg.output_directory,
                timestamp_format=cfg.timestamp_format,
            )
            output_path = exporter.export_comparison(comparison_report, output)
            formatter.console.print(f"Results saved to [cyan]{output_path}[/cyan]")

    except Exception as e:
        formatter.console.print(f"[bold red]Error:[/bold red] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


@main.command("list-templates")
@click.option(
    "--templates",
    "-t",
    default="templates",
    type=click.Path(exists=True),
    help="Path to templates directory",
)
def list_templates(templates):
    """List all available response templates."""
    formatter = ConsoleFormatter()

    try:
        template_loader = TemplateLoader(templates)
        template_info = template_loader.list_templates()

        formatter.console.print()
        formatter.console.rule("[bold blue]Available Templates[/bold blue]")
        formatter.console.print()

        for category, tones in template_info.items():
            formatter.console.print(f"[bold]{category}[/bold]")
            for tone, path in tones.items():
                formatter.console.print(f"  • {tone}: [cyan]{path}[/cyan]")
            formatter.console.print()

        total = sum(len(tones) for tones in template_info.values())
        formatter.console.print(f"Total templates: [bold]{total}[/bold]")

    except Exception as e:
        formatter.console.print(f"[bold red]Error:[/bold red] {e}")
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
        with open(result_file, "r", encoding="utf-8") as f:
            result_data = json.load(f)

        formatter.console.print()
        formatter.console.rule("[bold blue]Response Generation Report[/bold blue]")
        formatter.console.print()

        # Display key metrics
        if "average_confidence" in result_data:
            formatter.console.print(
                f"Average Confidence: [bold]{result_data['average_confidence']:.1%}[/bold]"
            )
        if "average_quality" in result_data:
            formatter.console.print(
                f"Average Quality: [bold]{result_data['average_quality']:.1%}[/bold]"
            )
        if "pass_rate" in result_data:
            formatter.console.print(
                f"Pass Rate: [bold]{result_data['pass_rate']:.1%}[/bold]"
            )

        formatter.console.print(f"\nFull results in: [cyan]{result_file}[/cyan]")

    except Exception as e:
        formatter.console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

"""
CLI for n8n email workflow validation.
"""

import sys
import time
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console

# Add categorization module to path for imports
categorization_path = Path(__file__).parent.parent.parent / "categorization"
sys.path.insert(0, str(categorization_path))

from workflow_validator.config.manager import ConfigManager
from workflow_validator.core.sender import EmailSender
from workflow_validator.core.uuid_tracker import UUIDTracker
from workflow_validator.core.validator import WorkflowValidator
from workflow_validator.data.loader import DataLoader
from workflow_validator.data.schemas import EmailLocation
from workflow_validator.email.imap_client import IMAPClient
from workflow_validator.email.smtp_client import SMTPClient
from workflow_validator.output.exporter import ResultExporter
from workflow_validator.output.formatter import ConsoleFormatter


@click.group()
def main():
    """n8n Email Workflow Validator - Test email categorization workflows."""
    pass


@main.command()
@click.option(
    "--dataset",
    "-d",
    default="../categorization/test_data/dummy_emails.json",
    help="Path to test email dataset",
)
@click.option(
    "--config", "-c", type=click.Path(exists=True), help="Path to config file (optional)"
)
@click.option(
    "--wait-time",
    "-w",
    type=int,
    help="Seconds to wait for n8n processing (overrides config)",
)
@click.option("--no-cleanup", is_flag=True, help="Skip cleanup of test emails")
@click.option("--test-inbox", required=True, help="Target test inbox email address")
@click.option("--verbose", "-v", is_flag=True, help="Detailed output")
def validate(dataset, config, wait_time, no_cleanup, test_inbox, verbose):
    """
    Run full workflow validation: send emails, wait, validate routing.

    Example:
        workflow-validator validate --test-inbox test@example.com
    """
    console = Console()

    try:
        # 1. Load configuration
        if verbose:
            console.print("[dim]Loading configuration...[/dim]")
        config_manager = ConfigManager(config)
        cfg = config_manager.load_config()

        # Override settings from CLI
        if wait_time:
            cfg.wait_time_seconds = wait_time
        if no_cleanup:
            cfg.cleanup_after_test = False

        # 2. Health checks
        console.print("[bold]Running health checks...[/bold]")
        smtp_client = SMTPClient(cfg.smtp)
        imap_client = IMAPClient(cfg.imap)

        if not smtp_client.health_check():
            console.print("[red]✗ SMTP server not accessible[/red]")
            console.print(
                f"  Host: {cfg.smtp.host}:{cfg.smtp.port}, User: {cfg.smtp.username}"
            )
            return
        console.print(f"[green]✓ SMTP server accessible[/green] ({cfg.smtp.host})")

        if not imap_client.health_check():
            console.print("[red]✗ IMAP server not accessible[/red]")
            console.print(
                f"  Host: {cfg.imap.host}:{cfg.imap.port}, User: {cfg.imap.username}"
            )
            return
        console.print(f"[green]✓ IMAP server accessible[/green] ({cfg.imap.host})")
        console.print()

        # 3. Load test emails
        console.print(f"[dim]Loading dataset from {dataset}...[/dim]")
        emails = DataLoader.load_emails(dataset)
        console.print(f"Loaded [cyan]{len(emails)}[/cyan] test emails\n")

        # 4. Send test emails
        console.print("[bold cyan]Phase 1: Sending test emails[/bold cyan]")
        uuid_tracker = UUIDTracker(cfg.uuid_storage_path)
        sender = EmailSender(smtp_client, uuid_tracker)

        with console.status("[bold green]Sending emails..."):
            sent_emails = sender.send_batch(emails, test_inbox, verbose=verbose)

        console.print(
            f"[green]✓ Sent {len(sent_emails)}/{len(emails)} emails[/green]\n"
        )

        if len(sent_emails) == 0:
            console.print("[red]No emails sent successfully. Aborting.[/red]")
            return

        # 5. Wait for n8n processing
        console.print(
            f"[bold cyan]Phase 2: Waiting {cfg.wait_time_seconds}s for n8n processing[/bold cyan]"
        )
        for i in range(cfg.wait_time_seconds):
            console.print(
                f"  Waiting... {i+1}/{cfg.wait_time_seconds}s", end="\r"
            )
            time.sleep(1)
        console.print(f"  [green]✓ Wait complete{' ' * 30}[/green]\n")

        # 6. Validate email routing
        console.print("[bold cyan]Phase 3: Validating email routing[/bold cyan]")
        imap_client.connect()

        # Get list of folders
        folders = imap_client.list_folders()
        if verbose:
            console.print(f"  Found {len(folders)} IMAP folders:")
            for folder in folders:
                console.print(f"    • {folder}")

        # Find each email and check location
        email_locations = []

        with console.status("[bold green]Searching for emails..."):
            for i, ewu in enumerate(sent_emails, 1):
                if verbose:
                    console.print(
                        f"  Searching for {ewu.original_email.id} ({i}/{len(sent_emails)})..."
                    )

                folder = imap_client.find_email_location(ewu.uuid, folders)

                if folder:
                    # Map folder to category
                    validator = WorkflowValidator(cfg.categories, cfg.folder_mappings)
                    predicted_category = validator.map_folder_to_category(folder)

                    location = EmailLocation(
                        uuid=ewu.uuid,
                        email_id=ewu.original_email.id,
                        found_in_folder=folder,
                        expected_category=ewu.original_email.expected_category,
                        predicted_category=predicted_category,
                        is_correct=(
                            predicted_category == ewu.original_email.expected_category
                        ),
                        validation_timestamp=datetime.now(),
                    )
                    email_locations.append(location)

                    if verbose:
                        status = "✓" if location.is_correct else "✗"
                        console.print(
                            f"    [{status}] Found in {folder} -> {predicted_category}"
                        )
                else:
                    # Email not found
                    location = EmailLocation(
                        uuid=ewu.uuid,
                        email_id=ewu.original_email.id,
                        found_in_folder=None,
                        expected_category=ewu.original_email.expected_category,
                        predicted_category=None,
                        is_correct=False,
                        validation_timestamp=datetime.now(),
                    )
                    email_locations.append(location)

                    if verbose:
                        console.print("    [✗] Not found")

        imap_client.disconnect()

        found_count = len([el for el in email_locations if el.found_in_folder])
        console.print(
            f"[green]✓ Found {found_count}/{len(sent_emails)} emails[/green]"
        )

        not_found_count = len(sent_emails) - found_count
        if not_found_count > 0:
            console.print(f"[yellow]⚠ {not_found_count} emails not found[/yellow]")
        console.print()

        # 7. Generate validation report
        validator = WorkflowValidator(cfg.categories, cfg.folder_mappings)
        report = validator.validate_email_locations(
            email_locations=email_locations,
            folder_mappings=cfg.folder_mappings,
            wait_time=cfg.wait_time_seconds,
            total_sent=len(sent_emails),
        )

        # 8. Display results
        formatter = ConsoleFormatter()
        formatter.print_workflow_validation_report(report)

        # 9. Export results
        exporter = ResultExporter(cfg.output_directory, cfg.timestamp_format)
        json_path, csv_path = exporter.export_workflow_validation(
            report, cfg.output_format
        )

        console.print("Results saved to:")
        if json_path:
            console.print(f"  • JSON: [cyan]{json_path}[/cyan]")
        if csv_path:
            console.print(f"  • CSV: [cyan]{csv_path}[/cyan]")
        console.print()

        # 10. Cleanup (optional)
        if cfg.cleanup_after_test:
            console.print("[bold cyan]Phase 4: Cleaning up test emails[/bold cyan]")
            imap_client.connect()

            with console.status("[bold yellow]Deleting emails..."):
                deleted = imap_client.delete_emails_by_uuid(
                    [ewu.uuid for ewu in sent_emails]
                )

            imap_client.disconnect()
            console.print(f"[green]✓ Deleted {deleted} test emails[/green]")

    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except ValueError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        sys.exit(1)
    except ConnectionError as e:
        console.print(f"[red]Connection error: {e}[/red]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


@main.command()
@click.option(
    "--config", "-c", type=click.Path(exists=True), help="Path to config file (optional)"
)
def check_connection(config):
    """Test IMAP and SMTP connections."""
    console = Console()

    try:
        console.print("[bold]Testing connections...[/bold]\n")

        # Load config
        config_manager = ConfigManager(config)
        cfg = config_manager.load_config()

        # Test SMTP
        console.print(f"SMTP: {cfg.smtp.host}:{cfg.smtp.port}")
        smtp_client = SMTPClient(cfg.smtp)
        if smtp_client.health_check():
            console.print("[green]✓ SMTP connection successful[/green]\n")
        else:
            console.print("[red]✗ SMTP connection failed[/red]\n")

        # Test IMAP
        console.print(f"IMAP: {cfg.imap.host}:{cfg.imap.port}")
        imap_client = IMAPClient(cfg.imap)
        if imap_client.health_check():
            console.print("[green]✓ IMAP connection successful[/green]\n")
        else:
            console.print("[red]✗ IMAP connection failed[/red]\n")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@main.command()
@click.argument("uuid", type=str)
@click.option(
    "--config", "-c", type=click.Path(exists=True), help="Path to config file (optional)"
)
def find_email(uuid, config):
    """Find a specific test email by UUID."""
    console = Console()

    try:
        from uuid import UUID as UUIDType

        email_uuid = UUIDType(uuid)

        console.print(f"[bold]Searching for email with UUID: {uuid}[/bold]\n")

        # Load config
        config_manager = ConfigManager(config)
        cfg = config_manager.load_config()

        # Connect to IMAP
        imap_client = IMAPClient(cfg.imap)
        imap_client.connect()

        # Get folders
        folders = imap_client.list_folders()
        console.print(f"Searching {len(folders)} folders...\n")

        # Search
        folder = imap_client.find_email_location(email_uuid, folders)

        if folder:
            console.print(f"[green]✓ Email found in: {folder}[/green]")
        else:
            console.print("[yellow]Email not found[/yellow]")

        imap_client.disconnect()

    except ValueError:
        console.print("[red]Invalid UUID format[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()

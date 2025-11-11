"""Docmost to Outline migration CLI."""

import sys
from pathlib import Path

import click
from rich.console import Console

from migrator.orchestrator import MigrationOrchestrator
from migrator.outline_client import OutlineClient
from utils.validators import ValidationError

# Default max file size: 25MB
DEFAULT_MAX_FILE_SIZE_MB = 25


@click.command()
@click.option(
    "--zip",
    "zip_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to Docmost export ZIP file",
)
@click.option(
    "--outline-url",
    required=True,
    help="Outline instance URL (e.g., https://outline.example.com)",
)
@click.option("--api-key", required=True, help="Outline API key")
@click.option(
    "--collection-id",
    default=None,
    help="Existing collection ID (creates new if not provided)",
)
@click.option(
    "--max-file-size",
    default=DEFAULT_MAX_FILE_SIZE_MB,
    type=int,
    help=f"Maximum file size in MB (default: {DEFAULT_MAX_FILE_SIZE_MB}MB)",
)
def main(
    zip_path: Path,
    outline_url: str,
    api_key: str,
    collection_id: str | None,
    max_file_size: int,
):
    """Migrate Docmost export to Outline.

    This tool migrates a Docmost ZIP export to an Outline instance,
    preserving document hierarchy, attachments, and formatting.
    """
    console = Console()

    try:
        # Convert MB to bytes
        max_size_bytes = max_file_size * 1024 * 1024

        # Display configuration
        console.print(
            "\n[bold cyan]Docmost → Outline Migration Tool[/bold cyan]\n"
        )
        console.print(f"ZIP file: {zip_path}")
        console.print(f"Outline URL: {outline_url}")
        console.print(f"Max file size: {max_file_size}MB")
        if collection_id:
            console.print(f"Target collection: {collection_id}")
        else:
            console.print("Target collection: [italic]Will create new[/italic]")
        console.print()

        # Confirm before proceeding
        if not click.confirm("Proceed with migration?", default=True):
            console.print("[yellow]Migration cancelled.[/yellow]")
            sys.exit(0)

        # Initialize Outline client
        console.print("\n[yellow]Connecting to Outline...[/yellow]")
        with OutlineClient(outline_url, api_key) as client:
            # Test connection
            auth_info = client.test_connection()
            user_name = (
                auth_info.get("data", {}).get("user", {}).get("name", "Unknown")
            )
            console.print(f"  ✓ Connected as: {user_name}\n")

            # Initialize orchestrator
            orchestrator = MigrationOrchestrator(
                outline_client=client,
                max_file_size=max_size_bytes,
                console=console,
            )

            # Run migration
            collection_id, stats = orchestrator.migrate(
                zip_path=str(zip_path), collection_id=collection_id
            )

        console.print(
            "\n[bold green]🎉 Migration completed successfully![/bold green]"
        )
        sys.exit(0)

    except ValidationError as e:
        console.print(f"\n[bold red]✗ Validation Error:[/bold red] {e}")
        sys.exit(1)

    except Exception as e:
        console.print(f"\n[bold red]✗ Migration Failed:[/bold red] {e}")
        if "--debug" in sys.argv:
            raise
        sys.exit(1)


if __name__ == "__main__":
    main()

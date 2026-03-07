"""Main CLI entry point for SignalSift."""

import click
from rich.console import Console

from signalsift import __version__
from signalsift.cli.cache import cache
from signalsift.cli.keywords import keywords
from signalsift.cli.report import report
from signalsift.cli.scan import scan
from signalsift.cli.sources import sources
from signalsift.cli.status import status
from signalsift.database.connection import database_exists, initialize_database
from signalsift.utils.logging import setup_logging

console = Console()


@click.group()
@click.version_option(__version__, prog_name="signalsift")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """
    SignalSift - Personal community intelligence tool.

    Monitor Reddit, YouTube, and Hacker News for topics you care about.
    Generates markdown reports for review and analysis.
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose

    # Set up logging
    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(level=log_level)

    # Initialize database if needed
    if not database_exists():
        console.print("[dim]Initializing database...[/dim]")
        initialize_database(populate_defaults=True)
        console.print("[green]✓[/green] Database initialized with default sources and keywords")


@cli.command()
@click.pass_context
def init(ctx: click.Context) -> None:
    """Initialize or reinitialize the database with defaults."""
    from signalsift.database.connection import reset_database

    if database_exists():
        if not click.confirm("Database already exists. This will reset all data. Continue?"):
            console.print("[yellow]Cancelled.[/yellow]")
            return

        reset_database()
        console.print("[green]✓[/green] Database reset with default configuration")
    else:
        initialize_database(populate_defaults=True)
        console.print("[green]✓[/green] Database initialized with default sources and keywords")


@cli.command()
@click.option("--check", is_flag=True, help="Show migration status only")
@click.option("--version", "target_version", type=int, help="Migrate to specific version")
@click.pass_context
def migrate(ctx: click.Context, check: bool, target_version: int | None) -> None:
    """Run database migrations."""
    from signalsift.database.migrations import (
        get_pending_migrations,
        migration_status,
    )
    from signalsift.database.migrations import (
        migrate as run_migrate,
    )

    if check:
        info = migration_status()
        console.print(f"Current version: [cyan]{info['current_version']}[/cyan]")
        console.print(f"Latest version:  [cyan]{info['latest_version']}[/cyan]")
        console.print(f"Applied:         [green]{info['applied']}[/green]")
        console.print(f"Pending:         [yellow]{info['pending']}[/yellow]")

        pending = get_pending_migrations()
        if pending:
            console.print("\n[bold]Pending migrations:[/bold]")
            for m in pending:
                console.print(f"  v{m.version}: {m.name}")
        return

    count = run_migrate(target_version=target_version)
    if count > 0:
        console.print(f"[green]✓[/green] Applied {count} migration(s)")
    else:
        console.print("[dim]Database is up to date[/dim]")


# Register command groups
cli.add_command(scan)
cli.add_command(report)
cli.add_command(status)
cli.add_command(sources)
cli.add_command(keywords)
cli.add_command(cache)
cli.add_command(migrate)


if __name__ == "__main__":
    cli()

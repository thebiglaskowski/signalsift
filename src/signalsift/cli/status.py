"""Status command for displaying cache statistics."""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from signalsift.database.queries import get_cache_stats, get_latest_report
from signalsift.utils.formatting import format_file_size, format_relative_time

console = Console()


@click.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show cache and configuration status."""
    from signalsift.config import get_settings

    settings = get_settings()
    stats = get_cache_stats()
    latest_report = get_latest_report()

    # Header
    console.print()
    console.print(Panel.fit("[bold]SignalSift Status[/bold]", border_style="blue"))
    console.print()

    # Database info
    db_path = settings.database.path
    db_size = db_path.stat().st_size if db_path.exists() else 0

    console.print(f"[bold]Database:[/bold] {db_path}")
    console.print(f"[dim]Size: {format_file_size(db_size)}[/dim]")
    console.print()

    # Reddit stats table
    reddit_table = Table(title="Reddit Threads", show_header=True, header_style="bold cyan")
    reddit_table.add_column("Metric", style="dim")
    reddit_table.add_column("Value", justify="right")

    reddit_table.add_row("Total", str(stats["reddit_total"]))
    reddit_table.add_row("Unprocessed", str(stats["reddit_unprocessed"]))
    reddit_table.add_row(
        "Last scan",
        (
            format_relative_time(stats["reddit_last_scan"].timestamp())
            if stats["reddit_last_scan"]
            else "Never"
        ),
    )

    console.print(reddit_table)
    console.print()

    # YouTube stats table
    youtube_table = Table(title="YouTube Videos", show_header=True, header_style="bold cyan")
    youtube_table.add_column("Metric", style="dim")
    youtube_table.add_column("Value", justify="right")

    youtube_table.add_row("Total", str(stats["youtube_total"]))
    youtube_table.add_row("Unprocessed", str(stats["youtube_unprocessed"]))
    youtube_table.add_row(
        "Last scan",
        (
            format_relative_time(stats["youtube_last_scan"].timestamp())
            if stats["youtube_last_scan"]
            else "Never"
        ),
    )

    console.print(youtube_table)
    console.print()

    # Sources table
    sources_table = Table(title="Sources Configured", show_header=True, header_style="bold cyan")
    sources_table.add_column("Type", style="dim")
    sources_table.add_column("Total", justify="right")
    sources_table.add_column("Enabled", justify="right")

    sources_table.add_row(
        "Reddit",
        str(stats["reddit_sources"]),
        str(stats["reddit_sources_enabled"]),
    )
    sources_table.add_row(
        "YouTube",
        str(stats["youtube_sources"]),
        str(stats["youtube_sources_enabled"]),
    )

    console.print(sources_table)
    console.print()

    # Report info
    console.print(f"[bold]Reports Generated:[/bold] {stats['reports_total']}")
    if latest_report:
        console.print(
            f"[bold]Last Report:[/bold] {stats['last_report_date'].strftime('%Y-%m-%d')} "
            f"({stats['last_report_path']})"
        )
    else:
        console.print("[dim]No reports generated yet[/dim]")

    # Credentials status
    console.print()
    console.print("[bold]API Credentials:[/bold]")

    if settings.has_reddit_credentials():
        console.print("  [green]✓[/green] Reddit credentials configured")
    else:
        console.print("  [yellow]✗[/yellow] Reddit credentials not configured")

    if settings.has_youtube_credentials():
        console.print("  [green]✓[/green] YouTube API key configured")
    else:
        console.print("  [yellow]✗[/yellow] YouTube API key not configured")

    console.print()

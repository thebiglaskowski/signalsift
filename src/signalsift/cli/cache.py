"""Cache management commands."""

import json
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from signalsift.database.queries import (
    clear_all_content,
    export_cache_to_json,
    get_cache_stats,
    prune_old_content,
    reset_processed_flags,
)
from signalsift.utils.formatting import format_file_size

console = Console()


@click.group()
def cache() -> None:
    """Cache management utilities."""
    pass


@cache.command("stats")
def cache_stats() -> None:
    """Show detailed cache statistics."""
    from signalsift.config import get_settings

    settings = get_settings()
    stats = get_cache_stats()

    db_path = settings.database.path
    db_size = db_path.stat().st_size if db_path.exists() else 0

    table = Table(title="Cache Statistics", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="dim")
    table.add_column("Value", justify="right")

    table.add_row("Database path", str(db_path))
    table.add_row("Database size", format_file_size(db_size))
    table.add_row("", "")
    table.add_row("Reddit threads (total)", str(stats["reddit_total"]))
    table.add_row("Reddit threads (unprocessed)", str(stats["reddit_unprocessed"]))
    table.add_row("", "")
    table.add_row("YouTube videos (total)", str(stats["youtube_total"]))
    table.add_row("YouTube videos (unprocessed)", str(stats["youtube_unprocessed"]))
    table.add_row("", "")
    table.add_row("Reports generated", str(stats["reports_total"]))

    console.print(table)


@cache.command("prune")
@click.option(
    "--older-than",
    type=int,
    required=True,
    help="Delete processed content older than N days",
)
@click.option("--force", is_flag=True, help="Skip confirmation")
def prune_cache(older_than: int, force: bool) -> None:
    """Delete old processed content from cache."""
    if not force and not click.confirm(
        f"Delete all processed content older than {older_than} days?"
    ):
        console.print("[yellow]Cancelled.[/yellow]")
        return

    reddit_deleted, youtube_deleted = prune_old_content(older_than)

    console.print(
        f"[green]✓[/green] Pruned {reddit_deleted} Reddit threads "
        f"and {youtube_deleted} YouTube videos"
    )


@cache.command("reset-processed")
@click.option("--force", is_flag=True, help="Skip confirmation")
def reset_processed(force: bool) -> None:
    """Reset processed flags on all content (allows reuse in new reports)."""
    if not force and not click.confirm("Reset processed flags on all content?"):
        console.print("[yellow]Cancelled.[/yellow]")
        return

    count = reset_processed_flags()
    console.print(f"[green]✓[/green] Reset processed flag on {count} items")


@cache.command("export")
@click.argument("output_path", type=click.Path(path_type=Path))
def export_cache(output_path: Path) -> None:
    """Export cache to JSON file."""
    data = export_cache_to_json()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    console.print(f"[green]✓[/green] Cache exported to: {output_path}")


@cache.command("clear")
@click.option("--confirm", "confirmed", is_flag=True, help="Confirm deletion")
def clear_cache(confirmed: bool) -> None:
    """Clear all cached content (destructive!)."""
    if not confirmed:
        console.print("[red]This will delete ALL cached content.[/red]")
        console.print("Run with --confirm to proceed.")
        return

    if not click.confirm("Are you SURE you want to delete all cached content?"):
        console.print("[yellow]Cancelled.[/yellow]")
        return

    reddit_deleted, youtube_deleted = clear_all_content()

    console.print(
        f"[green]✓[/green] Cleared {reddit_deleted} Reddit threads "
        f"and {youtube_deleted} YouTube videos"
    )

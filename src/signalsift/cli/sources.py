"""Sources management commands."""

import click
from rich.console import Console
from rich.table import Table

from signalsift.database.models import Source
from signalsift.database.queries import (
    add_source,
    get_all_sources,
    remove_source,
    toggle_source,
)

console = Console()


@click.group()
def sources() -> None:
    """Manage content sources (subreddits and YouTube channels)."""
    pass


@sources.command("list")
@click.option("--all", "show_all", is_flag=True, help="Show disabled sources too")
def list_sources(show_all: bool) -> None:
    """List all configured sources."""
    all_sources = get_all_sources(enabled_only=not show_all)

    if not all_sources:
        console.print("[dim]No sources configured.[/dim]")
        return

    # Reddit sources
    reddit_sources = [s for s in all_sources if s.source_type == "reddit"]
    if reddit_sources:
        table = Table(title="Reddit Subreddits", show_header=True, header_style="bold cyan")
        table.add_column("Subreddit", style="bold")
        table.add_column("Tier", justify="center")
        table.add_column("Status", justify="center")
        table.add_column("Last Fetched")

        for source in reddit_sources:
            status = "[green]✓[/green]" if source.enabled else "[red]✗[/red]"
            last_fetched = (
                source.last_fetched_datetime.strftime("%Y-%m-%d %H:%M")
                if source.last_fetched_datetime
                else "[dim]Never[/dim]"
            )
            table.add_row(
                f"r/{source.source_id}",
                str(source.tier),
                status,
                last_fetched,
            )

        console.print(table)
        console.print()

    # YouTube sources
    youtube_sources = [s for s in all_sources if s.source_type == "youtube"]
    if youtube_sources:
        table = Table(title="YouTube Channels", show_header=True, header_style="bold cyan")
        table.add_column("Channel", style="bold")
        table.add_column("ID", style="dim")
        table.add_column("Tier", justify="center")
        table.add_column("Status", justify="center")
        table.add_column("Last Fetched")

        for source in youtube_sources:
            status = "[green]✓[/green]" if source.enabled else "[red]✗[/red]"
            last_fetched = (
                source.last_fetched_datetime.strftime("%Y-%m-%d %H:%M")
                if source.last_fetched_datetime
                else "[dim]Never[/dim]"
            )
            table.add_row(
                source.display_name or source.source_id,
                source.source_id[:15] + "..." if len(source.source_id) > 15 else source.source_id,
                str(source.tier),
                status,
                last_fetched,
            )

        console.print(table)


def _normalize_youtube_id(source_id: str) -> str:
    """Normalize a YouTube channel URL or handle to a storable identifier.

    Accepts:
    - https://www.youtube.com/@handle
    - https://www.youtube.com/channel/UCxxx
    - @handle
    - UCxxx (channel ID — returned as-is)
    """
    import re

    # Full URL with handle: https://www.youtube.com/@handle
    handle_url = re.match(r"https?://(?:www\.)?youtube\.com/@([\w.-]+)", source_id)
    if handle_url:
        return f"@{handle_url.group(1)}"

    # Full URL with channel ID: https://www.youtube.com/channel/UCxxx
    channel_url = re.match(r"https?://(?:www\.)?youtube\.com/channel/(UC[\w-]+)", source_id)
    if channel_url:
        return channel_url.group(1)

    # Already a handle or channel ID — return as-is
    return source_id


@sources.command("add")
@click.argument("source_type", type=click.Choice(["reddit", "youtube"]))
@click.argument("source_id")
@click.option("--name", help="Display name for the source")
@click.option("--tier", type=int, default=2, help="Priority tier (1=high, 2=medium, 3=low)")
def add_source_cmd(source_type: str, source_id: str, name: str | None, tier: int) -> None:
    """Add a new source.

    SOURCE_TYPE: 'reddit' or 'youtube'
    SOURCE_ID: Subreddit name, YouTube channel ID, @handle, or channel URL
    """
    if source_type == "youtube":
        source_id = _normalize_youtube_id(source_id)

    # Set default display name
    if name is None:
        if source_type == "reddit":
            name = f"r/{source_id}"
        else:
            name = source_id

    source = Source(
        source_type=source_type,
        source_id=source_id,
        display_name=name,
        tier=tier,
        enabled=True,
    )

    add_source(source)
    console.print(f"[green]✓[/green] Added {source_type} source: {name}")


@sources.command("enable")
@click.argument("source_type", type=click.Choice(["reddit", "youtube"]))
@click.argument("source_id")
def enable_source(source_type: str, source_id: str) -> None:
    """Enable a source."""
    toggle_source(source_type, source_id, enabled=True)
    console.print(f"[green]✓[/green] Enabled {source_type} source: {source_id}")


@sources.command("disable")
@click.argument("source_type", type=click.Choice(["reddit", "youtube"]))
@click.argument("source_id")
def disable_source(source_type: str, source_id: str) -> None:
    """Disable a source."""
    toggle_source(source_type, source_id, enabled=False)
    console.print(f"[yellow]✓[/yellow] Disabled {source_type} source: {source_id}")


@sources.command("remove")
@click.argument("source_type", type=click.Choice(["reddit", "youtube"]))
@click.argument("source_id")
@click.option("--force", is_flag=True, help="Skip confirmation")
def remove_source_cmd(source_type: str, source_id: str, force: bool) -> None:
    """Remove a source."""
    if not force:
        if not click.confirm(f"Remove {source_type} source '{source_id}'?"):
            console.print("[yellow]Cancelled.[/yellow]")
            return

    if remove_source(source_type, source_id):
        console.print(f"[green]✓[/green] Removed {source_type} source: {source_id}")
    else:
        console.print(f"[red]✗[/red] Source not found: {source_id}")

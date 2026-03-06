"""Scan command for fetching content from sources."""

from datetime import datetime, timedelta

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from signalsift.config import get_settings
from signalsift.database.models import HackerNewsItem
from signalsift.database.queries import (
    insert_reddit_threads_batch,
    insert_youtube_videos_batch,
)
from signalsift.exceptions import RedditError, YouTubeError
from signalsift.processing.scoring import (
    process_hackernews_item,
    process_reddit_thread,
    process_youtube_video,
)
from signalsift.sources.reddit import RedditSource
from signalsift.sources.reddit_rss import RedditRSSSource
from signalsift.sources.youtube import YouTubeSource
from signalsift.utils.logging import get_logger

console = Console()
logger = get_logger(__name__)


@click.command()
@click.option("--reddit-only", is_flag=True, help="Only scan Reddit sources")
@click.option("--youtube-only", is_flag=True, help="Only scan YouTube sources")
@click.option("--hackernews-only", is_flag=True, help="Only scan Hacker News")
@click.option(
    "--subreddits",
    help="Comma-separated list of specific subreddits to scan",
)
@click.option(
    "--channels",
    help="Comma-separated list of specific channel IDs to scan",
)
@click.option(
    "--days",
    type=int,
    default=None,
    help="Only fetch content from the last N days",
)
@click.option(
    "--limit",
    type=int,
    default=None,
    help="Maximum items to fetch per source",
)
@click.option("--dry-run", is_flag=True, help="Show what would be fetched without saving")
@click.option(
    "--track-competitive",
    is_flag=True,
    default=True,
    help="Track competitive tool mentions (default: enabled)",
)
@click.pass_context
def scan(
    ctx: click.Context,
    reddit_only: bool,
    youtube_only: bool,
    hackernews_only: bool,
    subreddits: str | None,
    channels: str | None,
    days: int | None,
    limit: int | None,
    dry_run: bool,
    track_competitive: bool,
) -> None:
    """Fetch new content from configured sources."""
    settings = get_settings()
    verbose = ctx.obj.get("verbose", False)

    # Determine what to scan
    # If any *-only flag is set, only scan that source
    only_flags = [reddit_only, youtube_only, hackernews_only]
    any_only = any(only_flags)

    scan_reddit = reddit_only if any_only else True
    scan_youtube = youtube_only if any_only else True
    scan_hackernews = hackernews_only if any_only else True

    # Calculate since date
    since = None
    if days:
        since = datetime.now() - timedelta(days=days)
    else:
        since = datetime.now() - timedelta(days=settings.reddit.max_age_days)

    total_reddit = 0
    total_youtube = 0

    # Scan Reddit
    # Determine if Reddit scanning is possible based on mode
    reddit_mode = settings.reddit.mode
    can_scan_reddit = reddit_mode == "rss" or (  # RSS mode doesn't need credentials
        reddit_mode == "api" and settings.has_reddit_credentials()
    )

    if scan_reddit and can_scan_reddit:
        mode_label = "RSS" if reddit_mode == "rss" else "API"
        console.print(f"\n[bold]Scanning Reddit ({mode_label} mode)...[/bold]")

        try:
            # Choose the appropriate source based on mode
            reddit_source: RedditRSSSource | RedditSource = (
                RedditRSSSource() if reddit_mode == "rss" else RedditSource()
            )

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Fetching Reddit posts...", total=None)

                items = reddit_source.fetch(since=since, limit=limit)

                progress.update(task, description=f"Processing {len(items)} posts...")

                threads_to_insert = []
                for item in items:
                    thread = process_reddit_thread(item)

                    if dry_run:
                        if verbose:
                            console.print(
                                f"  [dim]Would save:[/dim] {thread.title[:60]}... "
                                f"(score: {thread.relevance_score:.0f})"
                            )
                    else:
                        threads_to_insert.append(thread)

                    total_reddit += 1

                # Batch insert all threads in single transaction
                if threads_to_insert:
                    insert_reddit_threads_batch(threads_to_insert)

            console.print(
                f"[green]✓[/green] Reddit: {total_reddit} new posts"
                + (" (dry run)" if dry_run else "")
            )

        except RedditError as e:
            console.print(f"[red]✗[/red] Reddit error: {e}")
            logger.error(f"Reddit scan failed: {e}")

    elif scan_reddit and reddit_mode == "api":
        console.print("[yellow]⚠[/yellow] Reddit API credentials not configured. Skipping.")
        console.print(
            "[dim]  Tip: Set mode to 'rss' in config.yaml to use RSS feeds instead.[/dim]"
        )

    # Scan YouTube
    if scan_youtube and settings.has_youtube_credentials():
        console.print("\n[bold]Scanning YouTube...[/bold]")

        try:
            youtube_source = YouTubeSource()

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Fetching YouTube videos...", total=None)

                items = youtube_source.fetch(since=since, limit=limit)

                progress.update(task, description=f"Processing {len(items)} videos...")

                videos_to_insert = []
                for item in items:
                    video = process_youtube_video(item)

                    if dry_run:
                        if verbose:
                            console.print(
                                f"  [dim]Would save:[/dim] {video.title[:60]}... "
                                f"(score: {video.relevance_score:.0f})"
                            )
                    else:
                        videos_to_insert.append(video)

                    total_youtube += 1

                # Batch insert all videos in single transaction
                if videos_to_insert:
                    insert_youtube_videos_batch(videos_to_insert)

            console.print(
                f"[green]✓[/green] YouTube: {total_youtube} new videos"
                + (" (dry run)" if dry_run else "")
            )

        except YouTubeError as e:
            console.print(f"[red]✗[/red] YouTube error: {e}")
            logger.error(f"YouTube scan failed: {e}")

    elif scan_youtube:
        console.print("[yellow]⚠[/yellow] YouTube API key not configured. Skipping.")

    # Scan Hacker News
    total_hackernews = 0
    if scan_hackernews:
        console.print("\n[bold]Scanning Hacker News...[/bold]")

        try:
            from signalsift.database.queries import insert_hackernews_items_batch
            from signalsift.sources.hackernews import HackerNewsSource

            hn_source = HackerNewsSource()

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Fetching Hacker News posts...", total=None)

                items = hn_source.fetch(since=since, limit=limit or 100)

                progress.update(task, description=f"Processing {len(items)} posts...")

                hn_items_to_insert: list[HackerNewsItem | dict] = []
                for item in items:
                    hn_data = process_hackernews_item(item)

                    if dry_run:
                        if verbose:
                            console.print(
                                f"  [dim]Would save:[/dim] {hn_data.title[:60]}... "
                                f"(score: {hn_data.relevance_score:.0f})"
                            )
                    else:
                        hn_items_to_insert.append(hn_data)

                    total_hackernews += 1

                # Batch insert all Hacker News items in single transaction
                if hn_items_to_insert:
                    insert_hackernews_items_batch(hn_items_to_insert)

            console.print(
                f"[green]✓[/green] Hacker News: {total_hackernews} new posts"
                + (" (dry run)" if dry_run else "")
            )

        except Exception as e:
            console.print(f"[red]✗[/red] Hacker News error: {e}")
            logger.error(f"Hacker News scan failed: {e}")

    # Track competitive intelligence
    if track_competitive and not dry_run:
        try:
            from signalsift.database.queries import get_reddit_threads, get_youtube_videos
            from signalsift.processing.competitive import get_competitive_intel

            console.print("\n[dim]Tracking competitive tool mentions...[/dim]")
            intel = get_competitive_intel()

            # Get recent threads and videos for tracking
            recent_threads = get_reddit_threads(
                since_timestamp=int(since.timestamp()) if since else None,
                limit=500,
            )
            recent_videos = get_youtube_videos(
                since_timestamp=int(since.timestamp()) if since else None,
                limit=100,
            )

            tracked = intel.track_content(threads=recent_threads, videos=recent_videos)
            if tracked > 0:
                console.print(f"[dim]  Tracked {tracked} new tool mentions[/dim]")

        except Exception as e:
            logger.debug(f"Competitive tracking failed: {e}")

    # Summary
    console.print()
    if dry_run:
        console.print(
            f"[bold]Dry run complete:[/bold] Would have saved "
            f"{total_reddit} Reddit posts, {total_youtube} YouTube videos, "
            f"and {total_hackernews} Hacker News posts"
        )
    else:
        console.print(
            f"[bold]Scan complete:[/bold] Added "
            f"{total_reddit} Reddit posts, {total_youtube} YouTube videos, "
            f"and {total_hackernews} Hacker News posts"
        )

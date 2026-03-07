"""Report generation command."""

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from signalsift.exceptions import ReportError
from signalsift.reports.generator import ReportGenerator
from signalsift.utils.logging import get_logger

console = Console()
logger = get_logger(__name__)


@click.command()
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    help="Custom output path for the report",
)
@click.option(
    "--days",
    type=int,
    default=None,
    help="Only include content from the last N days",
)
@click.option(
    "--min-score",
    type=float,
    default=None,
    help="Minimum relevance score to include",
)
@click.option(
    "--max-items",
    type=int,
    default=None,
    help="Maximum items per section",
)
@click.option(
    "--include-processed",
    is_flag=True,
    help="Include previously processed content",
)
@click.option(
    "--preview",
    is_flag=True,
    help="Generate report without marking content as processed",
)
@click.option(
    "--topic",
    default=None,
    metavar="CATEGORY",
    help="Filter report to a single keyword category (e.g. crypto, seo, webdev)",
)
@click.option(
    "--list-topics",
    is_flag=True,
    help="List available keyword categories and exit",
)
@click.pass_context
def report(
    ctx: click.Context,
    output: Path | None,
    days: int | None,
    min_score: float | None,
    max_items: int | None,
    include_processed: bool,
    preview: bool,
    topic: str | None,
    list_topics: bool,
) -> None:
    """Generate a markdown report from cached content."""
    verbose = ctx.obj.get("verbose", False)

    if list_topics:
        from collections import defaultdict

        from signalsift.database.queries import get_all_keywords

        keywords = get_all_keywords()
        category_counts: dict[str, int] = defaultdict(int)
        for kw in keywords:
            category_counts[kw.category] += 1

        table = Table(title="Available Report Topics", show_header=True, header_style="bold")
        table.add_column("Topic", style="cyan")
        table.add_column("Keywords", justify="right")
        table.add_column("Usage", style="dim")
        for cat, count in sorted(category_counts.items()):
            table.add_row(cat, str(count), f"sift report --topic {cat}")
        console.print(table)
        return

    if topic:
        console.print(f"\n[bold]Generating report (topic: {topic})...[/bold]")
    else:
        console.print("\n[bold]Generating report...[/bold]")

    try:
        generator = ReportGenerator()

        output_path = generator.generate(
            output_path=output,
            min_score=min_score,
            since_days=days,
            max_items=max_items,
            include_processed=include_processed,
            preview=preview,
            topic=topic,
        )

        if preview:
            console.print(f"[green]✓[/green] Preview report generated: [bold]{output_path}[/bold]")
            console.print("[dim]Content not marked as processed (preview mode)[/dim]")
        else:
            console.print(f"[green]✓[/green] Report generated: [bold]{output_path}[/bold]")

        # Show quick stats
        if verbose:
            console.print(f"\n[dim]Output path: {output_path.absolute()}[/dim]")

    except ReportError as e:
        console.print(f"[red]✗[/red] Report generation failed: {e}")
        logger.error(f"Report generation failed: {e}")
        raise click.Abort() from e

    except Exception as e:
        console.print(f"[red]✗[/red] Unexpected error: {e}")
        logger.exception("Report generation failed with unexpected error")
        raise click.Abort() from e

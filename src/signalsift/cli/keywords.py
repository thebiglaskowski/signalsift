"""Keywords management commands."""

import click
from rich.console import Console
from rich.table import Table

from signalsift.database.models import Keyword
from signalsift.database.queries import (
    add_keyword,
    get_all_keywords,
    get_keywords_by_category,
    remove_keyword,
)

console = Console()


@click.group()
def keywords() -> None:
    """Manage tracked keywords for content scoring."""
    pass


@keywords.command("list")
@click.option("--category", help="Filter by category")
@click.option("--all", "show_all", is_flag=True, help="Show disabled keywords too")
def list_keywords(category: str | None, show_all: bool) -> None:
    """List all tracked keywords."""
    if category:
        all_keywords = get_keywords_by_category(category, enabled_only=not show_all)
    else:
        all_keywords = get_all_keywords(enabled_only=not show_all)

    if not all_keywords:
        console.print("[dim]No keywords configured.[/dim]")
        return

    # Group by category
    categories: dict[str, list[Keyword]] = {}
    for kw in all_keywords:
        if kw.category not in categories:
            categories[kw.category] = []
        categories[kw.category].append(kw)

    for cat, kws in sorted(categories.items()):
        table = Table(
            title=f"Category: {cat.replace('_', ' ').title()}",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Keyword", style="bold")
        table.add_column("Weight", justify="right")
        table.add_column("Status", justify="center")

        for kw in sorted(kws, key=lambda x: x.weight, reverse=True):
            status = "[green]✓[/green]" if kw.enabled else "[red]✗[/red]"
            table.add_row(kw.keyword, f"{kw.weight:.1f}", status)

        console.print(table)
        console.print()


@keywords.command("add")
@click.argument("keywords", nargs=-1, required=True)
@click.option(
    "--category",
    required=True,
    help="Category (e.g., success_signals, pain_points, tool_mentions, techniques)",
)
@click.option("--weight", type=float, default=1.0, help="Scoring weight (default: 1.0)")
def add_keyword_cmd(keywords: tuple[str, ...], category: str, weight: float) -> None:
    """Add one or more tracked keywords."""
    for keyword in keywords:
        kw = Keyword(
            keyword=keyword.lower(),
            category=category,
            weight=weight,
            enabled=True,
        )
        add_keyword(kw)
        console.print(
            f"[green]✓[/green] Added keyword '{keyword}' to category '{category}' (weight: {weight})"
        )


@keywords.command("remove")
@click.argument("keyword")
@click.option("--force", is_flag=True, help="Skip confirmation")
def remove_keyword_cmd(keyword: str, force: bool) -> None:
    """Remove a tracked keyword."""
    if not force:
        if not click.confirm(f"Remove keyword '{keyword}'?"):
            console.print("[yellow]Cancelled.[/yellow]")
            return

    if remove_keyword(keyword):
        console.print(f"[green]✓[/green] Removed keyword: {keyword}")
    else:
        console.print(f"[red]✗[/red] Keyword not found: {keyword}")


@keywords.command("categories")
def list_categories() -> None:
    """Show available keyword categories."""
    categories = {
        "success_signals": "Indicators of successful strategies or results",
        "pain_points": "User frustrations and problems to solve",
        "tool_mentions": "SEO tools and software references",
        "techniques": "SEO methods and strategies",
        "monetization": "Revenue and monetization discussions",
        "ai_visibility": "AI search and GEO optimization",
        "content_generation": "AI content and automation",
    }

    table = Table(
        title="Keyword Categories",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Category", style="bold")
    table.add_column("Description")

    for cat, desc in categories.items():
        table.add_row(cat, desc)

    console.print(table)

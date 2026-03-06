# CLI — Command Layer

> Click-based user-facing command groups. Each command module maps to a feature area.

@rules/terminal-ui.md

## Patterns

- All command modules define a `@click.group()` or `@click.command()` — no standalone functions
- Pass shared state (verbose flag, db connection) via `@click.pass_context` + `ctx.obj`
- Use `rich.console.Console` for all output — no `print()` calls
- Rich markup for status: `[green]✓[/green]` for success, `[yellow]...[/yellow]` for warnings, `[red]✗[/red]` for errors
- Confirm destructive actions with `click.confirm()` before proceeding
- Inline imports for heavy or optional dependencies (e.g., `from signalsift.database.connection import reset_database` inside the command body)
- Command docstrings are the `--help` text — keep them concise and user-facing

## Structure

```
cli/
  main.py     # Root cli group + init command; auto-initializes DB on first run
  scan.py     # sift scan — fetch content from all enabled sources
  report.py   # sift report — generate markdown report
  status.py   # sift status — show source/keyword config summary
  sources.py  # sift sources — CRUD for source configuration
  keywords.py # sift keywords — CRUD for keyword tracking
  cache.py    # sift cache — inspect and clear local cache
```

## Key Files

| File | Note |
|------|------|
| `main.py` | Registers all subgroups; handles DB auto-init on every invocation |

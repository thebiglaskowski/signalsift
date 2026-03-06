# SignalSift

> Personal community intelligence CLI tool. Monitors Reddit, YouTube, and Hacker News for topics you care about and generates markdown reports for review and analysis.

## Quality Philosophy

- Fix every error you encounter, regardless of who introduced it
- Never label issues as "pre-existing" or "out of scope"
- Quality gates must pass with ZERO errors, not "zero new errors"
- The goal is a perfect codebase, not just "didn't make it worse"
- Solve root causes, never apply workarounds or quick fixes
- If you cannot fix something, explain why and propose alternatives — don't dismiss it
- Admit mistakes immediately — "I made a mistake" not "there was an issue"

## Tech Stack

| Technology | Purpose |
|-----------|---------|
| Python 3.11+ | Language |
| Click | CLI framework |
| Pydantic v2 | Data models and validation |
| Rich | Terminal output and formatting |
| SQLite | Local database (via stdlib sqlite3) |
| hatchling | Build backend |
| ruff | Linter (E, F, I, N, W, UP, B, C4, SIM rules) |
| black | Formatter (line-length 100) |
| mypy | Type checking (strict: disallow_untyped_defs) |
| pytest + pytest-cov | Testing (coverage threshold: 70%) |
| uv | Package and environment manager |

Optional extras: `.[nlp]` (spaCy), `.[ai]` (OpenAI/Anthropic), `.[semantic]` (FAISS)

## Architecture

```
src/signalsift/
  cli/          # Click command groups — user-facing interface
  config/       # Settings (pydantic-settings) + defaults
  database/     # SQLite connection, schema, models, queries, migrations
  processing/   # Content pipeline: scoring, sentiment, trends, NLP, LLM
  reports/      # Markdown report generation (Jinja2 templates)
  sources/      # Data source adapters: Reddit (API+RSS), YouTube, HN
  utils/        # Logging, retry, text helpers, formatting
  exceptions.py # Custom exception hierarchy
tests/          # Mirrors src/signalsift/ structure
documentation/  # One doc per feature — read before touching feature code
templates/      # Jinja2 report templates
data/           # Local SQLite database and cache files
reports/        # Generated markdown output files
```

## Commands

```bash
# Install / setup
uv venv && uv pip install -e .
uv pip install -e ".[all]"       # with all optional extras

# Run the CLI
uv run sift --help
uv run sift scan                 # fetch new content from all sources
uv run sift report               # generate markdown report
uv run sift status               # show current configuration
uv run sift sources              # manage data sources
uv run sift keywords             # manage tracking keywords
uv run sift cache                # manage local cache

# Quality gates (all must pass with zero errors)
uv run ruff check src/ tests/   # lint
uv run black --check src/ tests/ # format check
uv run mypy src/                 # type check
uv run pytest                    # tests with coverage
uv run pytest --cov=signalsift --cov-report=term-missing  # with coverage report
```

## Code Standards

- Line length: **100** characters (black + ruff)
- Target: Python **3.11** (`from __future__ import annotations` not needed — use native syntax)
- Type annotations required on all functions (`disallow_untyped_defs = true`)
- Use `X | Y` union syntax, not `Optional[X]` or `Union[X, Y]`
- Named constants for magic numbers (see `processing/scoring.py` for the pattern)
- Pydantic v2 validators use `@field_validator` with `mode="before"` where needed
- Models provide `.to_db_dict()` for SQLite insertion

## Environment Variables

```
REDDIT_CLIENT_ID      — Reddit API app client ID (only needed for API mode, not RSS)
REDDIT_CLIENT_SECRET  — Reddit API app client secret
YOUTUBE_API_KEY       — YouTube Data API v3 key (from Google Cloud Console)
OPENAI_API_KEY        — OpenAI API key (optional, for AI summarization)
ANTHROPIC_API_KEY     — Anthropic API key (optional, for AI summarization)
```

Copy `.env.example` to `.env` and fill in credentials. RSS mode works without any API keys.

## Key Files

| File | Purpose |
|------|---------|
| `src/signalsift/cli/main.py` | CLI entry point, `cli` group, auto-init logic |
| `src/signalsift/config/settings.py` | Pydantic-settings config class |
| `src/signalsift/database/connection.py` | DB path, init, reset helpers |
| `src/signalsift/database/schema.py` | `get_schema_sql()` — source of truth for schema |
| `src/signalsift/sources/base.py` | `BaseSource` ABC + `ContentItem` dataclass |
| `src/signalsift/exceptions.py` | Custom exception hierarchy |
| `pyproject.toml` | All tool config (ruff, black, mypy, pytest, coverage) |
| `documentation/_index.md` | Feature doc index — read the relevant doc before editing a feature |

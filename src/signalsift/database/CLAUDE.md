# Database Layer

> SQLite via stdlib `sqlite3`. Schema defined in `schema.py`; models use Pydantic v2.

@rules/database.md

## Patterns

- `schema.py` is the single source of truth — `get_schema_sql()` returns the full DDL
- Models live in `models.py` as Pydantic `BaseModel` subclasses: `RedditThread`, `YouTubeVideo`, `HackerNewsItem`
- Every model implements `.to_db_dict()` for SQLite insertion (serializes lists to JSON strings)
- `@field_validator("matched_keywords", mode="before")` pattern: deserialize JSON strings back to Python lists on load
- Boolean columns stored as `INTEGER` (0/1) — convert in `.to_db_dict()` and validators
- Timestamps stored as `INTEGER` (Unix epoch via `int(datetime.now().timestamp())`)
- Queries in `queries.py` — use parameterized queries, never string interpolation
- `connection.py` provides: `get_db_path()`, `initialize_database()`, `reset_database()`, `database_exists()`
- `migrations.py` handles schema evolution — check before adding columns

## Structure

```
database/
  connection.py  # Path resolution, init/reset helpers, context manager
  schema.py      # get_schema_sql() — all CREATE TABLE statements
  models.py      # Pydantic models: RedditThread, YouTubeVideo, HackerNewsItem
  queries.py     # All SQL read/write functions — parameterized only
  migrations.py  # ALTER TABLE migrations for schema changes
```

## Key Constraints

- DB file path comes from `config/settings.py` — never hardcode `data/signalsift.db`
- Tests patch `signalsift.database.connection.get_db_path` to inject `tmp_path` (see `conftest.py`)
- Never hold connections open across function calls — use context managers

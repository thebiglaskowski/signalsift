# Tests

> pytest-based test suite. Mirrors `src/signalsift/` structure. Coverage threshold: 70%.

@rules/testing.md

## Patterns

- Test files named `test_{module}.py`, test functions named `test_{behavior}_{condition}`
- Use `conftest.py` fixtures — do not duplicate fixture setup in individual test files
- Database tests: use `temp_db` fixture — it patches `get_db_path` to `tmp_path` automatically
- External API calls: always mock with `unittest.mock.patch` or `MagicMock` — no real network calls in tests
- CLI tests: use `click.testing.CliRunner` to invoke commands and assert output/exit codes
- Optional dependency tests: skip gracefully if extra not installed (`pytest.importorskip("spacy")`)

## Key Fixtures (conftest.py)

| Fixture | Provides |
|---------|----------|
| `temp_db_path` | `Path` to a temp `.db` file (not initialized) |
| `temp_db` | Initialized temp DB with schema; patches `get_db_path` for the test |
| `sample_reddit_thread` | Pre-built `RedditThread` model for testing |
| `sample_youtube_video` | Pre-built `YouTubeVideo` model |

## Running Tests

```bash
uv run pytest                                          # all tests
uv run pytest tests/test_processing/                  # one module
uv run pytest -k "test_scoring"                       # by name pattern
uv run pytest --cov=signalsift --cov-report=term-missing  # with coverage
uv run pytest --cov=signalsift --cov-fail-under=70    # enforce threshold
```

## Structure

```
tests/
  conftest.py              # Shared fixtures
  test_cli/                # CLI command tests
  test_config/             # Settings tests
  test_database/           # Schema, queries, model tests
  test_processing/         # Scoring, keywords, sentiment, etc.
  test_reports/            # Report generation tests
  test_sources/            # Source adapter tests (mocked APIs)
  test_utils/              # Utility function tests
  test_exceptions.py       # Exception hierarchy tests
```

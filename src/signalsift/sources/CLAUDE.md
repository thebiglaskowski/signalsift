# Sources — Data Adapters

> Pluggable adapters for Reddit (API + RSS), YouTube, and Hacker News. All implement `BaseSource`.

@rules/api-design.md
@rules/error-handling.md

## Patterns

- All sources extend `BaseSource` (ABC) from `base.py` — implement `fetch()`, `get_source_type()`, `test_connection()`
- `fetch()` returns `list[ContentItem]` — the common currency across the pipeline
- `ContentItem` is a `@dataclass` in `base.py` — don't subclass it, populate it from source-specific data
- Use `utils/retry.py` for all external API calls — exponential backoff is already implemented
- Prefer RSS mode for Reddit (`reddit_rss.py`) — no API credentials required
- API credentials come from `config/settings.py` — never read env vars directly in source modules
- `test_connection()` must be a lightweight probe — don't fetch real data, just validate auth/reachability
- Raise `signalsift.exceptions.*` not raw exceptions — lets the CLI handle them uniformly

## Structure

```
sources/
  base.py       # BaseSource ABC + ContentItem dataclass
  reddit.py     # PRAW-based Reddit adapter (requires API credentials)
  reddit_rss.py # RSS-based Reddit adapter (no credentials needed)
  youtube.py    # YouTube Data API v3 adapter
  hackernews.py # Hacker News Algolia API adapter (no credentials)
```

## Adding a New Source

1. Create `sources/{name}.py` implementing `BaseSource`
2. Return `ContentItem` objects from `fetch()`
3. Register in `cli/sources.py` source type list
4. Add a test in `tests/test_sources/test_{name}.py`

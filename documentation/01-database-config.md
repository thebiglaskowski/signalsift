---
feature: Database & Configuration
version: "1.0"
last_updated: 2026-03-06
dependencies: []
routes:
  - "CLI: sift init"
  - "CLI: sift migrate [--check] [--version N]"
  - "CLI: sift status"
status: draft
---

# Database & Configuration

> Manages the SQLite database lifecycle and application configuration loaded from `config.yaml` and `.env`.

## Data Model

### Tables Overview

| Table | Purpose |
|-------|---------|
| `reddit_threads` | Cached Reddit posts |
| `youtube_videos` | Cached YouTube videos |
| `hackernews_items` | Cached Hacker News stories |
| `reports` | Report generation history |
| `keywords` | Tracked keywords with categories/weights |
| `sources` | Configured subreddits and YouTube channels |
| `processing_log` | Debug log for scan/report actions |
| `keyword_trends` | Keyword mention counts over time periods |
| `tool_mentions` | Competitive tool mention tracking |
| `content_analysis` | LLM/sentiment/entity analysis results |
| `engagement_snapshots` | Engagement velocity tracking over time |

**Database path:** `data/signalsift.db` (default, configurable via `SIGNALSIFT_DATABASE__PATH`)

### Migration Versioning

Migrations are defined in `src/signalsift/database/migrations.py` as a list of `Migration` dataclasses. Each migration has: `version` (int), `name` (str), `sql` (str). The schema version is stored in SQLite's `PRAGMA user_version`.

## CLI Commands

### `sift init`

**Purpose:** Initialize or reinitialize the database with default sources and keywords.

**Behavior:**
- If database does not exist: creates it and populates defaults (calls `initialize_database(populate_defaults=True)`)
- If database already exists: prompts for confirmation, then calls `reset_database()` which drops and recreates all tables — **destructive**
- Auto-runs on every `sift` invocation if database doesn't exist yet

### `sift migrate [--check] [--version N]`

**Purpose:** Apply pending database schema migrations.

**Options:**
- `--check`: Show current version, latest version, applied/pending counts. Does not apply anything.
- `--version N`: Migrate to a specific version number instead of latest.

**Behavior:** Idempotent. Prints count of applied migrations. If already up to date, says so.

### `sift status`

**Purpose:** Show a rich-formatted dashboard of database stats, source counts, report history, and API credential status.

**Shows:**
- Database path and file size
- Reddit threads: total, unprocessed, last scan time
- YouTube videos: total, unprocessed, last scan time
- Sources configured (total + enabled per type)
- Reports generated + last report date/path
- API credential status (Reddit, YouTube)

## Configuration

### `config.yaml` Structure

```yaml
reddit:
  mode: rss          # "rss" (no credentials) or "api" (requires client_id/secret)
  min_score: 10      # Minimum Reddit upvotes to capture
  min_comments: 3    # Minimum comment count to capture
  max_age_days: 30   # How far back to look
  posts_per_subreddit: 25
  request_delay_seconds: 1.0

youtube:
  min_duration_seconds: 300   # 5 minutes
  max_duration_seconds: 7200  # 2 hours
  max_age_days: 30
  videos_per_channel: 10
  include_search: true
  search_queries_per_run: 5
  transcript_language: "en"
  transcript_max_length: 50000

scoring:
  min_relevance_score: 20     # Minimum score to include in reports
  weights:
    engagement: 1.0
    keywords: 1.2
    content_quality: 1.0
    source_tier: 0.8

reports:
  output_directory: reports/
  filename_format: "{date}.md"
  max_items_per_section: 15
  excerpt_length: 300

logging:
  level: INFO
  file: logs/signalsift.log
  max_size_mb: 10
  backup_count: 3
```

### Environment Variables

All settings can be overridden via env vars with prefix `SIGNALSIFT_` and `__` as nested delimiter:

| Variable | Purpose |
|----------|---------|
| `REDDIT_CLIENT_ID` | Reddit OAuth client ID (for API mode) |
| `REDDIT_CLIENT_SECRET` | Reddit OAuth client secret |
| `YOUTUBE_API_KEY` | YouTube Data API v3 key |
| `SIGNALSIFT_DATABASE__PATH` | Override database file path |
| `SIGNALSIFT_REDDIT__MODE` | Override Reddit mode |

Loaded via `pydantic-settings` with `env_file=".env"`. Copy `.env.example` to `.env` to configure.

## Business Rules

- **Auto-init:** Database is auto-initialized on first `sift` command if it doesn't exist. No manual init required for first use.
- **Settings cache:** `get_settings()` is `@lru_cache`-decorated — settings are loaded once per process. In tests, clear the cache with `get_settings.cache_clear()`.
- **Reddit mode:** Default is `rss` (no credentials needed). Setting `mode: api` requires `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` in `.env`. YouTube always requires `YOUTUBE_API_KEY`.
- **Directories:** `data/`, `reports/`, and `logs/` are auto-created by `settings.ensure_directories()` at startup.

## Edge Cases

- **Reset is destructive:** `sift init` on an existing database drops all content. Always confirm before running.
- **Missing .env:** Application works without `.env` — YouTube and Reddit API mode simply become unavailable. RSS mode for Reddit works without any credentials.
- **Schema version mismatch:** Run `sift migrate --check` first to see pending migrations. Never edit `data/signalsift.db` manually.

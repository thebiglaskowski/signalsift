---
feature: Report Generation
version: "1.0"
last_updated: 2026-03-06
dependencies:
  - "01-database-config.md"
  - "05-scoring.md"
routes:
  - "CLI: sift report [options]"
status: draft
---

# Report Generation

> Generates a markdown report from cached, scored content — pulling unprocessed Reddit threads and YouTube videos from the database, categorizing them by topic, and writing a Jinja2-rendered report to disk.

## CLI Command

### `sift report`

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `-o / --output PATH` | path | auto | Custom output path for the report |
| `--days N` | int | null | Only include content from last N days |
| `--min-score N` | float | `scoring.min_relevance_score` | Minimum relevance score to include |
| `--max-items N` | int | `reports.max_items_per_section` | Maximum items per report section |
| `--include-processed` | flag | false | Include previously processed content |
| `--preview` | flag | false | Generate report without marking content as processed |

**Default output path:** `{reports.output_directory}/{date}.md` — formatted via `reports.filename_format` in `config.yaml`. Supports `{date}` and `{time}` placeholders.

## Report Sections

The Jinja2 template at `src/signalsift/reports/templates/default.md.j2` renders the following sections from context data built by `ReportGenerator._build_context()`:

| Template Variable | Contents |
|-------------------|----------|
| `pain_points` | Threads categorized as `pain_point` |
| `success_stories` | Threads categorized as `success_story` |
| `tool_mentions` | Threads categorized as `tool_comparison` |
| `monetization_insights` | Threads with `monetization`, `roi_analysis`, or `ecommerce` category |
| `ai_visibility_insights` | Threads with `ai_visibility` category |
| `keyword_research_insights` | Threads with `keyword_research` or `local_seo` category |
| `content_generation_insights` | Threads with `ai_content` category |
| `competition_insights` | Threads with `competitor_analysis` or `content_brief` category |
| `image_generation_insights` | Threads with `image_generation` category |
| `static_sites_insights` | Threads with `static_sites` category |
| `rising_content` | Threads with engagement velocity >= 10 (top 10, sorted by velocity) |
| `youtube_videos` | YouTube videos (up to `max_items_per_section`) |
| `trends` | Top 5 emerging keyword trends (from `analyze_trends()`) |
| `emerging_trends` | Top 5 emerging trends with change % |
| `declining_trends` | Top 5 declining trends with change % |
| `new_topics` | Top 5 new topics not seen in prior period |
| `top_tools` | Top 5 competitive tools by mention count with sentiment label |
| `feature_gaps` | Top 5 feature gap opportunities from competitor complaints |

### Report Metadata

Each report includes a metadata header with:
- `generated_at`: ISO timestamp of generation
- `date_range_start` / `date_range_end`: Date range of included content
- `sources_summary`: Count of unique subreddits and YouTube channels
- `version`: SignalSift version string
- `reddit_count` / `youtube_count` / `new_count`: Item counts
- `top_themes`: Up to 5 most common content categories by frequency

## Thread/Video Context Shape

Each content item in the template receives:

**Reddit thread fields:**
- `title`, `url`, `source_badge` (`r/<subreddit>`), `relevance_score` (rounded int)
- `engagement` (formatted as `{score}↑ · {comments} comments`)
- `excerpt` (truncated `selftext`, default 300 chars, appended with `...`)
- `category`, `matched_keywords`
- Optional AI insight fields (all `None` unless AI analysis is run): `feature_suggestion`, `takeaway`, `monetization_angle`, `geo_opportunity`, `keyword_opportunity`, `content_strategy`, `competitive_angle`, `image_opportunity`, `tech_insight`

**YouTube video fields:**
- `title`, `url`, `channel_name`, `relevance_score` (rounded int)
- `view_count`, `like_count`, `duration_formatted`, `duration_seconds`
- `transcript_excerpt` (truncated to `excerpt_length`), `transcript_available`
- `category`, `matched_keywords`, `insights` (None unless AI analysis run)

## Processing Pipeline

1. Fetch unprocessed content via `get_unprocessed_content()` (filtered by `min_score` and `since_days`)
2. If `--include-processed`, fetches all content instead (no processed filter)
3. Build Jinja2 context via `_build_context()` — categorizes, finds rising content, pulls trend and competitive data
4. Render `default.md.j2` template
5. Write rendered markdown to output path (creates parent dirs if needed)
6. If not `--preview`: insert a `Report` record into the `reports` table and call `mark_content_processed()` on all included item IDs

## Data Model

### `reports` table

| Field | Type | Notes |
|-------|------|-------|
| `id` | TEXT | UUID, primary key |
| `generated_at` | INTEGER | Unix timestamp |
| `filepath` | TEXT | Absolute path to generated file |
| `reddit_count` | INTEGER | Reddit threads included |
| `youtube_count` | INTEGER | YouTube videos included |
| `date_range_start` | INTEGER | Earliest content timestamp (nullable) |
| `date_range_end` | INTEGER | Latest content timestamp (nullable) |
| `config_snapshot` | TEXT | JSON of `{min_score, since_days, max_items}` |

### Processed flag

After report generation (non-preview), `processed = 1` and `report_id = <uuid>` are set on all included `reddit_threads` and `youtube_videos` rows. Processed content is excluded from future reports unless `--include-processed` is passed.

## Business Rules

- **Preview mode:** `--preview` generates the full report file but does NOT insert a `reports` record and does NOT mark content as processed. Use for testing report output without consuming content.
- **Default min score:** Falls back to `scoring.min_relevance_score` from `config.yaml` (default: 20) if `--min-score` is not passed. Can be overridden per-run.
- **No content error:** If no content passes the score/date filters, `ReportError` is raised and the CLI prints an error. No file is written.
- **Section limits:** Each category section is capped at `max_items_per_section` (default: 15 from config). Override with `--max-items`.
- **Rising content cap:** Always top 10 by velocity, regardless of `--max-items`.
- **Trend data:** Calls `analyze_trends(current_period_days=7)`. If this fails, trend sections are empty (no crash).
- **Competitive data:** Calls `CompetitiveIntelligence` for last 30 days. If it fails, competitive sections are empty (no crash).
- **Content already in report:** Deduplicated by `processed` flag — once included in any report, a thread/video is marked processed and excluded from subsequent runs (unless `--include-processed`).

## Edge Cases

- **Empty sections:** If no content matches a category, the template variable is an empty list. The template should handle empty sections gracefully.
- **Date range calculation:** Derived from min/max of `created_utc` (threads) and `published_at` (videos). If somehow a report has neither, falls back to `now`.
- **`--include-processed` with `--days`:** When `include_processed` is True, uses `get_reddit_threads()` and `get_youtube_videos()` directly (not the unprocessed query), applying `since_days` as a timestamp filter.
- **Output path collision:** If the same date produces two reports, the second run overwrites the first file (no auto-incrementing suffix).
- **Jinja2 autoescaping:** Enabled only for HTML/XML extensions. The `.md.j2` template is not autoescaped — content is rendered as-is.

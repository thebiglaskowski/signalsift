---
feature: Content Scanning
version: "1.0"
last_updated: 2026-03-06
dependencies:
  - "01-database-config.md"
  - "02-sources.md"
  - "03-keywords.md"
  - "05-scoring.md"
routes:
  - "CLI: sift scan [options]"
status: draft
---

# Content Scanning

> Fetches new content from Reddit (RSS or API), YouTube, and Hacker News, scores it for relevance, and stores it in the SQLite database.

## CLI Command

### `sift scan`

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--reddit-only` | flag | false | Only scan Reddit sources |
| `--youtube-only` | flag | false | Only scan YouTube sources |
| `--hackernews-only` | flag | false | Only scan Hacker News |
| `--subreddits TEXT` | string | null | Comma-separated subreddits to scan (overrides database sources) |
| `--channels TEXT` | string | null | Comma-separated YouTube channel IDs to scan |
| `--days N` | int | null | Fetch content from last N days (default: `reddit.max_age_days` from config) |
| `--limit N` | int | null | Max items to fetch per source |
| `--dry-run` | flag | false | Show what would be fetched without saving |
| `--track-competitive` | flag | true | Track competitor tool mentions after scan |

**Behavior:** If any `--*-only` flag is set, only that source is scanned. If none are set, all three sources are scanned.

## Source Adapters

### Reddit

Two modes controlled by `reddit.mode` in `config.yaml`:

**RSS mode** (default, no credentials): `RedditRSSSource` in `src/signalsift/sources/reddit_rss.py`
- Fetches from `https://www.reddit.com/r/{subreddit}/new.rss`
- No authentication required
- Parses Atom feed; extracts title, link, author, selftext from `<content>` field

**API mode** (requires credentials): `RedditSource` in `src/signalsift/sources/reddit.py`
- Uses PRAW library with `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET`
- Richer metadata: score, num_comments, flair

**Filtering:** Posts below `reddit.min_score` or `reddit.min_comments` are excluded before scoring.

### YouTube

`YouTubeSource` in `src/signalsift/sources/youtube.py`. Requires `YOUTUBE_API_KEY`.

- Fetches from YouTube Data API v3
- Videos filtered by `min_duration_seconds` / `max_duration_seconds`
- Attempts to fetch transcripts via `youtube-transcript-api`
- Transcripts truncated to `youtube.transcript_max_length` (default: 50,000 chars)

### Hacker News

`HackerNewsSource` in `src/signalsift/sources/hackernews.py`. No credentials required.

- Fetches from HN Algolia API (`hn.algolia.com/api/v1/search`)
- Story types: `"story"`, `"ask_hn"`, `"show_hn"`
- IDs prefixed with `"hn_"` to avoid collisions with Reddit IDs
- Default limit: 100 items per scan

## Processing Pipeline

For each fetched item:
1. Run `process_reddit_thread()` / `process_youtube_video()` / `process_hackernews_item()` from `src/signalsift/processing/scoring.py`
2. Match against all enabled keywords using `KeywordMatcher`
3. Calculate relevance score (0-100 scale)
4. Classify content into a category
5. Compute SHA-256 content hash (title + body/transcript)

Items are batch-inserted using `INSERT OR IGNORE` — duplicate IDs are silently skipped (deduplication by content ID).

## Competitive Tracking

After scanning (unless `--dry-run`), if `--track-competitive` is enabled (default):
- Fetches recent threads/videos from the database (up to 500 Reddit, 100 YouTube)
- Runs `CompetitiveIntelligence.track_content()` to detect tool mentions
- Stores mentions in `tool_mentions` table

## Business Rules

- **RSS vs API for Reddit:** Default is RSS (works out of the box). API mode requires `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET`. If API mode is configured but credentials are missing, Reddit scan is skipped with a warning.
- **YouTube always requires API key:** If `YOUTUBE_API_KEY` is not set, YouTube scan is silently skipped.
- **HN always scans:** No credentials needed. Always runs unless `--reddit-only` or `--youtube-only`.
- **Deduplication:** Content IDs are unique per table. Re-scanning the same time window won't create duplicates (INSERT OR IGNORE).
- **Dry run:** In dry run mode with `--verbose`, shows what would be saved with truncated title and relevance score.
- **Batch inserts:** All inserts for a source are done in a single transaction for performance.
- **Since date:** Default lookback is `reddit.max_age_days` from config (typically 30 days). Override with `--days`.

## Edge Cases

- **Source fetch failure:** If a source throws `RedditError` or `YouTubeError`, the error is logged and displayed, but other sources continue scanning.
- **HN failure:** Any exception during HN scanning is caught and logged; scan continues.
- **Competitive tracking failure:** Silently caught and logged at DEBUG level — never interrupts main scan.
- **Empty results:** If a source returns 0 items, the count is shown as 0. Not an error.

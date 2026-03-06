---
feature: Competitive Intelligence
version: "1.0"
last_updated: 2026-03-06
dependencies:
  - "01-database-config.md"
  - "04-scan.md"
routes: []
status: draft
---

# Competitive Intelligence

> Automatically detects mentions of competitor SEO tools in scanned content, analyzes sentiment, identifies feature gaps from complaints, and tracks which tools are gaining or losing market share.

## Overview

The `CompetitiveIntelligence` class in `src/signalsift/processing/competitive.py` runs after each scan (see `04-scan.md`) and surfaces tool intelligence in generated reports. It requires no configuration — tool detection is keyword-based using a hardcoded `KNOWN_TOOLS` dictionary.

## Data Model

### `tool_mentions` table

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | INTEGER | primary key, autoincrement | Auto-generated |
| `tool_name` | TEXT | NOT NULL | Lowercase tool name (e.g., `"ahrefs"`) |
| `category` | TEXT | nullable | Tool category (e.g., `"backlink"`, `"content"`) |
| `sentiment` | TEXT | nullable | Sentiment label (see Sentiment Labels below) |
| `sentiment_score` | REAL | nullable | Polarity score from sentiment analysis |
| `context` | TEXT | nullable | Up to 500 chars of surrounding text |
| `source_type` | TEXT | nullable | `"reddit"`, `"youtube"`, or `"hackernews"` |
| `source_id` | TEXT | nullable | ID of the originating content |
| `source_title` | TEXT | nullable | Title of the originating content (truncated to 200 chars) |
| `captured_at` | TEXT | NOT NULL | ISO 8601 datetime string |

**Unique constraint:** `(tool_name, source_type, source_id)` — one mention per tool per content item.

**Indexes:** `idx_tool_mentions_tool` on `tool_name`; `idx_tool_mentions_date` on `captured_at`.

### Sentiment Labels

| Label | Meaning |
|-------|---------|
| `switching_from` | User is leaving this tool (treated as negative) |
| `switching_to` | User is adopting this tool (treated as positive) |
| `positive` | Positive sentiment detected |
| `very_positive` | Strong positive sentiment |
| `negative` | Negative sentiment detected |
| `very_negative` | Strong negative sentiment |
| `mixed` | Conflicting signals in context |
| `neutral` | No strong sentiment signal |

## Known Tools

Tools are defined in `KNOWN_TOOLS` dict in `src/signalsift/processing/entities.py`. Each entry maps a lowercase tool name to `{category, tier}`.

**Categories:** `backlink`, `all-in-one`, `keyword`, `content`, `technical`, `ai_content`, `outreach`, `rank_tracking`, `competitor`, `content_research`, `ai_detection`

**Tiers:** `enterprise`, `mid`, `budget`

Current tracked tools include: ahrefs, semrush, moz, se ranking, serpstat, ubersuggest, mangools, kwfinder, surfer, surfer seo, clearscope, marketmuse, frase, neuronwriter, screaming frog, sitebulb, deepcrawl, botify, jasper, copy.ai, content at scale, koala ai, writesonic, article forge, zimmwriter, byword, pitchbox, buzzstream, hunter.io, respona, accuranker, wincher, serprobot, spyfu, similarweb, buzzsumo, answerthepublic, originality.ai, gptzero.

## Detection Pipeline

### Tool Detection (`EntityExtractor._extract_tools()`)

- Case-insensitive substring search across full text (title + body/transcript)
- Context window: 50 chars before and after each match
- Sentiment hint detected from context using regex pattern matching:
  - **switching_from** patterns: "switched from", "moved away from", "left", "abandoned", "gave up on", "stopped using", "cancelled"
  - **switching_to** patterns: "switched to", "moved to", "started using", "now using", "trying out", "signed up for"
  - **positive** patterns: "love", "amazing", "great", "best", "recommend", "worth it", "game changer", "helped", "increased"
  - **negative** patterns: "hate", "terrible", "worst", "expensive", "overpriced", "buggy", "broken", "waste", "disappointed", "frustrat"
- If switching patterns found, they take priority over positive/negative
- Context truncated to 500 chars before storage

### Sentiment Analysis

After tool detection, each mention's context is passed to `analyze_sentiment()` from `src/signalsift/processing/sentiment.py`. The result provides:
- `sentiment.category.value` — category label string
- `sentiment.polarity` — float score stored in `sentiment_score`

The `sentiment_hint` from entity extraction (pattern-based) takes precedence over the full sentiment analysis label if present.

### Content Sources

`track_content()` accepts:
- `threads`: list of `RedditThread` — uses `title + selftext`
- `videos`: list of `YouTubeVideo` — uses `title + transcript[:5000]`

HackerNews items are not currently processed by competitive tracking.

## Analysis Methods

### `get_tool_stats(tool_name=None, days=30) -> list[ToolStats]`

Aggregates `tool_mentions` rows for the past N days. Per tool, counts:
- Total mentions
- Positive / negative / neutral mention counts
- Switching-from and switching-to counts
- Average sentiment polarity
- Up to 5 sample feature requests, complaints, and praises (extracted via regex patterns)
- Up to 5 sample context strings

Results sorted by `mention_count` descending. If `tool_name` is specified, filters to that tool only.

**Feature request patterns:** "wish it had", "would be nice if", "missing feature", "need a better", "should add", "looking for a way", "can't find"

**Complaint patterns:** "too expensive/slow/complicated", "terrible support/ui/ux", "keeps crashing", "waste of money", "gave up", "frustrat", "doesn't work"

**Praise patterns:** "love the tool", "game changer", "life saver", "highly recommend", "worth every penny", "saved me so much time", "couldn't live without"

Each pattern type caps at 5 entries per tool.

### `identify_feature_gaps(days=30) -> list[FeatureGap]`

Derives feature opportunity signals from tool complaints and feature requests. Returns top 20 gaps sorted by demand level then mention count.

**Demand levels:**
- `high`: tool has >= 20 mentions total
- `medium`: tool has >= 10 mentions total
- `low`: tool has < 10 mentions total

Each `FeatureGap` includes: `tool`, `feature_description` (complaint/request text), `demand_level`, `mention_count`, `sentiment_score`, `sample_quotes` (up to 3), `opportunity` (mapped from tool category).

**Category → Opportunity mapping:**
| Tool Category | Opportunity |
|---------------|-------------|
| `backlink` | `link_building` |
| `all-in-one` | `comprehensive` |
| `content` | `content_creation` |
| `keyword` | `keyword_research` |
| `technical` | `technical_seo` |
| `ai_content` | `ai_writing` |
| `outreach` | `outreach` |
| `rank_tracking` | `rank_tracking` |
| `competitor` | `competitive_analysis` |
| `ai_detection` | `ai_detection` |

### `get_market_movers(days=30) -> tuple[list[str], list[str]]`

Returns `(gainers, losers)` — each a list of up to 5 tool names. Net flow = `switching_to_count - switching_from_count`. Tools with positive net flow are gainers; negative net flow are losers. Sorted by absolute net flow magnitude.

### `generate_report(days=30) -> CompetitiveReport`

Assembles a `CompetitiveReport` dataclass with: `generated_at`, `period_start`, `period_end`, `tool_stats`, `feature_gaps`, `market_movers`, `market_losers`. The `head_to_head` field (co-mention analysis) is not yet implemented — always returns `{}`.

## Integration with Reports

`ReportGenerator._build_competitive_data()` calls `CompetitiveIntelligence` to populate these report template variables:
- `top_tools`: Top 5 tools by mention count with `name`, `mentions`, and sentiment label (`"positive"` if avg > 0.1, `"negative"` if avg < -0.1, otherwise `"neutral"`)
- `feature_gaps`: Top 5 gaps with `tool`, `description` (first 100 chars), `demand`, `opportunity`
- `competitive_intel`: Full dict with `tool_stats`, `feature_gaps`, `market_movers` for template access

If competitive data retrieval fails, all fields default to empty (no crash).

## Business Rules

- **Deduplication:** `INSERT OR IGNORE` on `(tool_name, source_type, source_id)` — the same tool mentioned in the same post is only stored once.
- **Table auto-created:** `_ensure_table()` creates `tool_mentions` if it doesn't exist, even if migrations haven't been run. Failure is logged as a warning, not an error.
- **Competitive tracking is opt-out:** Runs by default after every scan. Disable with `sift scan --no-track-competitive` (TODO: verify flag name; source shows `--track-competitive` defaults to `true`).
- **Failure is silent:** Both `track_content()` and the report integration catch all exceptions at DEBUG/WARNING level — competitive tracking never interrupts scanning or report generation.
- **YouTube transcript cap:** Only the first 5,000 characters of the transcript are used for tool detection to limit processing time.
- **Module-level singleton:** `get_competitive_intel()` returns a cached `CompetitiveIntelligence` instance. The DB path is set at first initialization.

## Edge Cases

- **Tool name in URL:** The substring search will match tool names appearing in URLs (e.g., `ahrefs.com`). No URL filtering is applied.
- **Overlapping tool names:** The entity extractor tracks `seen_positions` to avoid counting overlapping matches, but multi-word tools (e.g., "surfer seo") may still produce two entries if "surfer" is also matched separately.
- **No mentions in period:** `get_tool_stats()` returns an empty list. `identify_feature_gaps()` returns `[]`. No error.
- **spaCy not available:** Tool detection via `_extract_tools()` is regex-only and does not require spaCy. Organization/person extraction is skipped if spaCy is unavailable, but tool mentions still work.

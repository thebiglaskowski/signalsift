---
feature: Relevance Scoring
version: "1.0"
last_updated: 2026-03-06
dependencies:
  - "03-keywords.md"
routes: []
status: draft
---

# Relevance Scoring

> Calculates a 0-100 relevance score for each piece of content based on engagement, keyword matches, content quality, and source tier. Scores determine what gets included in reports.

## Scoring Algorithms

All scores are capped at 100 via `min(score, 100)`.

### Reddit Scoring

| Component | Max Points | Method |
|-----------|-----------|--------|
| Upvotes | 20 | `min(score / 2.5, 20)` |
| Comments | 15 | `min(num_comments / 1.33, 15)` |
| Viral bonus | +5 | If upvotes > 100 |
| Keyword matches | 35 | `sum(min(count, 3) * weight * 5)`, capped at 35 |
| Has metrics | +5 | Text contains `%`, `$`, `k`, traffic numbers |
| Detailed post | +5 | `selftext` > 500 characters |
| Quality flair | +5 | Flair contains "case study", "success", "strategy", "results", "guide", "tutorial" |
| Source tier 1 | +10 | High-priority subreddit |
| Source tier 2 | +5 | Medium-priority subreddit |
| Engagement velocity | 0-15 | See velocity table below |

### YouTube Scoring

| Component | Max Points | Method |
|-----------|-----------|--------|
| Views | 15 | `min(view_count / 666.67, 15)` (~10k views = 15 pts) |
| Likes | 10 | `min(like_count / 50, 10)` (~500 likes = 10 pts) |
| High engagement ratio | +5 | like_count/view_count > 4% |
| Keyword matches | 35 | `sum(min(count, 5) * weight * 3)`, capped at 35 |
| Optimal duration | +10 | 10-40 minutes (600-2400 seconds) |
| Acceptable duration | +5 | 5-10 min or 40-60 min |
| Transcript available | +5 | transcript_available = True |
| Substantial transcript | +5 | transcript > 2000 characters |
| Source tier 1 | +15 | High-priority channel |
| Source tier 2 | +8 | Medium-priority channel |

### Hacker News Scoring

| Component | Max Points | Method |
|-----------|-----------|--------|
| Points | 25 | `min(points / 2, 25)` |
| Comments | 15 | `min(num_comments / 2, 15)` |
| Keyword matches | 35 | Same as Reddit formula |
| Ask HN bonus | +10 | story_type = "ask_hn" |
| Show HN bonus | +5 | story_type = "show_hn" |
| High comment ratio | +5 | comments/points > 0.5 |
| Engagement velocity | 0-10 | Capped at 10 (vs 15 for Reddit) |

### Engagement Velocity

Velocity = `(score + comments * 2) / age_hours`. Minimum age: 0.5 hours (avoids division issues on brand-new posts).

| Velocity | Bonus |
|----------|-------|
| >= 50 | +15 (viral) |
| >= 20 | +10 (hot) |
| >= 10 | +7 (rising) |
| >= 5 | +4 (active) |
| >= 2 | +2 (moderate) |
| < 2 | 0 |

## Classification

After scoring, content is classified into one category via `classify_content()` in `src/signalsift/processing/classification.py`. Classification uses keyword category matches to determine content type.

| Category Key | Report Section |
|-------------|---------------|
| `pain_point` | Pain Points |
| `success_story` | Success Stories |
| `tool_comparison` | Tool Mentions |
| `monetization` / `roi_analysis` / `ecommerce` | Monetization Insights |
| `ai_visibility` | AI Visibility Insights |
| `keyword_research` / `local_seo` | Keyword Research Insights |
| `ai_content` | Content Generation Insights |
| `competitor_analysis` / `content_brief` | Competition Insights |

## Minimum Score Threshold

Content below `scoring.min_relevance_score` (default: 20) is stored in the database but **excluded from reports**. Override per-report with `sift report --min-score N`.

## Business Rules

- **Scores are computed at scan time** and stored in `relevance_score` column. Re-scanning the same content does not update scores (INSERT OR IGNORE deduplication).
- **Source tier is looked up dynamically** at scoring time from the `sources` table and cached per source_type for the duration of the process (via `lru_cache`), so batch scoring incurs only 1 DB query per source type instead of N. If a source isn't found, defaults to tier 2 (medium).
- **Keyword weight multiplies each match** — setting a keyword weight to 2.0 doubles its contribution to the score.
- **YouTube defaults tier 1** in `process_youtube_video()` — YouTube sources get the highest tier bonus unless explicitly set lower.
- **Score stored as REAL** in the database (float). Displayed as integer in reports (`round(relevance_score)`).

## Edge Cases

- **Zero engagement:** A post with 0 upvotes and 0 comments can still score via keywords and quality signals.
- **Very new content:** Velocity calculation uses a 0.5-hour minimum age to avoid artificially inflated scores on brand-new posts.
- **Missing content fields:** `selftext` and `transcript` default to empty string for scoring purposes — no crash on None.

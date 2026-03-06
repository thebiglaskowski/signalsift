---
feature: Keywords Management
version: "1.0"
last_updated: 2026-03-06
dependencies:
  - "01-database-config.md"
routes:
  - "CLI: sift keywords list [--category CAT] [--all]"
  - "CLI: sift keywords add <keyword> --category CAT [--weight N]"
  - "CLI: sift keywords remove <keyword> [--force]"
  - "CLI: sift keywords categories"
status: draft
---

# Keywords Management

> Manages the set of tracked keywords used to score and classify content during scans. Keywords drive relevance scoring and category classification.

## Data Model

### `keywords` table

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | INTEGER | primary key, autoincrement | Auto-generated |
| `keyword` | TEXT | NOT NULL | Stored lowercase |
| `category` | TEXT | NOT NULL | One of the defined categories |
| `weight` | REAL | default 1.0 | Multiplier in scoring (higher = more impact) |
| `enabled` | INTEGER | default 1 | Boolean (0/1) |

**Unique constraint:** `(keyword, category)` — same keyword can exist in multiple categories.

**Pydantic model:** `Keyword` in `src/signalsift/database/models.py`

## CLI Commands

### `sift keywords list`

Lists keywords grouped by category in Rich tables. Shows keyword, weight, and enabled status.

**Options:**
- `--category TEXT`: Filter to a specific category
- `--all`: Show disabled keywords too

**Sort:** Within each category, keywords are sorted by weight descending.

### `sift keywords add <keyword> --category CAT`

Adds a new keyword. `keyword` is stored lowercase.

**Options:**
- `--category TEXT`: Required. One of the defined categories.
- `--weight FLOAT`: Scoring weight multiplier (default: 1.0)

### `sift keywords remove <keyword>`

Removes a keyword. Prompts for confirmation unless `--force`.

**Note:** Removes by keyword text alone — if the same keyword exists in multiple categories, all instances are removed (TODO: confirm this behavior).

### `sift keywords categories`

Lists all available keyword categories with descriptions.

## Keyword Categories

| Category | Description |
|----------|-------------|
| `success_signals` | Indicators of successful strategies or results |
| `pain_points` | User frustrations and problems to solve |
| `tool_mentions` | SEO tools and software references |
| `techniques` | SEO methods and strategies |
| `monetization` | Revenue and monetization discussions |
| `ai_visibility` | AI search and GEO optimization |
| `content_generation` | AI content and automation |

## Business Rules

- **Keywords drive scoring:** During `sift scan`, each piece of content is matched against all enabled keywords. Each match contributes `min(count, 3) * weight * 5` points to the relevance score (capped at 35 points total for Reddit/HN, same cap for YouTube but multiplier is 3).
- **Keyword matching uses semantic expansion:** The `KeywordMatcher` in `src/signalsift/processing/keywords.py` uses spaCy for semantic similarity — a keyword like "startup" can match related terms like "bootstrapped" or "side project". Requires `en_core_web_md` spaCy model. Falls back to exact/substring matching if spaCy is unavailable.
- **FAISS acceleration:** If `faiss-cpu` is installed, semantic matching uses FAISS for 10-100x speedup over brute-force cosine similarity.
- **Category affects classification:** After scoring, content is classified into a category based on which keyword categories matched. Classification determines which report section the content appears in.
- **Default keywords:** `sift init` populates a default set of keywords across all categories. Customize by adding/removing via CLI.
- **Weight range:** No enforced min/max. Typical range is 0.5 (low signal) to 2.0 (high signal). Default is 1.0.

## Edge Cases

- **Keyword stored lowercase:** `keyword.lower()` is applied before storage. `add_keyword_cmd` normalizes input.
- **Duplicate add:** `add_keyword()` uses `INSERT OR IGNORE` — adding an existing (keyword, category) pair silently does nothing.
- **Disabled keywords:** Disabled keywords are excluded from matching during scans. Use `--all` to view them.
- **Missing spaCy model:** If `en_core_web_md` is not installed, semantic matching degrades to substring matching. Run `uv run python -m spacy download en_core_web_md` to install.

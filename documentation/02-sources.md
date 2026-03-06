---
feature: Sources Management
version: "1.0"
last_updated: 2026-03-06
dependencies:
  - "01-database-config.md"
routes:
  - "CLI: sift sources list [--all]"
  - "CLI: sift sources add <reddit|youtube> <source_id> [--name NAME] [--tier 1|2|3]"
  - "CLI: sift sources enable <reddit|youtube> <source_id>"
  - "CLI: sift sources disable <reddit|youtube> <source_id>"
  - "CLI: sift sources remove <reddit|youtube> <source_id> [--force]"
status: draft
---

# Sources Management

> Manages the list of subreddits and YouTube channels that SignalSift scans for content.

## Data Model

### `sources` table

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | INTEGER | primary key, autoincrement | Auto-generated |
| `source_type` | TEXT | NOT NULL | `"reddit"` or `"youtube"` |
| `source_id` | TEXT | NOT NULL | Subreddit name (e.g., `"seo"`) or YouTube channel ID |
| `display_name` | TEXT | nullable | Human-readable name shown in CLI output |
| `tier` | INTEGER | default 2 | Priority: 1=high, 2=medium, 3=low |
| `enabled` | INTEGER | default 1 | Boolean (0/1) |
| `last_fetched` | INTEGER | nullable | Unix timestamp of last successful fetch |

**Unique constraint:** `(source_type, source_id)` — no duplicate source entries.

**Pydantic model:** `Source` in `src/signalsift/database/models.py`

## CLI Commands

### `sift sources list`

Lists all enabled sources in separate Rich tables (Reddit Subreddits / YouTube Channels).

**Options:**
- `--all`: Show disabled sources too

**Output columns (Reddit):** Subreddit name (`r/<id>`), Tier, Status (checkmark), Last Fetched datetime
**Output columns (YouTube):** Display name, Channel ID (truncated at 15 chars), Tier, Status, Last Fetched

### `sift sources add <source_type> <source_id>`

Adds a new source. Defaults: `display_name` auto-set to `r/<id>` for Reddit or `<id>` for YouTube.

**Options:**
- `--name TEXT`: Override display name
- `--tier 1|2|3`: Priority tier (default: 2)

### `sift sources enable/disable <source_type> <source_id>`

Toggles the `enabled` flag. Disabled sources are skipped during scans.

### `sift sources remove <source_type> <source_id>`

Removes a source permanently from the database. Prompts for confirmation unless `--force`.

## Business Rules

- **Tier affects scoring:** Source tier feeds into relevance scoring bonuses. Tier 1 Reddit sources get +10 points; tier 2 get +5. Tier 1 YouTube sources get +15; tier 2 get +8. Tier 3 gets no bonus.
- **Default sources:** `sift init` populates a set of default subreddits and YouTube channels. These can be managed with these commands.
- **source_id for Reddit:** Use the subreddit name without `r/` prefix (e.g., `seo`, `bigseo`, `juststart`).
- **source_id for YouTube:** Use the YouTube channel ID (e.g., `UCVtuekEIwdVQTK7RmxcKAUg`), not the handle.
- **Disabled vs removed:** Prefer `disable` over `remove` to preserve scan history associations. Removed sources leave orphaned content in the database.
- **last_fetched:** Updated by the scan command after each successful source fetch. Used for display only — does not control scan window (that's driven by `--days` or `max_age_days`).

## Edge Cases

- **Duplicate add:** `add_source()` uses `INSERT OR IGNORE` — adding an existing source silently does nothing (no error).
- **Remove nonexistent:** `sift sources remove` will print an error if the source doesn't exist.
- **No YouTube without API key:** YouTube sources are stored in the database regardless of whether `YOUTUBE_API_KEY` is set. They'll just be skipped during scans with a warning.

---
feature: Cache Management
version: "1.0"
last_updated: 2026-03-06
dependencies:
  - "01-database-config.md"
routes:
  - "CLI: sift cache stats"
  - "CLI: sift cache prune --older-than N [--force]"
  - "CLI: sift cache reset-processed [--force]"
  - "CLI: sift cache export <output_path>"
  - "CLI: sift cache clear --confirm"
status: draft
---

# Cache Management

> Utilities for inspecting, pruning, resetting, exporting, and clearing the local SQLite content cache.

## CLI Commands

### `sift cache stats`

Displays a Rich table with database metrics. No options.

**Output columns:**

| Row | Source |
|-----|--------|
| Database path | `settings.database.path` |
| Database size | File size via `Path.stat().st_size`, formatted (e.g., `12.4 MB`) |
| Reddit threads (total) | `get_cache_stats()["reddit_total"]` |
| Reddit threads (unprocessed) | `get_cache_stats()["reddit_unprocessed"]` |
| YouTube videos (total) | `get_cache_stats()["youtube_total"]` |
| YouTube videos (unprocessed) | `get_cache_stats()["youtube_unprocessed"]` |
| Reports generated | `get_cache_stats()["reports_total"]` |

### `sift cache prune --older-than N`

Deletes **processed** content older than N days from both `reddit_threads` and `youtube_videos` tables.

**Options:**
- `--older-than N` (required): Age threshold in days
- `--force`: Skip confirmation prompt

**Behavior:** Prompts for confirmation unless `--force`. Calls `prune_old_content(older_than)` which returns `(reddit_deleted, youtube_deleted)` counts. Only deletes rows where `processed = 1` — unprocessed content is never pruned.

### `sift cache reset-processed`

Resets the `processed` flag to `0` on all content in both tables, allowing it to be included in future reports again.

**Options:**
- `--force`: Skip confirmation prompt

**Returns:** Count of items reset. Calls `reset_processed_flags()`.

**Use case:** Re-run a report with the same content pool, or recover from accidentally processing content in preview mode that shouldn't have been consumed.

### `sift cache export <output_path>`

Exports the full content cache to a JSON file.

**Arguments:**
- `output_path` (required): Destination path for the JSON export

**Behavior:** Calls `export_cache_to_json()` and writes the result as pretty-printed JSON (`indent=2`). Creates parent directories if they don't exist. Non-serializable types use `str()` fallback via `json.dumps(default=str)`.

### `sift cache clear --confirm`

Deletes **all** cached content from both `reddit_threads` and `youtube_videos` tables. Destructive.

**Options:**
- `--confirm` (required flag): Must be explicitly passed to proceed

**Behavior:** Even with `--confirm`, prompts a second confirmation (`click.confirm`). Calls `clear_all_content()` which returns `(reddit_deleted, youtube_deleted)` counts.

**Note:** This does NOT drop tables or reset the schema — only deletes row data. Keywords, sources, and reports metadata are untouched.

## Business Rules

- **Prune only affects processed content:** `prune_old_content()` filters by `processed = 1` before deleting. Unprocessed content (not yet in any report) is never deleted by prune.
- **Clear affects all content:** `clear_all_content()` deletes regardless of processed status. This is why it requires both `--confirm` flag and an interactive prompt.
- **HackerNews not tracked in stats:** `get_cache_stats()` only reports Reddit and YouTube counts. HackerNews items are stored in `hackernews_items` table but not surfaced in cache stats output.
- **Export includes all content:** `export_cache_to_json()` exports all content regardless of processed status. Format is determined by the query implementation.
- **Reset-processed enables re-reporting:** After resetting processed flags, `sift report` will include that content again as if it were fresh. This does not change `report_id` associations — the `reports` table still records prior report history.

## Edge Cases

- **Prune with 0 days:** Calling `prune --older-than 0` would delete all processed content (any age). The CLI does not enforce a minimum.
- **Clear on empty database:** `clear_all_content()` with no rows silently succeeds, returning `(0, 0)`.
- **Export path with missing parents:** `output_path.parent.mkdir(parents=True, exist_ok=True)` is called before writing — intermediate directories are created automatically.
- **Database not initialized:** If the database doesn't exist, these commands will fail. Run `sift init` first. (Auto-init on first command handles this for the main CLI flow.)

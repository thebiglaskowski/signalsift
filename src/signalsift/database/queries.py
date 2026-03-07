"""Database query functions for SignalSift."""

import json
from datetime import datetime, timedelta
from typing import Any

from signalsift.database.connection import get_connection
from signalsift.database.models import (
    HackerNewsItem,
    Keyword,
    ProcessingLogEntry,
    RedditThread,
    Report,
    Source,
    YouTubeVideo,
)

# =============================================================================
# Reddit Thread Queries
# =============================================================================


def thread_exists(thread_id: str) -> bool:
    """Check if a Reddit thread already exists in the cache."""
    with get_connection() as conn:
        cursor = conn.execute("SELECT 1 FROM reddit_threads WHERE id = ?", (thread_id,))
        return cursor.fetchone() is not None


def insert_reddit_thread(thread: RedditThread) -> None:
    """Insert a new Reddit thread into the cache."""
    with get_connection() as conn:
        data = thread.to_db_dict()
        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" * len(data))
        conn.execute(
            f"INSERT OR REPLACE INTO reddit_threads ({columns}) VALUES ({placeholders})",
            tuple(data.values()),
        )


def insert_reddit_threads_batch(threads: list[RedditThread]) -> int:
    """
    Insert multiple Reddit threads in a single transaction.

    Args:
        threads: List of RedditThread models to insert.

    Returns:
        Number of threads inserted.
    """
    if not threads:
        return 0

    with get_connection() as conn:
        # Get column structure from first thread
        first_data = threads[0].to_db_dict()
        columns = ", ".join(first_data.keys())
        placeholders = ", ".join("?" * len(first_data))

        # Prepare all data
        all_data = [tuple(t.to_db_dict().values()) for t in threads]

        conn.executemany(
            f"INSERT OR REPLACE INTO reddit_threads ({columns}) VALUES ({placeholders})",
            all_data,
        )
        return len(threads)


def get_reddit_threads(
    subreddits: list[str] | None = None,
    since_timestamp: int | None = None,
    min_score: float | None = None,
    processed: bool | None = None,
    limit: int | None = None,
) -> list[RedditThread]:
    """
    Get Reddit threads with optional filters.

    Args:
        subreddits: Filter by specific subreddits.
        since_timestamp: Only get threads created after this timestamp.
        min_score: Only get threads with relevance_score >= this value.
        processed: Filter by processed status (True/False/None for all).
        limit: Maximum number of threads to return.
    """
    query = "SELECT * FROM reddit_threads WHERE 1=1"
    params: list[Any] = []

    if subreddits:
        placeholders = ", ".join("?" * len(subreddits))
        query += f" AND subreddit IN ({placeholders})"
        params.extend(subreddits)

    if since_timestamp:
        query += " AND created_utc >= ?"
        params.append(since_timestamp)

    if min_score is not None:
        query += " AND relevance_score >= ?"
        params.append(min_score)

    if processed is not None:
        query += " AND processed = ?"
        params.append(1 if processed else 0)

    query += " ORDER BY relevance_score DESC, created_utc DESC"

    if limit:
        query += " LIMIT ?"
        params.append(limit)

    with get_connection() as conn:
        cursor = conn.execute(query, params)
        return [RedditThread(**dict(row)) for row in cursor.fetchall()]


# =============================================================================
# YouTube Video Queries
# =============================================================================


def video_exists(video_id: str) -> bool:
    """Check if a YouTube video already exists in the cache."""
    with get_connection() as conn:
        cursor = conn.execute("SELECT 1 FROM youtube_videos WHERE id = ?", (video_id,))
        return cursor.fetchone() is not None


def insert_youtube_video(video: YouTubeVideo) -> None:
    """Insert a new YouTube video into the cache."""
    with get_connection() as conn:
        data = video.to_db_dict()
        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" * len(data))
        conn.execute(
            f"INSERT OR REPLACE INTO youtube_videos ({columns}) VALUES ({placeholders})",
            tuple(data.values()),
        )


def insert_youtube_videos_batch(videos: list[YouTubeVideo]) -> int:
    """
    Insert multiple YouTube videos in a single transaction.

    Args:
        videos: List of YouTubeVideo models to insert.

    Returns:
        Number of videos inserted.
    """
    if not videos:
        return 0

    with get_connection() as conn:
        # Get column structure from first video
        first_data = videos[0].to_db_dict()
        columns = ", ".join(first_data.keys())
        placeholders = ", ".join("?" * len(first_data))

        # Prepare all data
        all_data = [tuple(v.to_db_dict().values()) for v in videos]

        conn.executemany(
            f"INSERT OR REPLACE INTO youtube_videos ({columns}) VALUES ({placeholders})",
            all_data,
        )
        return len(videos)


def get_youtube_videos(
    channel_ids: list[str] | None = None,
    since_timestamp: int | None = None,
    min_score: float | None = None,
    processed: bool | None = None,
    limit: int | None = None,
) -> list[YouTubeVideo]:
    """
    Get YouTube videos with optional filters.

    Args:
        channel_ids: Filter by specific channel IDs.
        since_timestamp: Only get videos published after this timestamp.
        min_score: Only get videos with relevance_score >= this value.
        processed: Filter by processed status (True/False/None for all).
        limit: Maximum number of videos to return.
    """
    query = "SELECT * FROM youtube_videos WHERE 1=1"
    params: list[Any] = []

    if channel_ids:
        placeholders = ", ".join("?" * len(channel_ids))
        query += f" AND channel_id IN ({placeholders})"
        params.extend(channel_ids)

    if since_timestamp:
        query += " AND published_at >= ?"
        params.append(since_timestamp)

    if min_score is not None:
        query += " AND relevance_score >= ?"
        params.append(min_score)

    if processed is not None:
        query += " AND processed = ?"
        params.append(1 if processed else 0)

    query += " ORDER BY relevance_score DESC, published_at DESC"

    if limit:
        query += " LIMIT ?"
        params.append(limit)

    with get_connection() as conn:
        cursor = conn.execute(query, params)
        return [YouTubeVideo(**dict(row)) for row in cursor.fetchall()]


# =============================================================================
# Hacker News Queries
# =============================================================================


def hackernews_exists(item_id: str) -> bool:
    """Check if a Hacker News item already exists in the cache."""
    with get_connection() as conn:
        cursor = conn.execute("SELECT 1 FROM hackernews_items WHERE id = ?", (item_id,))
        return cursor.fetchone() is not None


def insert_hackernews_item(item: HackerNewsItem | dict) -> None:
    """Insert a new Hacker News item into the cache."""
    with get_connection() as conn:
        # Support both model and dict (for backwards compatibility)
        if isinstance(item, HackerNewsItem):
            data = item.to_db_dict()
        else:
            data = item.copy()
            # Convert matched_keywords list to JSON
            if "matched_keywords" in data and isinstance(data["matched_keywords"], list):
                data["matched_keywords"] = json.dumps(data["matched_keywords"])

        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" * len(data))
        conn.execute(
            f"INSERT OR REPLACE INTO hackernews_items ({columns}) VALUES ({placeholders})",
            tuple(data.values()),
        )


def insert_hackernews_items_batch(items: list[HackerNewsItem | dict]) -> int:
    """
    Insert multiple Hacker News items in a single transaction.

    Args:
        items: List of HackerNewsItem models or dicts to insert.

    Returns:
        Number of items inserted.
    """
    if not items:
        return 0

    with get_connection() as conn:
        all_data = []
        columns = None
        placeholders = None

        for item in items:
            if isinstance(item, HackerNewsItem):
                data = item.to_db_dict()
            else:
                data = item.copy()
                if "matched_keywords" in data and isinstance(data["matched_keywords"], list):
                    data["matched_keywords"] = json.dumps(data["matched_keywords"])

            if columns is None:
                columns = ", ".join(data.keys())
                placeholders = ", ".join("?" * len(data))

            all_data.append(tuple(data.values()))

        if columns and all_data:
            conn.executemany(
                f"INSERT OR REPLACE INTO hackernews_items ({columns}) VALUES ({placeholders})",
                all_data,
            )
        return len(items)


def get_hackernews_items(
    since_timestamp: int | None = None,
    min_score: float | None = None,
    processed: bool | None = None,
    story_type: str | None = None,
    limit: int | None = None,
) -> list[HackerNewsItem]:
    """
    Get Hacker News items with optional filters.

    Args:
        since_timestamp: Only get items created after this timestamp.
        min_score: Only get items with relevance_score >= this value.
        processed: Filter by processed status.
        story_type: Filter by story type (story, ask_hn, show_hn).
        limit: Maximum number of items to return.

    Returns:
        List of HackerNewsItem models.
    """
    query = "SELECT * FROM hackernews_items WHERE 1=1"
    params: list[Any] = []

    if since_timestamp:
        query += " AND created_utc >= ?"
        params.append(since_timestamp)

    if min_score is not None:
        query += " AND relevance_score >= ?"
        params.append(min_score)

    if processed is not None:
        query += " AND processed = ?"
        params.append(1 if processed else 0)

    if story_type:
        query += " AND story_type = ?"
        params.append(story_type)

    query += " ORDER BY relevance_score DESC, created_utc DESC"

    if limit:
        query += " LIMIT ?"
        params.append(limit)

    with get_connection() as conn:
        cursor = conn.execute(query, params)
        return [HackerNewsItem(**dict(row)) for row in cursor.fetchall()]


# =============================================================================
# Unified Content Queries
# =============================================================================


def get_unprocessed_content(
    min_score: float | None = None,
    since_days: int | None = None,
    reddit_limit: int | None = None,
    youtube_limit: int | None = None,
) -> tuple[list[RedditThread], list[YouTubeVideo]]:
    """
    Get all unprocessed content (Reddit threads and YouTube videos).

    Args:
        min_score: Minimum relevance score to include.
        since_days: Only include content from the last N days.
        reddit_limit: Max Reddit threads to return.
        youtube_limit: Max YouTube videos to return.

    Returns:
        Tuple of (reddit_threads, youtube_videos)
    """
    since_timestamp = None
    if since_days:
        since_timestamp = int((datetime.now() - timedelta(days=since_days)).timestamp())

    threads = get_reddit_threads(
        since_timestamp=since_timestamp,
        min_score=min_score,
        processed=False,
        limit=reddit_limit,
    )

    videos = get_youtube_videos(
        since_timestamp=since_timestamp,
        min_score=min_score,
        processed=False,
        limit=youtube_limit,
    )

    return threads, videos


def mark_content_processed(
    report_id: str,
    thread_ids: list[str] | None = None,
    video_ids: list[str] | None = None,
) -> None:
    """Mark content as processed and associate with a report."""
    with get_connection() as conn:
        if thread_ids:
            placeholders = ", ".join("?" * len(thread_ids))
            conn.execute(
                f"UPDATE reddit_threads SET processed = 1, report_id = ? WHERE id IN ({placeholders})",
                [report_id] + thread_ids,
            )

        if video_ids:
            placeholders = ", ".join("?" * len(video_ids))
            conn.execute(
                f"UPDATE youtube_videos SET processed = 1, report_id = ? WHERE id IN ({placeholders})",
                [report_id] + video_ids,
            )


def reset_processed_flags() -> int:
    """Reset processed flags on all content. Returns count of items reset."""
    with get_connection() as conn:
        cursor = conn.execute(
            "UPDATE reddit_threads SET processed = 0, report_id = NULL WHERE processed = 1"
        )
        reddit_count = cursor.rowcount

        cursor = conn.execute(
            "UPDATE youtube_videos SET processed = 0, report_id = NULL WHERE processed = 1"
        )
        youtube_count = cursor.rowcount

        return reddit_count + youtube_count


# =============================================================================
# Source Queries
# =============================================================================


def get_sources_by_type(source_type: str, enabled_only: bool = True) -> list[Source]:
    """Get sources by type (reddit or youtube)."""
    query = "SELECT * FROM sources WHERE source_type = ?"
    params: list[Any] = [source_type]

    if enabled_only:
        query += " AND enabled = 1"

    query += " ORDER BY tier ASC, display_name ASC"

    with get_connection() as conn:
        cursor = conn.execute(query, params)
        return [Source(**dict(row)) for row in cursor.fetchall()]


def get_all_sources(enabled_only: bool = True) -> list[Source]:
    """Get all sources."""
    query = "SELECT * FROM sources"
    if enabled_only:
        query += " WHERE enabled = 1"
    query += " ORDER BY source_type, tier ASC, display_name ASC"

    with get_connection() as conn:
        cursor = conn.execute(query)
        return [Source(**dict(row)) for row in cursor.fetchall()]


def add_source(source: Source) -> None:
    """Add a new source."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO sources (source_type, source_id, display_name, tier, enabled)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                source.source_type,
                source.source_id,
                source.display_name,
                source.tier,
                1 if source.enabled else 0,
            ),
        )


def update_source_last_fetched(source_type: str, source_id: str) -> None:
    """Update the last_fetched timestamp for a source."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE sources SET last_fetched = ? WHERE source_type = ? AND source_id = ?",
            (int(datetime.now().timestamp()), source_type, source_id),
        )


def toggle_source(source_type: str, source_id: str, enabled: bool) -> None:
    """Enable or disable a source."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE sources SET enabled = ? WHERE source_type = ? AND source_id = ?",
            (1 if enabled else 0, source_type, source_id),
        )


def remove_source(source_type: str, source_id: str) -> bool:
    """Remove a source. Returns True if source was found and removed."""
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM sources WHERE source_type = ? AND source_id = ?",
            (source_type, source_id),
        )
        return cursor.rowcount > 0


# =============================================================================
# Keyword Queries
# =============================================================================


def get_keywords_by_category(
    category: str | None = None, enabled_only: bool = True
) -> list[Keyword]:
    """Get keywords, optionally filtered by category."""
    query = "SELECT * FROM keywords WHERE 1=1"
    params: list[Any] = []

    if category:
        query += " AND category = ?"
        params.append(category)

    if enabled_only:
        query += " AND enabled = 1"

    query += " ORDER BY category, weight DESC, keyword"

    with get_connection() as conn:
        cursor = conn.execute(query, params)
        return [Keyword(**dict(row)) for row in cursor.fetchall()]


def get_all_keywords(enabled_only: bool = True) -> list[Keyword]:
    """Get all keywords."""
    return get_keywords_by_category(category=None, enabled_only=enabled_only)


def add_keyword(keyword: Keyword) -> None:
    """Add a new keyword."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO keywords (keyword, category, weight, enabled)
            VALUES (?, ?, ?, ?)
            """,
            (keyword.keyword, keyword.category, keyword.weight, 1 if keyword.enabled else 0),
        )


def remove_keyword(keyword_text: str) -> bool:
    """Remove a keyword. Returns True if keyword was found and removed."""
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM keywords WHERE keyword = ?", (keyword_text,))
        return cursor.rowcount > 0


# =============================================================================
# Report Queries
# =============================================================================


def insert_report(report: Report) -> None:
    """Insert a new report record."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO reports (id, generated_at, filepath, reddit_count, youtube_count,
                                date_range_start, date_range_end, config_snapshot)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report.id,
                report.generated_at,
                report.filepath,
                report.reddit_count,
                report.youtube_count,
                report.date_range_start,
                report.date_range_end,
                report.config_snapshot,
            ),
        )


def get_reports(limit: int = 10) -> list[Report]:
    """Get recent reports."""
    with get_connection() as conn:
        cursor = conn.execute("SELECT * FROM reports ORDER BY generated_at DESC LIMIT ?", (limit,))
        return [Report(**dict(row)) for row in cursor.fetchall()]


def get_latest_report() -> Report | None:
    """Get the most recent report."""
    reports = get_reports(limit=1)
    return reports[0] if reports else None


# =============================================================================
# Cache Statistics
# =============================================================================


def get_cache_stats() -> dict[str, Any]:
    """Get statistics about the cache."""
    with get_connection() as conn:
        stats: dict[str, Any] = {}

        # Reddit stats
        cursor = conn.execute("SELECT COUNT(*) FROM reddit_threads")
        stats["reddit_total"] = cursor.fetchone()[0]

        cursor = conn.execute("SELECT COUNT(*) FROM reddit_threads WHERE processed = 0")
        stats["reddit_unprocessed"] = cursor.fetchone()[0]

        cursor = conn.execute("SELECT MAX(captured_at) FROM reddit_threads")
        result = cursor.fetchone()[0]
        stats["reddit_last_scan"] = datetime.fromtimestamp(result) if result else None

        # YouTube stats
        cursor = conn.execute("SELECT COUNT(*) FROM youtube_videos")
        stats["youtube_total"] = cursor.fetchone()[0]

        cursor = conn.execute("SELECT COUNT(*) FROM youtube_videos WHERE processed = 0")
        stats["youtube_unprocessed"] = cursor.fetchone()[0]

        cursor = conn.execute("SELECT MAX(captured_at) FROM youtube_videos")
        result = cursor.fetchone()[0]
        stats["youtube_last_scan"] = datetime.fromtimestamp(result) if result else None

        # Source stats
        cursor = conn.execute("SELECT COUNT(*) FROM sources WHERE source_type = 'reddit'")
        stats["reddit_sources"] = cursor.fetchone()[0]

        cursor = conn.execute(
            "SELECT COUNT(*) FROM sources WHERE source_type = 'reddit' AND enabled = 1"
        )
        stats["reddit_sources_enabled"] = cursor.fetchone()[0]

        cursor = conn.execute("SELECT COUNT(*) FROM sources WHERE source_type = 'youtube'")
        stats["youtube_sources"] = cursor.fetchone()[0]

        cursor = conn.execute(
            "SELECT COUNT(*) FROM sources WHERE source_type = 'youtube' AND enabled = 1"
        )
        stats["youtube_sources_enabled"] = cursor.fetchone()[0]

        # Report stats
        cursor = conn.execute("SELECT COUNT(*) FROM reports")
        stats["reports_total"] = cursor.fetchone()[0]

        cursor = conn.execute(
            "SELECT filepath, generated_at FROM reports ORDER BY generated_at DESC LIMIT 1"
        )
        result = cursor.fetchone()
        if result:
            stats["last_report_path"] = result[0]
            stats["last_report_date"] = datetime.fromtimestamp(result[1])
        else:
            stats["last_report_path"] = None
            stats["last_report_date"] = None

        return stats


# =============================================================================
# Processing Log
# =============================================================================


def log_processing_action(entry: ProcessingLogEntry) -> None:
    """Log a processing action."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO processing_log (timestamp, action, source_type, source_id, details)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                entry.timestamp,
                entry.action,
                entry.source_type,
                entry.source_id,
                entry.details,
            ),
        )


# =============================================================================
# Cache Management
# =============================================================================


def prune_old_content(older_than_days: int) -> tuple[int, int]:
    """
    Delete processed content older than specified days.

    Returns:
        Tuple of (reddit_deleted, youtube_deleted)
    """
    cutoff = int((datetime.now() - timedelta(days=older_than_days)).timestamp())

    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM reddit_threads WHERE processed = 1 AND captured_at < ?",
            (cutoff,),
        )
        reddit_deleted = cursor.rowcount

        cursor = conn.execute(
            "DELETE FROM youtube_videos WHERE processed = 1 AND captured_at < ?",
            (cutoff,),
        )
        youtube_deleted = cursor.rowcount

        return reddit_deleted, youtube_deleted


def clear_all_content() -> tuple[int, int]:
    """
    Delete all cached content.

    Returns:
        Tuple of (reddit_deleted, youtube_deleted)
    """
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM reddit_threads")
        reddit_deleted = cursor.rowcount

        cursor = conn.execute("DELETE FROM youtube_videos")
        youtube_deleted = cursor.rowcount

        return reddit_deleted, youtube_deleted


def export_cache_to_json() -> dict[str, Any]:
    """Export all cached content to a JSON-serializable dictionary."""
    with get_connection() as conn:
        # Reddit threads
        cursor = conn.execute("SELECT * FROM reddit_threads")
        reddit_threads = [dict(row) for row in cursor.fetchall()]

        # YouTube videos
        cursor = conn.execute("SELECT * FROM youtube_videos")
        youtube_videos = [dict(row) for row in cursor.fetchall()]

        # Reports
        cursor = conn.execute("SELECT * FROM reports")
        reports = [dict(row) for row in cursor.fetchall()]

        # Sources
        cursor = conn.execute("SELECT * FROM sources")
        sources = [dict(row) for row in cursor.fetchall()]

        # Keywords
        cursor = conn.execute("SELECT * FROM keywords")
        keywords = [dict(row) for row in cursor.fetchall()]

        return {
            "exported_at": datetime.now().isoformat(),
            "reddit_threads": reddit_threads,
            "youtube_videos": youtube_videos,
            "reports": reports,
            "sources": sources,
            "keywords": keywords,
        }

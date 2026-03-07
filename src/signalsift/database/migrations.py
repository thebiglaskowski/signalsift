"""Simple database migration system for SignalSift.

This module provides a lightweight migration system for tracking and applying
schema changes to the SQLite database.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from signalsift.database.connection import get_connection
from signalsift.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Migration:
    """Represents a database migration."""

    version: int
    name: str
    up: Callable[[sqlite3.Connection], None]
    down: Callable[[sqlite3.Connection], None] | None = None


# Migration registry
_migrations: list[Migration] = []


def migration(version: int, name: str) -> Callable:
    """
    Decorator to register a migration.

    Usage:
        @migration(1, "add_hackernews_indexes")
        def migrate_v1(conn):
            conn.execute("CREATE INDEX ...")
    """

    def decorator(func: Callable[[sqlite3.Connection], None]) -> Callable:
        _migrations.append(Migration(version=version, name=name, up=func))
        return func

    return decorator


MIGRATIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TEXT NOT NULL
);
"""


def ensure_migrations_table(conn: sqlite3.Connection) -> None:
    """Create the migrations tracking table if it doesn't exist."""
    conn.execute(MIGRATIONS_SCHEMA)
    conn.commit()


def get_current_version(conn: sqlite3.Connection) -> int:
    """Get the current schema version."""
    ensure_migrations_table(conn)
    cursor = conn.execute("SELECT MAX(version) FROM schema_migrations")
    result = cursor.fetchone()[0]
    return result if result is not None else 0


def get_applied_migrations(conn: sqlite3.Connection) -> list[int]:
    """Get list of applied migration versions."""
    ensure_migrations_table(conn)
    cursor = conn.execute("SELECT version FROM schema_migrations ORDER BY version")
    return [row[0] for row in cursor.fetchall()]


def apply_migration(conn: sqlite3.Connection, mig: Migration) -> None:
    """Apply a single migration."""
    logger.info(f"Applying migration {mig.version}: {mig.name}")

    try:
        mig.up(conn)
        conn.execute(
            "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)",
            (mig.version, mig.name, datetime.now().isoformat()),
        )
        conn.commit()
        logger.info(f"Migration {mig.version} applied successfully")
    except Exception as e:
        conn.rollback()
        logger.error(f"Migration {mig.version} failed: {e}")
        raise


def migrate(target_version: int | None = None) -> int:
    """
    Run all pending migrations up to target version.

    Args:
        target_version: Version to migrate to. None = latest.

    Returns:
        Number of migrations applied.
    """
    # Sort migrations by version
    sorted_migrations = sorted(_migrations, key=lambda m: m.version)

    if target_version is None and sorted_migrations:
        target_version = sorted_migrations[-1].version

    applied_count = 0

    with get_connection() as conn:
        current = get_current_version(conn)
        applied = set(get_applied_migrations(conn))

        logger.info(f"Current schema version: {current}")
        if target_version is not None:
            logger.info(f"Target schema version: {target_version}")

        for mig in sorted_migrations:
            if mig.version in applied:
                continue

            if target_version is not None and mig.version > target_version:
                break

            apply_migration(conn, mig)
            applied_count += 1

    if applied_count == 0:
        logger.info("Database is up to date")
    else:
        logger.info(f"Applied {applied_count} migration(s)")

    return applied_count


def get_pending_migrations() -> list[Migration]:
    """Get list of pending migrations."""
    sorted_migrations = sorted(_migrations, key=lambda m: m.version)

    with get_connection() as conn:
        applied = set(get_applied_migrations(conn))

    return [m for m in sorted_migrations if m.version not in applied]


def migration_status() -> dict:
    """Get migration status information."""
    sorted_migrations = sorted(_migrations, key=lambda m: m.version)

    with get_connection() as conn:
        current = get_current_version(conn)
        applied = set(get_applied_migrations(conn))

    return {
        "current_version": current,
        "latest_version": sorted_migrations[-1].version if sorted_migrations else 0,
        "total_migrations": len(sorted_migrations),
        "applied": len(applied),
        "pending": len([m for m in sorted_migrations if m.version not in applied]),
    }


# =============================================================================
# Define migrations below
# =============================================================================


@migration(1, "initial_schema")
def migrate_v1(conn: sqlite3.Connection) -> None:
    """Initial schema - marks existing databases as migrated.

    This is a baseline migration for existing databases. New databases
    will have the schema created via schema.py, this just marks them
    as being at version 1.
    """
    # No-op - schema is already created by initialize_database()
    pass


@migration(2, "add_hackernews_indexes")
def migrate_v2(conn: sqlite3.Connection) -> None:
    """Add additional indexes for HackerNews queries."""
    conn.execute("CREATE INDEX IF NOT EXISTS idx_hn_story_type ON hackernews_items(story_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_hn_points ON hackernews_items(points)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_hn_created_utc ON hackernews_items(created_utc)")


@migration(3, "add_content_indexes")
def migrate_v3(conn: sqlite3.Connection) -> None:
    """Add indexes for common content queries."""
    # Reddit indexes
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_reddit_subreddit_score "
        "ON reddit_threads(subreddit, relevance_score DESC)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_reddit_category " "ON reddit_threads(category)")

    # YouTube indexes
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_youtube_channel_score "
        "ON youtube_videos(channel_id, relevance_score DESC)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_youtube_category " "ON youtube_videos(category)")


# Future migrations would be added here:
# @migration(4, "add_some_column")
# def migrate_v4(conn: sqlite3.Connection) -> None:
#     conn.execute("ALTER TABLE ... ADD COLUMN ...")

"""Database connection management for SignalSift."""

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from signalsift.config import get_settings
from signalsift.config.defaults import (
    DEFAULT_KEYWORDS,
    DEFAULT_SUBREDDITS,
    DEFAULT_YOUTUBE_CHANNELS,
)
from signalsift.database.schema import get_schema_sql
from signalsift.exceptions import DatabaseError


def get_db_path() -> Path:
    """Get the database path from settings."""
    return get_settings().database.path


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """
    Get a database connection with context management.

    Usage:
        with get_connection() as conn:
            cursor = conn.execute("SELECT * FROM reddit_threads")
            rows = cursor.fetchall()
    """
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row  # Enable dict-like access to rows

    try:
        yield conn
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise DatabaseError(f"Database error: {e}") from e
    finally:
        conn.close()


def initialize_database(populate_defaults: bool = True) -> None:
    """
    Initialize the database with schema and optionally default data.

    Args:
        populate_defaults: Whether to populate default sources and keywords.
    """
    with get_connection() as conn:
        # Execute schema creation
        conn.executescript(get_schema_sql())

        if populate_defaults:
            _populate_default_sources(conn)
            _populate_default_keywords(conn)

    # Run any pending migrations
    from signalsift.database.migrations import migrate

    migrate()


def _populate_default_sources(conn: sqlite3.Connection) -> None:
    """Populate default Reddit subreddits and YouTube channels."""
    # Reddit subreddits
    for tier, subreddits in DEFAULT_SUBREDDITS.items():
        for subreddit in subreddits:
            conn.execute(
                """
                INSERT OR IGNORE INTO sources (source_type, source_id, display_name, tier, enabled)
                VALUES (?, ?, ?, ?, 1)
                """,
                ("reddit", subreddit, f"r/{subreddit}", tier),
            )

    # YouTube channels
    for channel_id, display_name in DEFAULT_YOUTUBE_CHANNELS.items():
        conn.execute(
            """
            INSERT OR IGNORE INTO sources (source_type, source_id, display_name, tier, enabled)
            VALUES (?, ?, ?, 1, 1)
            """,
            ("youtube", channel_id, display_name),
        )


def _populate_default_keywords(conn: sqlite3.Connection) -> None:
    """Populate default tracked keywords with weights based on SignalSift package relevance."""
    # Weight mapping based on category value for identifying SignalSift opportunities
    # Higher weights = more important signals for product enhancement ideas
    category_weights: dict[str, float] = {
        # High-value signals (1.5) - Direct indicators of opportunities
        "success_signals": 1.5,  # Success stories reveal what works
        "pain_points": 1.5,  # Pain points reveal feature gaps
        # Core package signals (1.3) - Primary package relevance
        "monetization": 1.3,  # revenue strategies
        "ai_visibility": 1.3,  # AI search optimization
        "keyword_research": 1.3,  # keyword discovery
        "content_generation": 1.3,  # AI content creation
        "competition": 1.3,  # competitive analysis
        # Supporting signals (1.2) - Secondary relevance
        "tool_mentions": 1.2,  # competitor and tool insights
        "techniques": 1.2,  # tactics and methods
        "image_generation": 1.2,  # visual content
        "static_sites": 1.2,  # site optimization
        "ecommerce": 1.2,  # e-commerce strategies
        # Supplementary signals (1.1) - Broader context
        "local_seo": 1.1,  # local keywords
    }

    for category, keywords in DEFAULT_KEYWORDS.items():
        weight = category_weights.get(category, 1.0)

        for keyword in keywords:
            conn.execute(
                """
                INSERT OR IGNORE INTO keywords (keyword, category, weight, enabled)
                VALUES (?, ?, ?, 1)
                """,
                (keyword, category, weight),
            )


def reset_database() -> None:
    """Reset the database by dropping all tables and reinitializing."""
    db_path = get_db_path()
    if db_path.exists():
        db_path.unlink()
    initialize_database(populate_defaults=True)


def database_exists() -> bool:
    """Check if the database file exists."""
    return get_db_path().exists()

"""Trend detection for SignalSift.

This module provides time-series analysis to detect emerging
and declining trends across scans.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from signalsift.config.defaults import DEFAULT_DB_PATH
from signalsift.processing.keywords import get_matcher
from signalsift.utils.logging import get_logger

if TYPE_CHECKING:
    from signalsift.database.models import RedditThread, YouTubeVideo

logger = get_logger(__name__)


@dataclass
class Trend:
    """A detected trend in content."""

    topic: str  # The keyword/topic
    category: str
    current_count: int
    previous_count: int
    change_percent: float  # Percentage change
    velocity: float  # Rate of change
    direction: str  # "rising", "falling", "stable", "new", "gone"
    avg_engagement: float  # Average engagement for this topic
    sample_titles: list[str]  # Example titles mentioning this topic


@dataclass
class TrendReport:
    """Summary of all trends for a period."""

    period_start: datetime
    period_end: datetime
    comparison_start: datetime
    comparison_end: datetime
    emerging: list[Trend]  # Rising trends
    declining: list[Trend]  # Falling trends
    new_topics: list[Trend]  # Topics that didn't exist in previous period
    gone_topics: list[Trend]  # Topics that disappeared
    stable_hot: list[Trend]  # Consistently popular


# SQL for creating the trends tracking table
TRENDS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS keyword_trends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL,
    category TEXT NOT NULL,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    mention_count INTEGER NOT NULL,
    avg_engagement REAL NOT NULL,
    sample_titles TEXT,  -- JSON array
    created_at TEXT NOT NULL,
    UNIQUE(keyword, period_start, period_end)
)
"""

TRENDS_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_trends_keyword ON keyword_trends(keyword);
CREATE INDEX IF NOT EXISTS idx_trends_period ON keyword_trends(period_start, period_end);
"""


class TrendDetector:
    """Detect trends across content scans."""

    def __init__(
        self,
        db_path: Path | None = None,
        rising_threshold: float = 1.5,
        falling_threshold: float = 0.5,
    ) -> None:
        """
        Initialize the trend detector.

        Args:
            db_path: Path to SQLite database.
            rising_threshold: Multiplier to consider a topic "rising" (1.5 = 50% increase).
            falling_threshold: Multiplier to consider a topic "falling" (0.5 = 50% decrease).
        """
        self.db_path = db_path or DEFAULT_DB_PATH
        self.rising_threshold = rising_threshold
        self.falling_threshold = falling_threshold
        self._ensure_table()

    def _ensure_table(self) -> None:
        """Ensure the trends table exists."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(TRENDS_TABLE_SQL)
                conn.executescript(TRENDS_INDEX_SQL)
                conn.commit()
        except Exception as e:
            logger.warning(f"Could not create trends table: {e}")

    def record_period(
        self,
        threads: list[RedditThread],
        videos: list[YouTubeVideo],
        period_start: datetime,
        period_end: datetime,
    ) -> None:
        """
        Record keyword occurrences for a time period.

        Args:
            threads: Reddit threads from the period.
            videos: YouTube videos from the period.
            period_start: Start of the period.
            period_end: End of the period.
        """
        import json

        # Count keywords across all content
        keyword_data: dict[str, dict] = {}
        matcher = get_matcher()

        # Process threads
        for thread in threads:
            text = (thread.title or "") + " " + (thread.selftext or "")
            matches = matcher.find_matches(text)

            for match in matches:
                key = match.keyword.lower()
                if key not in keyword_data:
                    keyword_data[key] = {
                        "category": match.category,
                        "count": 0,
                        "total_engagement": 0,
                        "titles": [],
                    }

                keyword_data[key]["count"] += match.count
                keyword_data[key]["total_engagement"] += thread.score + thread.num_comments
                if len(keyword_data[key]["titles"]) < 3:
                    keyword_data[key]["titles"].append(thread.title[:100])

        # Process videos
        for video in videos:
            text = (video.title or "") + " " + (video.transcript or "")
            matches = matcher.find_matches(text)

            for match in matches:
                key = match.keyword.lower()
                if key not in keyword_data:
                    keyword_data[key] = {
                        "category": match.category,
                        "count": 0,
                        "total_engagement": 0,
                        "titles": [],
                    }

                keyword_data[key]["count"] += match.count
                keyword_data[key]["total_engagement"] += video.view_count
                if len(keyword_data[key]["titles"]) < 3:
                    keyword_data[key]["titles"].append(video.title[:100])

        # Store in database
        try:
            with sqlite3.connect(self.db_path) as conn:
                for keyword, data in keyword_data.items():
                    avg_engagement = (
                        data["total_engagement"] / data["count"] if data["count"] > 0 else 0
                    )

                    conn.execute(
                        """
                        INSERT OR REPLACE INTO keyword_trends
                        (keyword, category, period_start, period_end, mention_count,
                         avg_engagement, sample_titles, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            keyword,
                            data["category"],
                            period_start.isoformat(),
                            period_end.isoformat(),
                            data["count"],
                            avg_engagement,
                            json.dumps(data["titles"]),
                            datetime.now().isoformat(),
                        ),
                    )
                conn.commit()
                logger.info(f"Recorded trends for {len(keyword_data)} keywords")
        except Exception as e:
            logger.error(f"Failed to record trends: {e}")

    def analyze(
        self,
        current_period_days: int = 7,
        comparison_period_days: int = 7,
        min_mentions: int = 2,
    ) -> TrendReport:
        """
        Analyze trends by comparing current period to previous period.

        Args:
            current_period_days: Days to include in current period.
            comparison_period_days: Days to include in comparison period.
            min_mentions: Minimum mentions to include in analysis.

        Returns:
            TrendReport with categorized trends.
        """

        now = datetime.now()
        current_end = now
        current_start = now - timedelta(days=current_period_days)
        comparison_end = current_start
        comparison_start = comparison_end - timedelta(days=comparison_period_days)

        # Get current period data
        current_data = self._get_period_data(current_start, current_end)

        # Get comparison period data
        comparison_data = self._get_period_data(comparison_start, comparison_end)

        # Calculate trends
        emerging: list[Trend] = []
        declining: list[Trend] = []
        new_topics: list[Trend] = []
        gone_topics: list[Trend] = []
        stable_hot: list[Trend] = []

        all_keywords = set(current_data.keys()) | set(comparison_data.keys())

        for keyword in all_keywords:
            current = current_data.get(
                keyword, {"count": 0, "engagement": 0, "titles": [], "category": "unknown"}
            )
            previous = comparison_data.get(
                keyword, {"count": 0, "engagement": 0, "titles": [], "category": "unknown"}
            )

            current_count = current["count"]
            previous_count = previous["count"]
            category = current.get("category") or previous.get("category") or "unknown"
            titles = current.get("titles", []) or previous.get("titles", [])
            avg_engagement = current.get("engagement", 0)

            # Skip low-mention keywords
            if current_count < min_mentions and previous_count < min_mentions:
                continue

            # Calculate change
            if previous_count == 0:
                if current_count >= min_mentions:
                    change_percent = 100.0
                    direction = "new"
                else:
                    continue
            elif current_count == 0:
                change_percent = -100.0
                direction = "gone"
            else:
                ratio = current_count / previous_count
                change_percent = (ratio - 1) * 100

                if ratio >= self.rising_threshold:
                    direction = "rising"
                elif ratio <= self.falling_threshold:
                    direction = "falling"
                else:
                    direction = "stable"

            # Calculate velocity (mentions per day)
            velocity = current_count / current_period_days if current_period_days > 0 else 0

            trend = Trend(
                topic=keyword,
                category=category,
                current_count=current_count,
                previous_count=previous_count,
                change_percent=round(change_percent, 1),
                velocity=round(velocity, 2),
                direction=direction,
                avg_engagement=round(avg_engagement, 1),
                sample_titles=titles[:3] if isinstance(titles, list) else [],
            )

            # Categorize
            if direction == "new":
                new_topics.append(trend)
            elif direction == "gone":
                gone_topics.append(trend)
            elif direction == "rising":
                emerging.append(trend)
            elif direction == "falling":
                declining.append(trend)
            elif current_count >= min_mentions * 2:  # Stable but popular
                stable_hot.append(trend)

        # Sort by change magnitude
        emerging.sort(key=lambda t: t.change_percent, reverse=True)
        declining.sort(key=lambda t: t.change_percent)
        new_topics.sort(key=lambda t: t.current_count, reverse=True)
        gone_topics.sort(key=lambda t: t.previous_count, reverse=True)
        stable_hot.sort(key=lambda t: t.current_count, reverse=True)

        return TrendReport(
            period_start=current_start,
            period_end=current_end,
            comparison_start=comparison_start,
            comparison_end=comparison_end,
            emerging=emerging[:10],
            declining=declining[:10],
            new_topics=new_topics[:10],
            gone_topics=gone_topics[:10],
            stable_hot=stable_hot[:10],
        )

    def _get_period_data(
        self,
        start: datetime,
        end: datetime,
    ) -> dict[str, dict]:
        """Get aggregated keyword data for a period."""
        import json

        data: dict[str, dict] = {}

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT keyword, category, SUM(mention_count) as total_count,
                           AVG(avg_engagement) as engagement,
                           GROUP_CONCAT(sample_titles) as all_titles
                    FROM keyword_trends
                    WHERE period_start >= ? AND period_end <= ?
                    GROUP BY keyword
                    """,
                    (start.isoformat(), end.isoformat()),
                )

                for row in cursor:
                    keyword = row[0]
                    # Parse sample titles
                    titles = []
                    if row[4]:
                        try:
                            for title_json in row[4].split(","):
                                titles.extend(json.loads(title_json))
                        except json.JSONDecodeError:
                            pass

                    data[keyword] = {
                        "category": row[1],
                        "count": row[2],
                        "engagement": row[3] or 0,
                        "titles": titles[:3],
                    }
        except Exception as e:
            logger.warning(f"Could not get period data: {e}")

        return data

    def get_emerging_topics(
        self,
        days: int = 7,
        min_change: float = 50.0,
    ) -> list[Trend]:
        """
        Get topics that are trending up.

        Args:
            days: Days to analyze.
            min_change: Minimum percentage increase.

        Returns:
            List of emerging trends.
        """
        report = self.analyze(current_period_days=days)
        return [t for t in report.emerging if t.change_percent >= min_change]

    def get_declining_topics(
        self,
        days: int = 7,
        max_change: float = -30.0,
    ) -> list[Trend]:
        """
        Get topics that are trending down.

        Args:
            days: Days to analyze.
            max_change: Maximum percentage change (negative).

        Returns:
            List of declining trends.
        """
        report = self.analyze(current_period_days=days)
        return [t for t in report.declining if t.change_percent <= max_change]

    def calculate_velocity(
        self,
        keyword: str,
        days: int = 7,
    ) -> float:
        """
        Calculate mentions per day for a keyword.

        Args:
            keyword: The keyword to check.
            days: Number of days to analyze.

        Returns:
            Mentions per day.
        """
        end = datetime.now()
        start = end - timedelta(days=days)
        data = self._get_period_data(start, end)

        if keyword.lower() in data:
            return float(data[keyword.lower()]["count"]) / days
        return 0.0


# Module-level instance
_default_detector: TrendDetector | None = None


def get_detector() -> TrendDetector:
    """Get the default trend detector instance."""
    global _default_detector
    if _default_detector is None:
        _default_detector = TrendDetector()
    return _default_detector


def analyze_trends(
    current_period_days: int = 7,
    comparison_period_days: int = 7,
) -> TrendReport:
    """Convenience function to analyze trends."""
    return get_detector().analyze(
        current_period_days=current_period_days,
        comparison_period_days=comparison_period_days,
    )


def get_emerging_topics(days: int = 7) -> list[Trend]:
    """Get topics that are trending up."""
    return get_detector().get_emerging_topics(days=days)


def get_declining_topics(days: int = 7) -> list[Trend]:
    """Get topics that are trending down."""
    return get_detector().get_declining_topics(days=days)

"""Competitive intelligence tracking for SignalSift.

This module provides dedicated tracking for competitor tool mentions,
sentiment analysis, and feature gap identification.
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from signalsift.config.defaults import DEFAULT_DB_PATH
from signalsift.processing.entities import (
    KNOWN_TOOLS,
    get_extractor,
)
from signalsift.processing.sentiment import analyze_sentiment
from signalsift.utils.logging import get_logger

if TYPE_CHECKING:
    from signalsift.database.models import RedditThread, YouTubeVideo

logger = get_logger(__name__)


@dataclass
class ToolStats:
    """Aggregated statistics for a competitor tool."""

    tool_name: str
    category: str
    tier: str
    mention_count: int
    positive_mentions: int
    negative_mentions: int
    neutral_mentions: int
    switching_from_count: int  # Users leaving this tool
    switching_to_count: int  # Users adopting this tool
    avg_sentiment: float
    feature_requests: list[str]  # Extracted feature requests
    complaints: list[str]  # Common complaints
    praises: list[str]  # Common praises
    sample_contexts: list[str]  # Sample mention contexts


@dataclass
class FeatureGap:
    """A potential feature opportunity based on competitor complaints."""

    tool: str
    feature_description: str
    demand_level: str  # "high", "medium", "low"
    mention_count: int
    sentiment_score: float
    sample_quotes: list[str]
    opportunity: str | None  # Category of opportunity this represents


@dataclass
class CompetitiveReport:
    """Complete competitive intelligence report."""

    generated_at: datetime
    period_start: datetime
    period_end: datetime
    tool_stats: list[ToolStats]
    feature_gaps: list[FeatureGap]
    market_movers: list[str]  # Tools gaining market share
    market_losers: list[str]  # Tools losing market share
    head_to_head: dict[str, dict[str, int]]  # Tool vs tool comparison mentions


# SQL for creating the competitive tracking table
COMPETITIVE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS tool_mentions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_name TEXT NOT NULL,
    category TEXT,
    sentiment TEXT,
    sentiment_score REAL,
    context TEXT,
    source_type TEXT,  -- 'reddit', 'youtube', 'hackernews'
    source_id TEXT,
    source_title TEXT,
    captured_at TEXT NOT NULL,
    UNIQUE(tool_name, source_type, source_id)
)
"""

COMPETITIVE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_tool_mentions_tool ON tool_mentions(tool_name);
CREATE INDEX IF NOT EXISTS idx_tool_mentions_date ON tool_mentions(captured_at);
"""

# Feature request patterns
FEATURE_REQUEST_PATTERNS = [
    r"wish\s+(?:it|they)\s+had",
    r"(?:would|could)\s+be\s+(?:nice|great|helpful)\s+(?:if|to)",
    r"missing\s+(?:feature|functionality)",
    r"(?:need|want)s?\s+(?:a|an|to)\s+(?:better|new|improved)",
    r"should\s+(?:add|include|have)",
    r"looking\s+for\s+(?:a|an)\s+(?:feature|option|way)",
    r"can'?t\s+(?:do|find|see)",
]

# Complaint patterns
COMPLAINT_PATTERNS = [
    r"(?:too|so)\s+(?:expensive|slow|complicated|buggy)",
    r"(?:terrible|horrible|awful|worst)\s+(?:support|ui|ux|experience)",
    r"(?:keeps?\s+)?(?:crashing|breaking|failing)",
    r"(?:waste\s+of|not\s+worth)\s+(?:money|time)",
    r"(?:gave\s+up|stopped\s+using|cancelled|canceled)",
    r"(?:frustrat|disappoint|annoy)",
    r"(?:doesn'?t|don'?t)\s+(?:work|help|do)",
]

# Praise patterns
PRAISE_PATTERNS = [
    r"(?:love|amazing|excellent|fantastic|best)\s+(?:tool|feature|product)",
    r"(?:game\s*changer|life\s*saver)",
    r"(?:highly\s+)?recommend",
    r"(?:worth\s+(?:every|the)\s+(?:penny|money))",
    r"(?:saved\s+me)\s+(?:so\s+much\s+)?(?:time|money|hours)",
    r"(?:couldn'?t\s+live\s+without)",
]


class CompetitiveIntelligence:
    """Track and analyze competitor tool mentions."""

    def __init__(self, db_path: Path | None = None) -> None:
        """
        Initialize competitive intelligence tracker.

        Args:
            db_path: Path to SQLite database.
        """
        self.db_path = db_path or DEFAULT_DB_PATH
        self._extractor = get_extractor()
        self._ensure_table()

    def _ensure_table(self) -> None:
        """Ensure the competitive tracking table exists."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(COMPETITIVE_TABLE_SQL)
                conn.executescript(COMPETITIVE_INDEX_SQL)
                conn.commit()
        except Exception as e:
            logger.warning(f"Could not create competitive tracking table: {e}")

    def track_content(
        self,
        threads: list[RedditThread] | None = None,
        videos: list[YouTubeVideo] | None = None,
    ) -> int:
        """
        Track tool mentions in content.

        Args:
            threads: Reddit threads to analyze.
            videos: YouTube videos to analyze.

        Returns:
            Number of mentions tracked.
        """

        mentions_tracked = 0

        # Process Reddit threads
        if threads:
            for thread in threads:
                text = (thread.title or "") + " " + (thread.selftext or "")
                tool_mentions = self._extractor._extract_tools(text)

                for mention in tool_mentions:
                    sentiment = analyze_sentiment(mention.context)

                    try:
                        with sqlite3.connect(self.db_path) as conn:
                            conn.execute(
                                """
                                INSERT OR IGNORE INTO tool_mentions
                                (tool_name, category, sentiment, sentiment_score, context,
                                 source_type, source_id, source_title, captured_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    mention.tool,
                                    KNOWN_TOOLS.get(mention.tool, {}).get("category"),
                                    mention.sentiment_hint or sentiment.category.value,
                                    sentiment.polarity,
                                    mention.context[:500],
                                    "reddit",
                                    thread.id,
                                    thread.title[:200],
                                    datetime.now().isoformat(),
                                ),
                            )
                            if conn.total_changes > 0:
                                mentions_tracked += 1
                    except Exception as e:
                        logger.debug(f"Failed to track mention: {e}")

        # Process YouTube videos
        if videos:
            for video in videos:
                text = (video.title or "") + " " + (video.transcript or "")[:5000]
                tool_mentions = self._extractor._extract_tools(text)

                for mention in tool_mentions:
                    sentiment = analyze_sentiment(mention.context)

                    try:
                        with sqlite3.connect(self.db_path) as conn:
                            conn.execute(
                                """
                                INSERT OR IGNORE INTO tool_mentions
                                (tool_name, category, sentiment, sentiment_score, context,
                                 source_type, source_id, source_title, captured_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    mention.tool,
                                    KNOWN_TOOLS.get(mention.tool, {}).get("category"),
                                    mention.sentiment_hint or sentiment.category.value,
                                    sentiment.polarity,
                                    mention.context[:500],
                                    "youtube",
                                    video.id,
                                    video.title[:200],
                                    datetime.now().isoformat(),
                                ),
                            )
                            if conn.total_changes > 0:
                                mentions_tracked += 1
                    except Exception as e:
                        logger.debug(f"Failed to track mention: {e}")

        logger.info(f"Tracked {mentions_tracked} new tool mentions")
        return mentions_tracked

    def get_tool_stats(
        self,
        tool_name: str | None = None,
        days: int = 30,
    ) -> list[ToolStats]:
        """
        Get statistics for tools.

        Args:
            tool_name: Specific tool to get stats for, or None for all.
            days: Number of days to analyze.

        Returns:
            List of ToolStats objects.
        """
        import re

        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        stats: list[ToolStats] = []

        try:
            with sqlite3.connect(self.db_path) as conn:
                if tool_name:
                    cursor = conn.execute(
                        """
                        SELECT tool_name, category, sentiment, sentiment_score, context
                        FROM tool_mentions
                        WHERE tool_name = ? AND captured_at >= ?
                        """,
                        (tool_name.lower(), cutoff),
                    )
                else:
                    cursor = conn.execute(
                        """
                        SELECT tool_name, category, sentiment, sentiment_score, context
                        FROM tool_mentions
                        WHERE captured_at >= ?
                        """,
                        (cutoff,),
                    )

                # Aggregate by tool
                tool_data: dict[str, dict] = defaultdict(
                    lambda: {
                        "category": None,
                        "mentions": 0,
                        "positive": 0,
                        "negative": 0,
                        "neutral": 0,
                        "switching_from": 0,
                        "switching_to": 0,
                        "sentiment_sum": 0.0,
                        "feature_requests": [],
                        "complaints": [],
                        "praises": [],
                        "contexts": [],
                    }
                )

                for row in cursor:
                    tool = row[0]
                    data = tool_data[tool]
                    data["category"] = row[1]
                    data["mentions"] += 1
                    sentiment = row[2]
                    sentiment_score = row[3] or 0
                    context = row[4] or ""

                    # Count sentiment types
                    if sentiment == "switching_from":
                        data["switching_from"] += 1
                        data["negative"] += 1
                    elif sentiment == "switching_to":
                        data["switching_to"] += 1
                        data["positive"] += 1
                    elif sentiment in ["positive", "very_positive"]:
                        data["positive"] += 1
                    elif sentiment in ["negative", "very_negative"]:
                        data["negative"] += 1
                    else:
                        data["neutral"] += 1

                    data["sentiment_sum"] += sentiment_score

                    # Extract feature requests
                    for pattern in FEATURE_REQUEST_PATTERNS:
                        if re.search(pattern, context, re.IGNORECASE):
                            if len(data["feature_requests"]) < 5:
                                data["feature_requests"].append(context[:200])
                            break

                    # Extract complaints
                    for pattern in COMPLAINT_PATTERNS:
                        if re.search(pattern, context, re.IGNORECASE):
                            if len(data["complaints"]) < 5:
                                data["complaints"].append(context[:200])
                            break

                    # Extract praises
                    for pattern in PRAISE_PATTERNS:
                        if re.search(pattern, context, re.IGNORECASE):
                            if len(data["praises"]) < 5:
                                data["praises"].append(context[:200])
                            break

                    # Store sample contexts
                    if len(data["contexts"]) < 5:
                        data["contexts"].append(context[:200])

                # Build stats objects
                for tool, data in tool_data.items():
                    tool_info = KNOWN_TOOLS.get(tool, {})
                    avg_sentiment = (
                        data["sentiment_sum"] / data["mentions"] if data["mentions"] > 0 else 0
                    )

                    stats.append(
                        ToolStats(
                            tool_name=tool,
                            category=data["category"] or tool_info.get("category", "unknown"),
                            tier=tool_info.get("tier", "unknown"),
                            mention_count=data["mentions"],
                            positive_mentions=data["positive"],
                            negative_mentions=data["negative"],
                            neutral_mentions=data["neutral"],
                            switching_from_count=data["switching_from"],
                            switching_to_count=data["switching_to"],
                            avg_sentiment=round(avg_sentiment, 3),
                            feature_requests=data["feature_requests"],
                            complaints=data["complaints"],
                            praises=data["praises"],
                            sample_contexts=data["contexts"],
                        )
                    )

        except Exception as e:
            logger.error(f"Failed to get tool stats: {e}")

        # Sort by mention count
        stats.sort(key=lambda s: s.mention_count, reverse=True)
        return stats

    def identify_feature_gaps(self, days: int = 30) -> list[FeatureGap]:
        """
        Identify feature gaps from competitor complaints.

        Args:
            days: Number of days to analyze.

        Returns:
            List of FeatureGap opportunities.
        """
        tool_stats = self.get_tool_stats(days=days)
        gaps: list[FeatureGap] = []

        # Map tool categories to opportunity types
        category_to_opportunity = {
            "backlink": "link_building",
            "all-in-one": "comprehensive",
            "content": "content_creation",
            "keyword": "keyword_research",
            "technical": "technical_seo",
            "ai_content": "ai_writing",
            "outreach": "outreach",
            "rank_tracking": "rank_tracking",
            "competitor": "competitive_analysis",
            "ai_detection": "ai_detection",
        }

        for stats in tool_stats:
            # Look at tools with complaints
            if stats.complaints:
                for complaint in stats.complaints:
                    # Determine demand level
                    if stats.mention_count >= 20:
                        demand = "high"
                    elif stats.mention_count >= 10:
                        demand = "medium"
                    else:
                        demand = "low"

                    gaps.append(
                        FeatureGap(
                            tool=stats.tool_name,
                            feature_description=complaint,
                            demand_level=demand,
                            mention_count=stats.mention_count,
                            sentiment_score=stats.avg_sentiment,
                            sample_quotes=stats.complaints[:3],
                            opportunity=category_to_opportunity.get(stats.category),
                        )
                    )

            # Also look at feature requests
            if stats.feature_requests:
                for request in stats.feature_requests:
                    demand = "medium" if stats.mention_count >= 10 else "low"

                    gaps.append(
                        FeatureGap(
                            tool=stats.tool_name,
                            feature_description=request,
                            demand_level=demand,
                            mention_count=stats.mention_count,
                            sentiment_score=stats.avg_sentiment,
                            sample_quotes=stats.feature_requests[:3],
                            opportunity=category_to_opportunity.get(stats.category),
                        )
                    )

        # Sort by demand level and mention count
        demand_order = {"high": 0, "medium": 1, "low": 2}
        gaps.sort(key=lambda g: (demand_order.get(g.demand_level, 3), -g.mention_count))

        return gaps[:20]  # Return top 20 gaps

    def get_market_movers(self, days: int = 30) -> tuple[list[str], list[str]]:
        """
        Identify tools gaining and losing market share.

        Based on switching_to vs switching_from patterns.

        Returns:
            Tuple of (gainers, losers).
        """
        stats = self.get_tool_stats(days=days)

        # Calculate net flow
        tool_flow: dict[str, int] = {}
        for s in stats:
            net = s.switching_to_count - s.switching_from_count
            if net != 0:
                tool_flow[s.tool_name] = net

        # Sort
        gainers = sorted(
            [t for t, n in tool_flow.items() if n > 0],
            key=lambda t: tool_flow[t],
            reverse=True,
        )
        losers = sorted(
            [t for t, n in tool_flow.items() if n < 0],
            key=lambda t: tool_flow[t],
        )

        return gainers[:5], losers[:5]

    def generate_report(self, days: int = 30) -> CompetitiveReport:
        """
        Generate a complete competitive intelligence report.

        Args:
            days: Number of days to analyze.

        Returns:
            CompetitiveReport with all insights.
        """
        now = datetime.now()
        period_start = now - timedelta(days=days)

        tool_stats = self.get_tool_stats(days=days)
        feature_gaps = self.identify_feature_gaps(days=days)
        gainers, losers = self.get_market_movers(days=days)

        # Build head-to-head comparison
        head_to_head: dict[str, dict[str, int]] = {}
        # This would require analyzing co-mentions - simplified for now

        return CompetitiveReport(
            generated_at=now,
            period_start=period_start,
            period_end=now,
            tool_stats=tool_stats,
            feature_gaps=feature_gaps,
            market_movers=gainers,
            market_losers=losers,
            head_to_head=head_to_head,
        )


# Module-level instance
_default_intel: CompetitiveIntelligence | None = None


def get_competitive_intel() -> CompetitiveIntelligence:
    """Get the default competitive intelligence instance."""
    global _default_intel
    if _default_intel is None:
        _default_intel = CompetitiveIntelligence()
    return _default_intel


def track_tool_mentions(
    threads: list[RedditThread] | None = None,
    videos: list[YouTubeVideo] | None = None,
) -> int:
    """Track tool mentions in content."""
    return get_competitive_intel().track_content(threads, videos)


def get_tool_report(days: int = 30) -> CompetitiveReport:
    """Generate a competitive intelligence report."""
    return get_competitive_intel().generate_report(days)

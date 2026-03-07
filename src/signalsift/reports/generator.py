"""Report generation for SignalSift."""

import json
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from jinja2 import Environment, FileSystemLoader, select_autoescape

from signalsift import __version__
from signalsift.config import get_settings
from signalsift.database.models import RedditThread, Report, YouTubeVideo
from signalsift.database.queries import (
    get_all_keywords,
    get_cache_stats,
    get_keywords_by_category,
    get_unprocessed_content,
    insert_report,
    mark_content_processed,
)
from signalsift.exceptions import ReportError
from signalsift.processing.classification import get_category_name
from signalsift.processing.scoring import calculate_engagement_velocity
from signalsift.utils.logging import get_logger

logger = get_logger(__name__)


class ReportGenerator:
    """Generate markdown reports from cached content."""

    def __init__(self) -> None:
        """Initialize the report generator."""
        self.settings = get_settings()
        self._env: Environment | None = None

    @property
    def env(self) -> Environment:
        """Get or create the Jinja2 environment."""
        if self._env is None:
            template_dir = Path(__file__).parent / "templates"
            self._env = Environment(
                loader=FileSystemLoader(str(template_dir)),
                autoescape=select_autoescape(["html", "xml"]),
                trim_blocks=True,
                lstrip_blocks=True,
            )
            # Add custom filters
            self._env.filters["truncate"] = self._truncate
            self._env.filters["format_number"] = self._format_number
            self._env.filters["format_datetime"] = self._format_datetime
        return self._env

    def generate(
        self,
        output_path: Path | None = None,
        min_score: float | None = None,
        since_days: int | None = None,
        max_items: int | None = None,
        include_processed: bool = False,
        preview: bool = False,
        delta: bool = False,
        include_trends: bool = True,
        include_competitive: bool = True,
        topic: str | None = None,
    ) -> Path:
        """
        Generate a markdown report.

        Args:
            output_path: Custom output path. Uses default if not provided.
            min_score: Minimum relevance score to include.
            since_days: Only include content from last N days.
            max_items: Maximum items per section.
            include_processed: Include previously processed content.
            preview: If True, don't mark content as processed.
            delta: If True, only include new content since last report.
            include_trends: Include trend analysis section.
            include_competitive: Include competitive intelligence section.
            topic: If set, filter content to only items matching this keyword category.

        Returns:
            Path to the generated report.
        """
        # Get content
        if include_processed:
            from signalsift.database.queries import get_reddit_threads, get_youtube_videos

            since_timestamp = None
            if since_days:
                since_timestamp = int(
                    (datetime.now() - __import__("datetime").timedelta(days=since_days)).timestamp()
                )

            threads = get_reddit_threads(
                since_timestamp=since_timestamp,
                min_score=min_score,
                limit=max_items,
            )
            videos = get_youtube_videos(
                since_timestamp=since_timestamp,
                min_score=min_score,
                limit=max_items,
            )
        else:
            threads, videos = get_unprocessed_content(
                min_score=min_score or self.settings.scoring.min_relevance_score,
                since_days=since_days,
                reddit_limit=max_items,
                youtube_limit=max_items,
            )

        if not threads and not videos:
            raise ReportError("No content to include in report")

        # Filter by topic/keyword category if requested
        if topic:
            topic_keywords = {kw.keyword.lower() for kw in get_keywords_by_category(category=topic)}
            if not topic_keywords:
                raise ReportError(
                    f"No keywords found for topic '{topic}'. "
                    "Use 'sift keywords list' to see available categories."
                )
            threads = [
                t
                for t in threads
                if t.matched_keywords
                and any(kw.lower() in topic_keywords for kw in t.matched_keywords)
            ]
            videos = [
                v
                for v in videos
                if v.matched_keywords
                and any(kw.lower() in topic_keywords for kw in v.matched_keywords)
            ]
            if not threads and not videos:
                raise ReportError(
                    f"No content matched topic '{topic}'. "
                    "Try running 'sift scan' first or check available topics with 'sift keywords list'."
                )

        # Build context
        context = self._build_context(
            threads,
            videos,
            include_trends=include_trends,
            include_competitive=include_competitive,
        )

        # Render template
        template = self.env.get_template("default.md.j2")
        content = template.render(**context)

        # Determine output path
        if output_path is None:
            output_path = self._get_default_output_path(topic=topic)

        # Write report
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")

        logger.info(f"Report generated: {output_path}")

        # Create report record and mark content as processed
        if not preview:
            report_id = str(uuid.uuid4())
            report = Report(
                id=report_id,
                generated_at=int(datetime.now().timestamp()),
                filepath=str(output_path),
                reddit_count=len(threads),
                youtube_count=len(videos),
                date_range_start=(
                    min([t.created_utc for t in threads] + [v.published_at for v in videos])
                    if threads or videos
                    else None
                ),
                date_range_end=(
                    max([t.created_utc for t in threads] + [v.published_at for v in videos])
                    if threads or videos
                    else None
                ),
                config_snapshot=json.dumps(
                    {
                        "min_score": min_score,
                        "since_days": since_days,
                        "max_items": max_items,
                    }
                ),
            )
            insert_report(report)

            mark_content_processed(
                report_id=report_id,
                thread_ids=[t.id for t in threads],
                video_ids=[v.id for v in videos],
            )

        return output_path

    def _build_context(
        self,
        threads: list[RedditThread],
        videos: list[YouTubeVideo],
        include_trends: bool = True,
        include_competitive: bool = True,
    ) -> dict[str, Any]:
        """Build the template context from content."""
        now = datetime.now()
        max_per_section = self.settings.reports.max_items_per_section
        excerpt_length = self.settings.reports.excerpt_length

        # Deduplicate threads by ID (preserve order, keep highest-scored occurrence)
        seen_ids: set[str] = set()
        deduped_threads: list[RedditThread] = []
        for t in threads:
            if t.id not in seen_ids:
                seen_ids.add(t.id)
                deduped_threads.append(t)
        threads = deduped_threads

        # Load current active keywords for filtering stored matched_keywords
        active_keywords = {kw.keyword.lower() for kw in get_all_keywords()}

        # Build sub-contexts using helper methods
        metadata = self._build_metadata_context(threads, videos, now)
        categorized = self._build_categorized_content(
            threads, max_per_section, excerpt_length, active_keywords
        )
        rising = self._build_rising_content(threads, excerpt_length, active_keywords)
        trends = self._build_trend_data(include_trends)
        competitive = self._build_competitive_data(include_competitive)
        grouped = self._build_grouped_content(threads, videos, excerpt_length, active_keywords)

        # Merge all contexts
        context: dict[str, Any] = {}
        context.update(metadata)
        context.update(categorized)
        context.update(rising)
        context.update(trends)
        context.update(competitive)
        context.update(grouped)

        # Add YouTube content
        context["youtube_videos"] = [
            self._video_to_context(v, excerpt_length, active_keywords)
            for v in videos[:max_per_section]
        ]

        return context

    def _build_metadata_context(
        self,
        threads: list[RedditThread],
        videos: list[YouTubeVideo],
        now: datetime,
    ) -> dict[str, Any]:
        """Build report metadata context."""
        all_timestamps = [t.created_utc for t in threads] + [v.published_at for v in videos]
        date_range_start = datetime.fromtimestamp(min(all_timestamps)) if all_timestamps else now
        date_range_end = datetime.fromtimestamp(max(all_timestamps)) if all_timestamps else now

        # Get top themes
        category_counts: dict[str, int] = defaultdict(int)
        for thread in threads:
            if thread.category:
                category_counts[thread.category] += 1
        for video in videos:
            if video.category:
                category_counts[video.category] += 1
        top_themes = [
            get_category_name(cat)
            for cat, _ in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        ]

        # Count unique sources
        reddit_sources = len({t.subreddit for t in threads})
        youtube_sources = len({v.channel_name or v.channel_id for v in videos})

        return {
            "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "date_range_start": date_range_start.strftime("%Y-%m-%d"),
            "date_range_end": date_range_end.strftime("%Y-%m-%d"),
            "sources_summary": f"{reddit_sources} subreddits, {youtube_sources} YouTube channels",
            "version": __version__,
            "reddit_count": len(threads),
            "youtube_count": len(videos),
            "new_count": len(threads) + len(videos),
            "top_themes": top_themes,
            "cache_stats": get_cache_stats(),
        }

    def _build_categorized_content(
        self,
        threads: list[RedditThread],
        max_per_section: int,
        excerpt_length: int,
        active_keywords: set[str] | None = None,
    ) -> dict[str, Any]:
        """Build categorized content context."""
        # Define category mappings
        category_mappings = {
            "pain_points": ["pain_point"],
            "success_stories": ["success_story"],
            "tool_mentions": ["tool_comparison"],
            "monetization_insights": ["monetization", "roi_analysis", "ecommerce"],
            "ai_visibility_insights": ["ai_visibility"],
            "keyword_research_insights": ["keyword_research", "local_seo"],
            "content_generation_insights": ["ai_content"],
            "competition_insights": ["competitor_analysis", "content_brief"],
            "image_generation_insights": ["image_generation"],
            "static_sites_insights": ["static_sites"],
        }

        result: dict[str, Any] = {}
        for context_key, categories in category_mappings.items():
            items = [t for t in threads if t.category in categories]
            items.sort(key=lambda x: x.relevance_score, reverse=True)
            result[context_key] = [
                self._thread_to_context(t, excerpt_length, active_keywords)
                for t in items[:max_per_section]
            ]

        return result

    def _build_rising_content(
        self,
        threads: list[RedditThread],
        excerpt_length: int,
        active_keywords: set[str] | None = None,
    ) -> dict[str, Any]:
        """Build rising content context (high engagement velocity)."""
        threads_with_velocity = []
        for thread in threads:
            velocity = calculate_engagement_velocity(
                thread.score,
                thread.num_comments,
                thread.created_utc,
            )
            if velocity >= 10:  # Rising if >10 engagement/hour
                threads_with_velocity.append({"thread": thread, "velocity": velocity})

        # Sort by velocity
        threads_with_velocity.sort(key=lambda x: cast(float, x["velocity"]), reverse=True)

        return {
            "rising_content": [
                {
                    **self._thread_to_context(
                        cast(RedditThread, item["thread"]), excerpt_length, active_keywords
                    ),
                    "velocity": item["velocity"],
                }
                for item in threads_with_velocity[:10]
            ]
        }

    def _build_trend_data(self, include_trends: bool) -> dict[str, Any]:
        """Build trend analysis context."""
        if not include_trends:
            return {"trends": [], "emerging_trends": [], "declining_trends": [], "new_topics": []}

        try:
            from signalsift.processing.trends import analyze_trends

            trends_data = analyze_trends(current_period_days=7)
        except Exception as e:
            logger.warning(f"Could not get trend data: {e}")
            return {"trends": [], "emerging_trends": [], "declining_trends": [], "new_topics": []}

        return {
            "trends": [
                {
                    "topic": t.topic,
                    "change": (
                        f"+{t.change_percent}%" if t.change_percent > 0 else f"{t.change_percent}%"
                    ),
                    "direction": t.direction,
                    "mention_count": t.current_count,
                }
                for t in trends_data.emerging[:5]
            ],
            "emerging_trends": [
                {"topic": t.topic, "change": f"+{t.change_percent}%", "count": t.current_count}
                for t in trends_data.emerging[:5]
            ],
            "declining_trends": [
                {"topic": t.topic, "change": f"{t.change_percent}%", "count": t.current_count}
                for t in trends_data.declining[:5]
            ],
            "new_topics": [
                {"topic": t.topic, "count": t.current_count} for t in trends_data.new_topics[:5]
            ],
        }

    def _build_competitive_data(self, include_competitive: bool) -> dict[str, Any]:
        """Build competitive intelligence context."""
        empty_result: dict[str, Any] = {
            "competitive_intel": None,
            "top_tools": [],
            "feature_gaps": [],
        }

        if not include_competitive:
            return empty_result

        try:
            from signalsift.processing.competitive import get_competitive_intel

            intel = get_competitive_intel()
            competitive_data = {
                "tool_stats": intel.get_tool_stats(days=30)[:10],
                "feature_gaps": intel.identify_feature_gaps(days=30)[:5],
                "market_movers": intel.get_market_movers(days=30),
            }
        except Exception as e:
            logger.warning(f"Could not get competitive data: {e}")
            return empty_result

        return {
            "competitive_intel": competitive_data,
            "top_tools": [
                {
                    "name": s.tool_name,
                    "mentions": s.mention_count,
                    "sentiment": (
                        "positive"
                        if s.avg_sentiment > 0.1
                        else "negative" if s.avg_sentiment < -0.1 else "neutral"
                    ),
                }
                for s in cast(list[Any], competitive_data["tool_stats"])[:5]
            ],
            "feature_gaps": [
                {
                    "tool": g.tool,
                    "description": g.feature_description[:100],
                    "demand": g.demand_level,
                    "opportunity": g.opportunity,
                }
                for g in cast(list[Any], competitive_data["feature_gaps"])[:5]
            ],
        }

    def _build_grouped_content(
        self,
        threads: list[RedditThread],
        videos: list[YouTubeVideo],
        excerpt_length: int,
        active_keywords: set[str] | None = None,
    ) -> dict[str, Any]:
        """Build content grouped by source."""
        reddit_by_subreddit: dict[str, list[RedditThread]] = defaultdict(list)
        for thread in threads:
            reddit_by_subreddit[thread.subreddit].append(thread)

        youtube_by_channel: dict[str, list[YouTubeVideo]] = defaultdict(list)
        for video in videos:
            channel = video.channel_name or video.channel_id
            youtube_by_channel[channel].append(video)

        return {
            "reddit_by_subreddit": {
                sub: [
                    self._thread_to_context(t, excerpt_length, active_keywords)
                    for t in threads_list
                ]
                for sub, threads_list in reddit_by_subreddit.items()
            },
            "youtube_by_channel": {
                channel: [
                    self._video_to_context(v, excerpt_length, active_keywords) for v in videos_list
                ]
                for channel, videos_list in youtube_by_channel.items()
            },
        }

    def _thread_to_context(
        self,
        thread: RedditThread,
        excerpt_length: int,
        active_keywords: set[str] | None = None,
    ) -> dict[str, Any]:
        """Convert a Reddit thread to template context."""
        excerpt = (thread.selftext or "")[:excerpt_length]
        if len(thread.selftext or "") > excerpt_length:
            excerpt += "..."

        # Filter matched_keywords against current active keyword set to remove stale noise
        matched = thread.matched_keywords
        if active_keywords and matched:
            matched = [kw for kw in matched if kw.lower() in active_keywords]

        engagement_parts = []
        if thread.score > 0:
            engagement_parts.append(f"⬆️ {thread.score}")
        engagement_parts.append(f"💬 {thread.num_comments}")
        engagement = " · ".join(engagement_parts)

        return {
            "title": thread.title,
            "url": thread.url,
            "source_badge": f"r/{thread.subreddit}",
            "relevance_score": round(thread.relevance_score),
            "engagement": engagement,
            "excerpt": excerpt,
            "category": thread.category,
            "score": thread.score,
            "num_comments": thread.num_comments,
            "matched_keywords": matched,
            # Optional insight fields (populated by AI analysis if enabled)
            "feature_suggestion": None,
            "takeaway": None,
            "monetization_angle": None,
            "geo_opportunity": None,
            "keyword_opportunity": None,
            "content_strategy": None,
            "competitive_angle": None,
            "image_opportunity": None,
            "tech_insight": None,
        }

    def _video_to_context(
        self,
        video: YouTubeVideo,
        excerpt_length: int,
        active_keywords: set[str] | None = None,
    ) -> dict[str, Any]:
        """Convert a YouTube video to template context."""
        transcript_excerpt = (video.transcript or "")[:excerpt_length]
        if len(video.transcript or "") > excerpt_length:
            transcript_excerpt += "..."

        # Filter matched_keywords against current active keyword set to remove stale noise
        matched = video.matched_keywords
        if active_keywords and matched:
            matched = [kw for kw in matched if kw.lower() in active_keywords]

        return {
            "title": video.title,
            "url": video.url,
            "channel_name": video.channel_name or video.channel_id,
            "relevance_score": round(video.relevance_score),
            "view_count": video.view_count,
            "like_count": video.like_count,
            "duration_formatted": video.duration_formatted,
            "duration_seconds": video.duration_seconds,
            "transcript_excerpt": transcript_excerpt,
            "transcript_available": video.transcript_available,
            "category": video.category,
            "matched_keywords": matched,
            "insights": None,
        }

    def _get_default_output_path(self, topic: str | None = None) -> Path:
        """Get the default output path for a report."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = self.settings.reports.filename_format.format(
            date=date_str,
            time=datetime.now().strftime("%H%M%S"),
        )
        if topic:
            stem = Path(filename).stem
            suffix = Path(filename).suffix
            filename = f"{stem}-{topic}{suffix}"
        return self.settings.reports.output_directory / filename

    @staticmethod
    def _truncate(text: str, length: int = 50) -> str:
        """Truncate text to specified length."""
        if len(text) <= length:
            return text
        return text[: length - 3] + "..."

    @staticmethod
    def _format_number(value: int) -> str:
        """Format large numbers (e.g., 1500 -> 1.5K)."""
        if value >= 1_000_000:
            return f"{value / 1_000_000:.1f}M"
        if value >= 1_000:
            return f"{value / 1_000:.1f}K"
        return str(value)

    @staticmethod
    def _format_datetime(timestamp: int) -> str:
        """Format a Unix timestamp as a date string."""
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")


def generate_report(**kwargs: Any) -> Path:
    """Convenience function to generate a report."""
    generator = ReportGenerator()
    return generator.generate(**kwargs)

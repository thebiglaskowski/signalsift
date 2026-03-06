"""Tests for report generation."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from signalsift.database.models import RedditThread, YouTubeVideo
from signalsift.exceptions import ReportError
from signalsift.reports.generator import ReportGenerator


@pytest.fixture
def sample_threads() -> list[RedditThread]:
    """Create sample Reddit threads for testing."""
    return [
        RedditThread(
            id="thread1",
            subreddit="SEO",
            title="How to improve keyword research",
            author="user1",
            selftext="Detailed post about keyword research strategies and tools...",
            url="/r/SEO/comments/thread1/",
            score=150,
            num_comments=45,
            created_utc=1704067200,  # 2024-01-01
            relevance_score=85.0,
            matched_keywords=["keyword research", "SEO"],
            category="keyword_research",
        ),
        RedditThread(
            id="thread2",
            subreddit="bigseo",
            title="SEO tools comparison 2024",
            author="user2",
            selftext="Comparing top SEO tools and their features...",
            url="/r/bigseo/comments/thread2/",
            score=200,
            num_comments=60,
            created_utc=1704153600,  # 2024-01-02
            relevance_score=90.0,
            matched_keywords=["SEO tools", "comparison"],
            category="tool_comparison",
        ),
        RedditThread(
            id="thread3",
            subreddit="SEO",
            title="I tripled my organic traffic",
            author="user3",
            selftext="Here's how I achieved 3x growth in 6 months...",
            url="/r/SEO/comments/thread3/",
            score=500,
            num_comments=120,
            created_utc=1704240000,  # 2024-01-03
            relevance_score=95.0,
            matched_keywords=["organic traffic", "growth"],
            category="success_story",
        ),
        RedditThread(
            id="thread4",
            subreddit="SEO",
            title="Pain point: Finding the right keywords",
            author="user4",
            selftext="I'm struggling with keyword selection for my niche...",
            url="/r/SEO/comments/thread4/",
            score=80,
            num_comments=30,
            created_utc=1704326400,  # 2024-01-04
            relevance_score=75.0,
            matched_keywords=["keywords", "pain point"],
            category="pain_point",
        ),
    ]


@pytest.fixture
def sample_videos() -> list[YouTubeVideo]:
    """Create sample YouTube videos for testing."""
    return [
        YouTubeVideo(
            id="video1",
            channel_id="channel1",
            channel_name="SEO Guru",
            title="Complete SEO Guide 2024",
            description="Everything about SEO in one video",
            url="https://youtube.com/watch?v=video1",
            duration_seconds=1800,
            view_count=50000,
            like_count=2000,
            published_at=1704067200,
            transcript="This video covers SEO strategies including keyword research...",
            transcript_available=True,
            relevance_score=80.0,
            matched_keywords=["SEO", "guide"],
            category="techniques",
        ),
        YouTubeVideo(
            id="video2",
            channel_id="channel2",
            channel_name="Marketing Pro",
            title="AI Tools for Content Generation",
            description="Best AI tools for creating SEO content",
            url="https://youtube.com/watch?v=video2",
            duration_seconds=900,
            view_count=30000,
            like_count=1500,
            published_at=1704153600,
            transcript="Today we'll explore AI content generation tools...",
            transcript_available=True,
            relevance_score=75.0,
            matched_keywords=["AI", "content"],
            category="ai_content",
        ),
    ]


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock()
    settings.scoring.min_relevance_score = 70.0
    settings.reports.max_items_per_section = 10
    settings.reports.excerpt_length = 200
    settings.reports.output_directory = Path("/tmp/reports")
    settings.reports.filename_format = "report_{date}_{time}.md"
    return settings


@pytest.fixture
def generator(mock_settings):
    """Create a ReportGenerator instance with mocked settings."""
    with patch("signalsift.reports.generator.get_settings", return_value=mock_settings):
        return ReportGenerator()


class TestReportGeneratorInit:
    """Tests for ReportGenerator initialization."""

    def test_init_creates_instance(self, mock_settings):
        """Test that ReportGenerator initializes correctly."""
        with patch("signalsift.reports.generator.get_settings", return_value=mock_settings):
            generator = ReportGenerator()
            assert generator.settings == mock_settings
            assert generator._env is None

    def test_env_property_lazy_initialization(self, generator):
        """Test that env property initializes Jinja2 environment lazily."""
        assert generator._env is None
        env = generator.env
        assert env is not None
        assert generator._env is env
        # Second call should return same instance
        assert generator.env is env

    def test_env_has_custom_filters(self, generator):
        """Test that custom filters are registered."""
        env = generator.env
        assert "truncate" in env.filters
        assert "format_number" in env.filters
        assert "format_datetime" in env.filters


class TestBuildMetadataContext:
    """Tests for _build_metadata_context method."""

    def test_metadata_with_threads_and_videos(
        self, generator, sample_threads, sample_videos
    ):
        """Test metadata generation with both threads and videos."""
        now = datetime(2024, 1, 5, 12, 0, 0)

        with patch("signalsift.reports.generator.get_cache_stats", return_value={"total": 100}):
            result = generator._build_metadata_context(sample_threads, sample_videos, now)

        assert result["generated_at"] == "2024-01-05 12:00:00"
        # Date range depends on timezone, just check it's a date string
        assert len(result["date_range_start"]) == 10  # YYYY-MM-DD format
        assert len(result["date_range_end"]) == 10
        assert result["reddit_count"] == 4
        assert result["youtube_count"] == 2
        assert result["new_count"] == 6
        assert "subreddits" in result["sources_summary"]
        assert "YouTube channels" in result["sources_summary"]

    def test_metadata_with_empty_content(self, generator):
        """Test metadata generation with no content."""
        now = datetime(2024, 1, 5, 12, 0, 0)

        with patch("signalsift.reports.generator.get_cache_stats", return_value={"total": 0}):
            result = generator._build_metadata_context([], [], now)

        assert result["reddit_count"] == 0
        assert result["youtube_count"] == 0
        assert result["new_count"] == 0

    def test_metadata_top_themes(self, generator, sample_threads, sample_videos):
        """Test that top themes are calculated correctly."""
        now = datetime.now()

        with patch("signalsift.reports.generator.get_cache_stats", return_value={}):
            with patch("signalsift.reports.generator.get_category_name") as mock_get_cat:
                mock_get_cat.side_effect = lambda x: x.replace("_", " ").title()
                result = generator._build_metadata_context(sample_threads, sample_videos, now)

        assert "top_themes" in result
        assert len(result["top_themes"]) <= 5

    def test_metadata_unique_sources(self, generator, sample_threads, sample_videos):
        """Test counting unique sources."""
        now = datetime.now()

        with patch("signalsift.reports.generator.get_cache_stats", return_value={}):
            result = generator._build_metadata_context(sample_threads, sample_videos, now)

        # Should count unique subreddits (SEO, bigseo = 2)
        assert "2 subreddits" in result["sources_summary"]
        # Should count unique channels (2 channels)
        assert "2 YouTube channels" in result["sources_summary"]


class TestBuildCategorizedContent:
    """Tests for _build_categorized_content method."""

    def test_categorizes_by_pain_points(self, generator, sample_threads):
        """Test that pain points are categorized correctly."""
        result = generator._build_categorized_content(sample_threads, max_per_section=10, excerpt_length=200)

        assert "pain_points" in result
        assert len(result["pain_points"]) == 1
        assert result["pain_points"][0]["title"] == "Pain point: Finding the right keywords"

    def test_categorizes_by_success_stories(self, generator, sample_threads):
        """Test that success stories are categorized correctly."""
        result = generator._build_categorized_content(sample_threads, max_per_section=10, excerpt_length=200)

        assert "success_stories" in result
        assert len(result["success_stories"]) == 1
        assert result["success_stories"][0]["title"] == "I tripled my organic traffic"

    def test_categorizes_by_tool_mentions(self, generator, sample_threads):
        """Test that tool comparisons are categorized correctly."""
        result = generator._build_categorized_content(sample_threads, max_per_section=10, excerpt_length=200)

        assert "tool_mentions" in result
        assert len(result["tool_mentions"]) == 1

    def test_respects_max_per_section(self, generator):
        """Test that max_per_section limit is respected."""
        threads = [
            RedditThread(
                id=f"thread_{i}",
                subreddit="SEO",
                title=f"Pain point {i}",
                url=f"/r/SEO/comments/thread_{i}/",
                created_utc=1704067200 + i,
                relevance_score=80.0 - i,
                category="pain_point",
                matched_keywords=[],
            )
            for i in range(15)
        ]

        result = generator._build_categorized_content(threads, max_per_section=5, excerpt_length=200)

        assert len(result["pain_points"]) == 5

    def test_sorts_by_relevance_score(self, generator):
        """Test that items are sorted by relevance score."""
        threads = [
            RedditThread(
                id="low",
                subreddit="SEO",
                title="Low score",
                url="/r/SEO/comments/low/",
                created_utc=1704067200,
                relevance_score=60.0,
                category="pain_point",
                matched_keywords=[],
            ),
            RedditThread(
                id="high",
                subreddit="SEO",
                title="High score",
                url="/r/SEO/comments/high/",
                created_utc=1704067200,
                relevance_score=95.0,
                category="pain_point",
                matched_keywords=[],
            ),
            RedditThread(
                id="medium",
                subreddit="SEO",
                title="Medium score",
                url="/r/SEO/comments/medium/",
                created_utc=1704067200,
                relevance_score=75.0,
                category="pain_point",
                matched_keywords=[],
            ),
        ]

        result = generator._build_categorized_content(threads, max_per_section=10, excerpt_length=200)

        scores = [item["relevance_score"] for item in result["pain_points"]]
        assert scores == [95, 75, 60]

    def test_all_category_mappings_present(self, generator, sample_threads):
        """Test that all category mappings are in the result."""
        result = generator._build_categorized_content(sample_threads, max_per_section=10, excerpt_length=200)

        expected_keys = [
            "pain_points",
            "success_stories",
            "tool_mentions",
            "monetization_insights",
            "ai_visibility_insights",
            "keyword_research_insights",
            "content_generation_insights",
            "competition_insights",
            "image_generation_insights",
            "static_sites_insights",
        ]

        for key in expected_keys:
            assert key in result


class TestBuildRisingContent:
    """Tests for _build_rising_content method."""

    def test_identifies_high_velocity_content(self, generator):
        """Test that high velocity content is identified."""
        # Create thread with high engagement in short time
        threads = [
            RedditThread(
                id="rising",
                subreddit="SEO",
                title="Viral post",
                url="/r/SEO/comments/rising/",
                score=1000,
                num_comments=500,
                created_utc=int(datetime.now().timestamp()) - 3600,  # 1 hour ago
                relevance_score=90.0,
                category="success_story",
                matched_keywords=[],
            )
        ]

        with patch("signalsift.reports.generator.calculate_engagement_velocity", return_value=150.0):
            result = generator._build_rising_content(threads, excerpt_length=200)

        assert "rising_content" in result
        assert len(result["rising_content"]) == 1
        assert result["rising_content"][0]["velocity"] == 150.0

    def test_filters_low_velocity_content(self, generator):
        """Test that low velocity content is filtered out."""
        threads = [
            RedditThread(
                id="slow",
                subreddit="SEO",
                title="Slow post",
                url="/r/SEO/comments/slow/",
                score=10,
                num_comments=2,
                created_utc=int(datetime.now().timestamp()) - 86400,  # 1 day ago
                relevance_score=70.0,
                category="pain_point",
                matched_keywords=[],
            )
        ]

        with patch("signalsift.reports.generator.calculate_engagement_velocity", return_value=0.5):
            result = generator._build_rising_content(threads, excerpt_length=200)

        assert len(result["rising_content"]) == 0

    def test_limits_to_top_10(self, generator):
        """Test that only top 10 rising items are returned."""
        threads = [
            RedditThread(
                id=f"thread_{i}",
                subreddit="SEO",
                title=f"Thread {i}",
                url=f"/r/SEO/comments/thread_{i}/",
                score=100 + i,
                num_comments=50 + i,
                created_utc=int(datetime.now().timestamp()) - 3600,
                relevance_score=80.0,
                category="success_story",
                matched_keywords=[],
            )
            for i in range(15)
        ]

        with patch("signalsift.reports.generator.calculate_engagement_velocity", return_value=50.0):
            result = generator._build_rising_content(threads, excerpt_length=200)

        assert len(result["rising_content"]) == 10

    def test_sorts_by_velocity(self, generator):
        """Test that rising content is sorted by velocity."""
        threads = [
            RedditThread(
                id="slow",
                subreddit="SEO",
                title="Slow",
                url="/r/SEO/comments/slow/",
                score=100,
                num_comments=20,
                created_utc=int(datetime.now().timestamp()) - 3600,
                relevance_score=80.0,
                category="success_story",
                matched_keywords=[],
            ),
            RedditThread(
                id="fast",
                subreddit="SEO",
                title="Fast",
                url="/r/SEO/comments/fast/",
                score=500,
                num_comments=200,
                created_utc=int(datetime.now().timestamp()) - 3600,
                relevance_score=90.0,
                category="success_story",
                matched_keywords=[],
            ),
        ]

        def velocity_side_effect(score, comments, created):
            if score == 500:
                return 100.0
            return 15.0

        with patch("signalsift.reports.generator.calculate_engagement_velocity", side_effect=velocity_side_effect):
            result = generator._build_rising_content(threads, excerpt_length=200)

        assert len(result["rising_content"]) == 2
        assert result["rising_content"][0]["velocity"] == 100.0
        assert result["rising_content"][1]["velocity"] == 15.0


class TestBuildTrendData:
    """Tests for _build_trend_data method."""

    def test_returns_empty_when_disabled(self, generator):
        """Test that empty data is returned when trends disabled."""
        result = generator._build_trend_data(include_trends=False)

        assert result["trends"] == []
        assert result["emerging_trends"] == []
        assert result["declining_trends"] == []
        assert result["new_topics"] == []

    def test_calls_analyze_trends_when_enabled(self, generator):
        """Test that analyze_trends is called when enabled."""
        mock_trend = MagicMock()
        mock_trend.topic = "AI SEO"
        mock_trend.change_percent = 150
        mock_trend.direction = "up"
        mock_trend.current_count = 50

        mock_trends_data = MagicMock()
        mock_trends_data.emerging = [mock_trend]
        mock_trends_data.declining = []
        mock_trends_data.new_topics = []

        with patch("signalsift.processing.trends.analyze_trends", return_value=mock_trends_data):
            result = generator._build_trend_data(include_trends=True)

        assert len(result["trends"]) == 1
        assert result["trends"][0]["topic"] == "AI SEO"
        assert result["trends"][0]["change"] == "+150%"

    def test_handles_trends_import_error(self, generator):
        """Test graceful handling when trends module unavailable."""
        with patch("signalsift.processing.trends.analyze_trends", side_effect=ImportError("No module")):
            result = generator._build_trend_data(include_trends=True)

        assert result["trends"] == []
        assert result["emerging_trends"] == []

    def test_handles_trends_exception(self, generator):
        """Test graceful handling of analysis exceptions."""
        with patch("signalsift.processing.trends.analyze_trends", side_effect=Exception("Analysis failed")):
            result = generator._build_trend_data(include_trends=True)

        assert result["trends"] == []

    def test_formats_declining_trends(self, generator):
        """Test that declining trends are formatted correctly."""
        mock_trend = MagicMock()
        mock_trend.topic = "Old technique"
        mock_trend.change_percent = -30
        mock_trend.current_count = 10

        mock_trends_data = MagicMock()
        mock_trends_data.emerging = []
        mock_trends_data.declining = [mock_trend]
        mock_trends_data.new_topics = []

        with patch("signalsift.processing.trends.analyze_trends", return_value=mock_trends_data):
            result = generator._build_trend_data(include_trends=True)

        assert len(result["declining_trends"]) == 1
        assert result["declining_trends"][0]["change"] == "-30%"


class TestBuildCompetitiveData:
    """Tests for _build_competitive_data method."""

    def test_returns_empty_when_disabled(self, generator):
        """Test that empty data is returned when competitive analysis disabled."""
        result = generator._build_competitive_data(include_competitive=False)

        assert result["competitive_intel"] is None
        assert result["top_tools"] == []
        assert result["feature_gaps"] == []

    def test_calls_get_competitive_intel_when_enabled(self, generator):
        """Test that competitive intel is fetched when enabled."""
        mock_tool_stat = MagicMock()
        mock_tool_stat.tool_name = "Semrush"
        mock_tool_stat.mention_count = 100
        mock_tool_stat.avg_sentiment = 0.5

        mock_intel = MagicMock()
        mock_intel.get_tool_stats.return_value = [mock_tool_stat]
        mock_intel.identify_feature_gaps.return_value = []
        mock_intel.get_market_movers.return_value = []

        with patch("signalsift.processing.competitive.get_competitive_intel", return_value=mock_intel):
            result = generator._build_competitive_data(include_competitive=True)

        assert result["competitive_intel"] is not None
        assert len(result["top_tools"]) == 1
        assert result["top_tools"][0]["name"] == "Semrush"
        assert result["top_tools"][0]["sentiment"] == "positive"

    def test_sentiment_classification(self, generator):
        """Test sentiment classification logic."""
        mock_tool_positive = MagicMock()
        mock_tool_positive.tool_name = "Tool A"
        mock_tool_positive.mention_count = 50
        mock_tool_positive.avg_sentiment = 0.3

        mock_tool_negative = MagicMock()
        mock_tool_negative.tool_name = "Tool B"
        mock_tool_negative.mention_count = 30
        mock_tool_negative.avg_sentiment = -0.3

        mock_tool_neutral = MagicMock()
        mock_tool_neutral.tool_name = "Tool C"
        mock_tool_neutral.mention_count = 20
        mock_tool_neutral.avg_sentiment = 0.05

        mock_intel = MagicMock()
        mock_intel.get_tool_stats.return_value = [mock_tool_positive, mock_tool_negative, mock_tool_neutral]
        mock_intel.identify_feature_gaps.return_value = []
        mock_intel.get_market_movers.return_value = []

        with patch("signalsift.processing.competitive.get_competitive_intel", return_value=mock_intel):
            result = generator._build_competitive_data(include_competitive=True)

        assert result["top_tools"][0]["sentiment"] == "positive"
        assert result["top_tools"][1]["sentiment"] == "negative"
        assert result["top_tools"][2]["sentiment"] == "neutral"

    def test_handles_competitive_import_error(self, generator):
        """Test graceful handling when competitive module unavailable."""
        with patch("signalsift.processing.competitive.get_competitive_intel", side_effect=ImportError("No module")):
            result = generator._build_competitive_data(include_competitive=True)

        assert result["competitive_intel"] is None
        assert result["top_tools"] == []

    def test_feature_gaps_truncation(self, generator):
        """Test that feature descriptions are truncated."""
        mock_gap = MagicMock()
        mock_gap.tool = "Competitor Tool"
        mock_gap.feature_description = "A" * 150  # Long description
        mock_gap.demand_level = "high"
        mock_gap.opportunity = "medium"

        mock_intel = MagicMock()
        mock_intel.get_tool_stats.return_value = []
        mock_intel.identify_feature_gaps.return_value = [mock_gap]
        mock_intel.get_market_movers.return_value = []

        with patch("signalsift.processing.competitive.get_competitive_intel", return_value=mock_intel):
            result = generator._build_competitive_data(include_competitive=True)

        assert len(result["feature_gaps"]) == 1
        assert len(result["feature_gaps"][0]["description"]) == 100


class TestThreadToContext:
    """Tests for _thread_to_context method."""

    def test_converts_thread_to_context(self, generator):
        """Test basic thread to context conversion."""
        thread = RedditThread(
            id="test123",
            subreddit="SEO",
            title="Test title",
            author="test_user",
            selftext="Test content",
            url="/r/SEO/comments/test123/",
            score=100,
            num_comments=25,
            created_utc=1704067200,
            relevance_score=80.0,
            matched_keywords=["test", "SEO"],
            category="pain_point",
        )

        result = generator._thread_to_context(thread, excerpt_length=200)

        assert result["title"] == "Test title"
        assert result["url"] == "/r/SEO/comments/test123/"
        assert result["source_badge"] == "r/SEO"
        assert result["relevance_score"] == 80
        assert result["engagement"] == "100↑ · 25 comments"
        assert result["excerpt"] == "Test content"
        assert result["category"] == "pain_point"

    def test_truncates_long_excerpt(self, generator):
        """Test that long excerpts are truncated."""
        thread = RedditThread(
            id="test123",
            subreddit="SEO",
            title="Test",
            url="/r/SEO/comments/test123/",
            selftext="A" * 300,
            created_utc=1704067200,
            matched_keywords=[],
        )

        result = generator._thread_to_context(thread, excerpt_length=100)

        assert len(result["excerpt"]) == 103  # 100 + "..."
        assert result["excerpt"].endswith("...")

    def test_handles_none_selftext(self, generator):
        """Test handling of threads with no selftext."""
        thread = RedditThread(
            id="test123",
            subreddit="SEO",
            title="Link post",
            url="/r/SEO/comments/test123/",
            selftext=None,
            created_utc=1704067200,
            matched_keywords=[],
        )

        result = generator._thread_to_context(thread, excerpt_length=200)

        assert result["excerpt"] == ""

    def test_rounds_relevance_score(self, generator):
        """Test that relevance score is rounded."""
        thread = RedditThread(
            id="test123",
            subreddit="SEO",
            title="Test",
            url="/r/SEO/comments/test123/",
            created_utc=1704067200,
            relevance_score=85.7,
            matched_keywords=[],
        )

        result = generator._thread_to_context(thread, excerpt_length=200)

        assert result["relevance_score"] == 86

    def test_includes_all_optional_fields(self, generator):
        """Test that all optional insight fields are present."""
        thread = RedditThread(
            id="test123",
            subreddit="SEO",
            title="Test",
            url="/r/SEO/comments/test123/",
            created_utc=1704067200,
            matched_keywords=[],
        )

        result = generator._thread_to_context(thread, excerpt_length=200)

        optional_fields = [
            "feature_suggestion",
            "takeaway",
            "monetization_angle",
            "geo_opportunity",
            "keyword_opportunity",
            "content_strategy",
            "competitive_angle",
            "image_opportunity",
            "tech_insight",
        ]

        for field in optional_fields:
            assert field in result
            assert result[field] is None


class TestVideoToContext:
    """Tests for _video_to_context method."""

    def test_converts_video_to_context(self, generator):
        """Test basic video to context conversion."""
        video = YouTubeVideo(
            id="video123",
            channel_id="channel1",
            channel_name="Test Channel",
            title="Test Video",
            description="Test description",
            url="https://youtube.com/watch?v=video123",
            duration_seconds=600,
            view_count=10000,
            like_count=500,
            published_at=1704067200,
            transcript="Test transcript content",
            transcript_available=True,
            relevance_score=75.0,
            matched_keywords=["test", "video"],
            category="techniques",
        )

        result = generator._video_to_context(video, excerpt_length=200)

        assert result["title"] == "Test Video"
        assert result["url"] == "https://youtube.com/watch?v=video123"
        assert result["channel_name"] == "Test Channel"
        assert result["relevance_score"] == 75
        assert result["view_count"] == 10000
        assert result["like_count"] == 500
        assert result["duration_formatted"] == "10:00"
        assert result["transcript_excerpt"] == "Test transcript content"
        assert result["transcript_available"] is True

    def test_truncates_long_transcript(self, generator):
        """Test that long transcripts are truncated."""
        video = YouTubeVideo(
            id="video123",
            channel_id="channel1",
            title="Test",
            url="https://youtube.com/watch?v=video123",
            published_at=1704067200,
            transcript="A" * 300,
            transcript_available=True,
            matched_keywords=[],
        )

        result = generator._video_to_context(video, excerpt_length=100)

        assert len(result["transcript_excerpt"]) == 103  # 100 + "..."
        assert result["transcript_excerpt"].endswith("...")

    def test_handles_none_transcript(self, generator):
        """Test handling of videos with no transcript."""
        video = YouTubeVideo(
            id="video123",
            channel_id="channel1",
            title="Test",
            url="https://youtube.com/watch?v=video123",
            published_at=1704067200,
            transcript=None,
            transcript_available=False,
            matched_keywords=[],
        )

        result = generator._video_to_context(video, excerpt_length=200)

        assert result["transcript_excerpt"] == ""
        assert result["transcript_available"] is False

    def test_uses_channel_id_fallback(self, generator):
        """Test that channel_id is used when channel_name is None."""
        video = YouTubeVideo(
            id="video123",
            channel_id="UC12345",
            channel_name=None,
            title="Test",
            url="https://youtube.com/watch?v=video123",
            published_at=1704067200,
            matched_keywords=[],
        )

        result = generator._video_to_context(video, excerpt_length=200)

        assert result["channel_name"] == "UC12345"


class TestStaticHelpers:
    """Tests for static helper methods."""

    def test_truncate_short_text(self):
        """Test truncate with text shorter than limit."""
        result = ReportGenerator._truncate("Short text", length=50)
        assert result == "Short text"

    def test_truncate_long_text(self):
        """Test truncate with text longer than limit."""
        result = ReportGenerator._truncate("A" * 100, length=50)
        assert len(result) == 50
        assert result.endswith("...")

    def test_truncate_exact_length(self):
        """Test truncate with text exactly at limit."""
        result = ReportGenerator._truncate("A" * 50, length=50)
        assert result == "A" * 50

    def test_format_number_small(self):
        """Test format_number with small numbers."""
        assert ReportGenerator._format_number(100) == "100"
        assert ReportGenerator._format_number(999) == "999"

    def test_format_number_thousands(self):
        """Test format_number with thousands."""
        assert ReportGenerator._format_number(1000) == "1.0K"
        assert ReportGenerator._format_number(1500) == "1.5K"
        assert ReportGenerator._format_number(15000) == "15.0K"

    def test_format_number_millions(self):
        """Test format_number with millions."""
        assert ReportGenerator._format_number(1_000_000) == "1.0M"
        assert ReportGenerator._format_number(2_500_000) == "2.5M"

    def test_format_datetime(self):
        """Test format_datetime."""
        timestamp = 1704067200  # 2024-01-01 00:00:00 UTC
        result = ReportGenerator._format_datetime(timestamp)
        # Result depends on local timezone, just check format
        assert len(result) == 16  # YYYY-MM-DD HH:MM format
        assert result[4] == "-"
        assert result[7] == "-"
        assert result[10] == " "
        assert result[13] == ":"


class TestGenerate:
    """Tests for the generate method."""

    @pytest.fixture(autouse=True)
    def mock_cache_stats(self):
        with patch("signalsift.reports.generator.get_cache_stats", return_value={}):
            yield

    def test_raises_error_with_no_content(self, generator):
        """Test that ReportError is raised when no content available."""
        with patch("signalsift.reports.generator.get_unprocessed_content", return_value=([], [])):
            with pytest.raises(ReportError, match="No content to include in report"):
                generator.generate()

    def test_uses_unprocessed_content_by_default(self, generator, sample_threads, sample_videos):
        """Test that unprocessed content is fetched by default."""
        with patch("signalsift.reports.generator.get_unprocessed_content", return_value=(sample_threads, sample_videos)):
            with patch("signalsift.reports.generator.insert_report"):
                with patch("signalsift.reports.generator.mark_content_processed"):
                    mock_template = MagicMock()
                    mock_template.render.return_value = "# Report content"

                    with patch.object(type(generator), "env", property(lambda self: MagicMock(get_template=lambda x: mock_template))):
                        output_path = Path("/tmp/test_report.md")
                        with patch.object(Path, "write_text"):
                            with patch.object(Path, "mkdir"):
                                result = generator.generate(output_path=output_path)

        assert result == output_path

    def test_marks_content_as_processed(self, generator, sample_threads, sample_videos):
        """Test that content is marked as processed when preview=False."""
        with patch("signalsift.reports.generator.get_unprocessed_content", return_value=(sample_threads, sample_videos)):
            with patch("signalsift.reports.generator.insert_report") as mock_insert:
                with patch("signalsift.reports.generator.mark_content_processed") as mock_mark:
                    mock_template = MagicMock()
                    mock_template.render.return_value = "# Report"

                    with patch.object(type(generator), "env", property(lambda self: MagicMock(get_template=lambda x: mock_template))):
                        output_path = Path("/tmp/test.md")
                        with patch.object(Path, "write_text"):
                            with patch.object(Path, "mkdir"):
                                generator.generate(output_path=output_path, preview=False)

        mock_insert.assert_called_once()
        mock_mark.assert_called_once()

    def test_does_not_mark_content_in_preview_mode(self, generator, sample_threads, sample_videos):
        """Test that content is not marked as processed when preview=True."""
        with patch("signalsift.reports.generator.get_unprocessed_content", return_value=(sample_threads, sample_videos)):
            with patch("signalsift.reports.generator.insert_report") as mock_insert:
                with patch("signalsift.reports.generator.mark_content_processed") as mock_mark:
                    mock_template = MagicMock()
                    mock_template.render.return_value = "# Report"

                    with patch.object(type(generator), "env", property(lambda self: MagicMock(get_template=lambda x: mock_template))):
                        output_path = Path("/tmp/test.md")
                        with patch.object(Path, "write_text"):
                            with patch.object(Path, "mkdir"):
                                generator.generate(output_path=output_path, preview=True)

        mock_insert.assert_not_called()
        mock_mark.assert_not_called()

    def test_respects_min_score_filter(self, generator, sample_threads, sample_videos):
        """Test that min_score filter is applied."""
        with patch("signalsift.reports.generator.get_unprocessed_content", return_value=(sample_threads, sample_videos)) as mock_get:
            with patch("signalsift.reports.generator.insert_report"):
                with patch("signalsift.reports.generator.mark_content_processed"):
                    mock_template = MagicMock()
                    mock_template.render.return_value = "# Report"

                    with patch.object(type(generator), "env", property(lambda self: MagicMock(get_template=lambda x: mock_template))):
                        output_path = Path("/tmp/test.md")
                        with patch.object(Path, "write_text"):
                            with patch.object(Path, "mkdir"):
                                generator.generate(output_path=output_path, min_score=80.0)

        # Verify min_score was passed to get_unprocessed_content
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs["min_score"] == 80.0

    def test_uses_processed_content_when_requested(self, generator, sample_threads, sample_videos):
        """Test that processed content can be included."""
        with patch("signalsift.database.queries.get_reddit_threads", return_value=sample_threads):
            with patch("signalsift.database.queries.get_youtube_videos", return_value=sample_videos):
                with patch("signalsift.reports.generator.insert_report"):
                    with patch("signalsift.reports.generator.mark_content_processed"):
                        mock_template = MagicMock()
                        mock_template.render.return_value = "# Report"

                        with patch.object(type(generator), "env", property(lambda self: MagicMock(get_template=lambda x: mock_template))):
                            output_path = Path("/tmp/test.md")
                            with patch.object(Path, "write_text"):
                                with patch.object(Path, "mkdir"):
                                    generator.generate(output_path=output_path, include_processed=True)

    def test_creates_output_directory(self, generator, sample_threads, sample_videos):
        """Test that output directory is created if it doesn't exist."""
        with patch("signalsift.reports.generator.get_unprocessed_content", return_value=(sample_threads, sample_videos)):
            with patch("signalsift.reports.generator.insert_report"):
                with patch("signalsift.reports.generator.mark_content_processed"):
                    mock_template = MagicMock()
                    mock_template.render.return_value = "# Report"

                    with patch.object(type(generator), "env", property(lambda self: MagicMock(get_template=lambda x: mock_template))):
                        output_path = Path("/tmp/new_dir/test.md")
                        with patch.object(Path, "write_text"):
                            with patch.object(Path, "mkdir") as mock_mkdir:
                                generator.generate(output_path=output_path)

        # Verify mkdir was called with the correct arguments (may be called multiple times)
        assert mock_mkdir.call_count >= 1
        mock_mkdir.assert_called_with(parents=True, exist_ok=True)


class TestBuildContext:
    """Tests for _build_context method."""

    def test_builds_complete_context(self, generator, sample_threads, sample_videos):
        """Test that complete context is built."""
        with patch("signalsift.reports.generator.get_cache_stats", return_value={"total": 100}):
            with patch("signalsift.reports.generator.get_category_name", side_effect=lambda x: x):
                with patch("signalsift.reports.generator.calculate_engagement_velocity", return_value=5.0):
                    context = generator._build_context(sample_threads, sample_videos)

        # Verify all major sections are present
        assert "generated_at" in context
        assert "reddit_count" in context
        assert "youtube_count" in context
        assert "youtube_videos" in context
        assert "pain_points" in context
        assert "success_stories" in context
        assert "rising_content" in context

    def test_excludes_trends_when_disabled(self, generator, sample_threads, sample_videos):
        """Test that trends are excluded when disabled."""
        with patch("signalsift.reports.generator.get_cache_stats", return_value={}):
            with patch("signalsift.reports.generator.get_category_name", side_effect=lambda x: x):
                with patch("signalsift.reports.generator.calculate_engagement_velocity", return_value=0):
                    context = generator._build_context(
                        sample_threads, sample_videos, include_trends=False
                    )

        assert context["trends"] == []
        assert context["emerging_trends"] == []

    def test_excludes_competitive_when_disabled(self, generator, sample_threads, sample_videos):
        """Test that competitive data is excluded when disabled."""
        with patch("signalsift.reports.generator.get_cache_stats", return_value={}):
            with patch("signalsift.reports.generator.get_category_name", side_effect=lambda x: x):
                with patch("signalsift.reports.generator.calculate_engagement_velocity", return_value=0):
                    context = generator._build_context(
                        sample_threads, sample_videos, include_competitive=False
                    )

        assert context["competitive_intel"] is None
        assert context["top_tools"] == []


class TestBuildGroupedContent:
    """Tests for _build_grouped_content method."""

    def test_groups_threads_by_subreddit(self, generator, sample_threads):
        """Test that threads are grouped by subreddit."""
        result = generator._build_grouped_content(sample_threads, [], excerpt_length=200)

        assert "reddit_by_subreddit" in result
        assert "SEO" in result["reddit_by_subreddit"]
        assert "bigseo" in result["reddit_by_subreddit"]
        assert len(result["reddit_by_subreddit"]["SEO"]) == 3
        assert len(result["reddit_by_subreddit"]["bigseo"]) == 1

    def test_groups_videos_by_channel(self, generator, sample_videos):
        """Test that videos are grouped by channel."""
        result = generator._build_grouped_content([], sample_videos, excerpt_length=200)

        assert "youtube_by_channel" in result
        assert "SEO Guru" in result["youtube_by_channel"]
        assert "Marketing Pro" in result["youtube_by_channel"]

    def test_uses_channel_id_when_name_missing(self, generator):
        """Test that channel_id is used when channel_name is None."""
        videos = [
            YouTubeVideo(
                id="video1",
                channel_id="UC12345",
                channel_name=None,
                title="Test",
                url="https://youtube.com/watch?v=video1",
                published_at=1704067200,
                matched_keywords=[],
            )
        ]

        result = generator._build_grouped_content([], videos, excerpt_length=200)

        assert "UC12345" in result["youtube_by_channel"]


class TestConvenienceFunction:
    """Tests for the generate_report convenience function."""

    @pytest.fixture(autouse=True)
    def mock_cache_stats(self):
        with patch("signalsift.reports.generator.get_cache_stats", return_value={}):
            yield

    def test_convenience_function_creates_generator(self, mock_settings):
        """Test that convenience function creates and uses ReportGenerator."""
        threads = [
            RedditThread(
                id="test1",
                subreddit="SEO",
                title="Test",
                url="/r/SEO/comments/test1/",
                created_utc=1704067200,
                matched_keywords=[],
            )
        ]

        with patch("signalsift.reports.generator.get_settings", return_value=mock_settings):
            with patch("signalsift.reports.generator.get_unprocessed_content", return_value=(threads, [])):
                with patch("signalsift.reports.generator.insert_report"):
                    with patch("signalsift.reports.generator.mark_content_processed"):
                        mock_template = MagicMock()
                        mock_template.render.return_value = "# Report"

                        from signalsift.reports.generator import ReportGenerator, generate_report

                        with patch.object(type(ReportGenerator()), "env", property(lambda self: MagicMock(get_template=lambda x: mock_template))):
                            output_path = Path("/tmp/test.md")
                            with patch.object(Path, "write_text"):
                                with patch.object(Path, "mkdir"):
                                    result = generate_report(output_path=output_path)

        assert result == output_path

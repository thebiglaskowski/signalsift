"""Tests for database models."""

import json

from signalsift.database.models import (
    Keyword,
    RedditThread,
    Report,
    Source,
    YouTubeVideo,
)


class TestRedditThread:
    """Tests for RedditThread model."""

    def test_creation_with_required_fields(self) -> None:
        """Test creating a thread with required fields."""
        thread = RedditThread(
            id="abc123",
            subreddit="SEO",
            title="Test Title",
            url="/r/SEO/comments/abc123",
            created_utc=1704067200,
            captured_at=1704067200,
            matched_keywords=[],
        )
        assert thread.id == "abc123"
        assert thread.subreddit == "SEO"
        assert thread.score == 0  # Default

    def test_parse_keywords_from_json_string(self) -> None:
        """Test that matched_keywords parses JSON strings."""
        thread = RedditThread(
            id="abc123",
            subreddit="SEO",
            title="Test",
            url="/r/SEO/comments/abc123",
            created_utc=1704067200,
            captured_at=1704067200,
            matched_keywords='["seo", "keywords"]',
        )
        assert thread.matched_keywords == ["seo", "keywords"]

    def test_parse_keywords_from_list(self) -> None:
        """Test that matched_keywords accepts lists directly."""
        thread = RedditThread(
            id="abc123",
            subreddit="SEO",
            title="Test",
            url="/r/SEO/comments/abc123",
            created_utc=1704067200,
            captured_at=1704067200,
            matched_keywords=["seo", "keywords"],
        )
        assert thread.matched_keywords == ["seo", "keywords"]

    def test_parse_keywords_invalid_json(self) -> None:
        """Test that invalid JSON returns empty list."""
        thread = RedditThread(
            id="abc123",
            subreddit="SEO",
            title="Test",
            url="/r/SEO/comments/abc123",
            created_utc=1704067200,
            captured_at=1704067200,
            matched_keywords="not valid json",
        )
        assert thread.matched_keywords == []

    def test_to_db_dict(self, sample_reddit_thread: RedditThread) -> None:
        """Test conversion to database dictionary."""
        db_dict = sample_reddit_thread.to_db_dict()

        assert db_dict["id"] == sample_reddit_thread.id
        assert db_dict["subreddit"] == sample_reddit_thread.subreddit
        assert db_dict["processed"] == 0  # Boolean -> int
        assert isinstance(db_dict["matched_keywords"], str)  # JSON string
        assert json.loads(db_dict["matched_keywords"]) == sample_reddit_thread.matched_keywords

    def test_created_datetime_property(self, sample_reddit_thread: RedditThread) -> None:
        """Test created_datetime property."""
        dt = sample_reddit_thread.created_datetime
        # Just verify it returns a datetime and matches the timestamp
        assert dt.timestamp() == sample_reddit_thread.created_utc

    def test_permalink_property(self) -> None:
        """Test permalink generation."""
        thread = RedditThread(
            id="abc123",
            subreddit="SEO",
            title="Test",
            url="/r/SEO/comments/abc123",
            created_utc=1704067200,
            captured_at=1704067200,
            matched_keywords=[],
        )
        assert thread.permalink == "https://reddit.com/r/SEO/comments/abc123"

    def test_permalink_already_full_url(self) -> None:
        """Test permalink when URL is already full."""
        thread = RedditThread(
            id="abc123",
            subreddit="SEO",
            title="Test",
            url="https://reddit.com/r/SEO/comments/abc123",
            created_utc=1704067200,
            captured_at=1704067200,
            matched_keywords=[],
        )
        assert thread.permalink == "https://reddit.com/r/SEO/comments/abc123"


class TestYouTubeVideo:
    """Tests for YouTubeVideo model."""

    def test_creation_with_required_fields(self) -> None:
        """Test creating a video with required fields."""
        video = YouTubeVideo(
            id="dQw4w9WgXcQ",
            channel_id="UC_test",
            title="Test Video",
            url="https://youtube.com/watch?v=dQw4w9WgXcQ",
            published_at=1704067200,
            captured_at=1704067200,
            matched_keywords=[],
        )
        assert video.id == "dQw4w9WgXcQ"
        assert video.view_count == 0  # Default

    def test_duration_formatted_short(self) -> None:
        """Test duration formatting for short videos."""
        video = YouTubeVideo(
            id="test",
            channel_id="UC_test",
            title="Test",
            url="https://youtube.com/watch?v=test",
            published_at=1704067200,
            captured_at=1704067200,
            matched_keywords=[],
            duration_seconds=185,  # 3:05
        )
        assert video.duration_formatted == "3:05"

    def test_duration_formatted_long(self) -> None:
        """Test duration formatting for long videos."""
        video = YouTubeVideo(
            id="test",
            channel_id="UC_test",
            title="Test",
            url="https://youtube.com/watch?v=test",
            published_at=1704067200,
            captured_at=1704067200,
            matched_keywords=[],
            duration_seconds=3725,  # 1:02:05
        )
        assert video.duration_formatted == "1:02:05"

    def test_duration_formatted_none(self) -> None:
        """Test duration formatting when None."""
        video = YouTubeVideo(
            id="test",
            channel_id="UC_test",
            title="Test",
            url="https://youtube.com/watch?v=test",
            published_at=1704067200,
            captured_at=1704067200,
            matched_keywords=[],
            duration_seconds=None,
        )
        assert video.duration_formatted == "N/A"

    def test_to_db_dict(self, sample_youtube_video: YouTubeVideo) -> None:
        """Test conversion to database dictionary."""
        db_dict = sample_youtube_video.to_db_dict()

        assert db_dict["id"] == sample_youtube_video.id
        assert db_dict["transcript_available"] == 1  # Boolean -> int
        assert isinstance(db_dict["matched_keywords"], str)


class TestKeyword:
    """Tests for Keyword model."""

    def test_creation_with_defaults(self) -> None:
        """Test creating keyword with default values."""
        kw = Keyword(keyword="seo", category="tools")
        assert kw.keyword == "seo"
        assert kw.weight == 1.0
        assert kw.enabled is True

    def test_creation_with_custom_weight(self) -> None:
        """Test creating keyword with custom weight."""
        kw = Keyword(keyword="case study", category="success_signals", weight=1.5)
        assert kw.weight == 1.5


class TestSource:
    """Tests for Source model."""

    def test_creation(self) -> None:
        """Test creating a source."""
        source = Source(
            source_type="reddit",
            source_id="SEO",
            display_name="r/SEO",
            tier=1,
        )
        assert source.source_type == "reddit"
        assert source.tier == 1

    def test_last_fetched_datetime_none(self) -> None:
        """Test last_fetched_datetime when not set."""
        source = Source(source_type="reddit", source_id="test")
        assert source.last_fetched_datetime is None

    def test_last_fetched_datetime_set(self) -> None:
        """Test last_fetched_datetime when set."""
        source = Source(
            source_type="reddit",
            source_id="test",
            last_fetched=1704067200,
        )
        assert source.last_fetched_datetime is not None
        assert source.last_fetched_datetime.timestamp() == 1704067200


class TestReport:
    """Tests for Report model."""

    def test_creation(self) -> None:
        """Test creating a report."""
        report = Report(
            id="report_123",
            generated_at=1704067200,
            filepath="/reports/2024-01-01.md",
            reddit_count=10,
            youtube_count=5,
        )
        assert report.id == "report_123"
        assert report.reddit_count == 10

    def test_generated_datetime(self) -> None:
        """Test generated_datetime property."""
        report = Report(
            id="report_123",
            generated_at=1704067200,
            filepath="/reports/test.md",
        )
        assert report.generated_datetime.timestamp() == 1704067200

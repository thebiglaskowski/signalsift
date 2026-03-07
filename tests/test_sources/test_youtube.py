"""Tests for YouTube source adapter."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from signalsift.sources.base import ContentItem
from signalsift.sources.youtube import YouTubeSource


class TestYouTubeSourceInit:
    """Tests for YouTubeSource initialization."""

    def test_init_creates_instance(self):
        """Test that YouTubeSource initializes properly."""
        with patch("signalsift.sources.youtube.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock()
            source = YouTubeSource()

            assert source._youtube is None
            assert source._transcript_api is not None

    def test_get_source_type(self):
        """Test source type identifier."""
        with patch("signalsift.sources.youtube.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock()
            source = YouTubeSource()

            assert source.get_source_type() == "youtube"


class TestYouTubeProperty:
    """Tests for the youtube property."""

    def test_youtube_property_creates_client_with_credentials(self):
        """Test that youtube property creates client when credentials exist."""
        with patch("signalsift.sources.youtube.get_settings") as mock_settings:
            mock = MagicMock()
            mock.has_youtube_credentials.return_value = True
            mock.youtube.api_key = "test_api_key"
            mock_settings.return_value = mock

            source = YouTubeSource()

            with patch("signalsift.sources.youtube.build") as mock_build:
                mock_build.return_value = MagicMock()
                _ = source.youtube

                mock_build.assert_called_once_with("youtube", "v3", developerKey="test_api_key")

    def test_youtube_property_raises_without_credentials(self):
        """Test that youtube property raises error without credentials."""
        from signalsift.exceptions import YouTubeError

        with patch("signalsift.sources.youtube.get_settings") as mock_settings:
            mock = MagicMock()
            mock.has_youtube_credentials.return_value = False
            mock_settings.return_value = mock

            source = YouTubeSource()

            with pytest.raises(YouTubeError, match="YouTube API key not configured"):
                _ = source.youtube

    def test_youtube_property_caches_client(self):
        """Test that youtube property caches the client."""
        with patch("signalsift.sources.youtube.get_settings") as mock_settings:
            mock = MagicMock()
            mock.has_youtube_credentials.return_value = True
            mock.youtube.api_key = "test_api_key"
            mock_settings.return_value = mock

            source = YouTubeSource()

            with patch("signalsift.sources.youtube.build") as mock_build:
                mock_client = MagicMock()
                mock_build.return_value = mock_client

                # Access twice
                client1 = source.youtube
                client2 = source.youtube

                # Should only build once
                mock_build.assert_called_once()
                assert client1 is client2


class TestTestConnection:
    """Tests for test_connection method."""

    @pytest.fixture
    def source(self):
        """Create a YouTubeSource with mocked settings."""
        with patch("signalsift.sources.youtube.get_settings") as mock_settings:
            mock = MagicMock()
            mock.has_youtube_credentials.return_value = True
            mock.youtube.api_key = "test_key"
            mock_settings.return_value = mock
            return YouTubeSource()

    def test_test_connection_success(self, source):
        """Test successful connection test."""
        mock_youtube = MagicMock()
        mock_search = MagicMock()
        mock_list = MagicMock()
        mock_list.execute.return_value = {"items": []}

        mock_search.list.return_value = mock_list
        mock_youtube.search.return_value = mock_search
        source._youtube = mock_youtube

        assert source.test_connection() is True

    def test_test_connection_failure(self, source):
        """Test failed connection test."""
        mock_youtube = MagicMock()
        mock_search = MagicMock()
        mock_list = MagicMock()
        mock_list.execute.side_effect = Exception("API error")

        mock_search.list.return_value = mock_list
        mock_youtube.search.return_value = mock_search
        source._youtube = mock_youtube

        assert source.test_connection() is False


class TestParseDuration:
    """Tests for _parse_duration method."""

    @pytest.fixture
    def source(self):
        """Create a YouTubeSource with mocked settings."""
        with patch("signalsift.sources.youtube.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock()
            return YouTubeSource()

    def test_parse_duration_full(self, source):
        """Test parsing duration with hours, minutes, and seconds."""
        assert source._parse_duration("PT1H30M15S") == 5415

    def test_parse_duration_minutes_seconds(self, source):
        """Test parsing duration with minutes and seconds."""
        assert source._parse_duration("PT10M30S") == 630

    def test_parse_duration_only_minutes(self, source):
        """Test parsing duration with only minutes."""
        assert source._parse_duration("PT5M") == 300

    def test_parse_duration_only_seconds(self, source):
        """Test parsing duration with only seconds."""
        assert source._parse_duration("PT45S") == 45

    def test_parse_duration_only_hours(self, source):
        """Test parsing duration with only hours."""
        assert source._parse_duration("PT2H") == 7200

    def test_parse_duration_zero(self, source):
        """Test parsing zero duration."""
        assert source._parse_duration("PT0S") == 0

    def test_parse_duration_invalid(self, source):
        """Test parsing invalid duration string."""
        assert source._parse_duration("invalid") == 0


class TestCleanTranscript:
    """Tests for _clean_transcript method."""

    @pytest.fixture
    def source(self):
        """Create a YouTubeSource with mocked settings."""
        with patch("signalsift.sources.youtube.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock()
            return YouTubeSource()

    def test_clean_transcript_removes_music(self, source):
        """Test removing [Music] artifacts."""
        text = "Hello [Music] world"
        result = source._clean_transcript(text)
        assert "[Music]" not in result
        assert "Hello" in result
        assert "world" in result

    def test_clean_transcript_removes_applause(self, source):
        """Test removing [Applause] artifacts."""
        text = "Thank you [Applause] everyone"
        result = source._clean_transcript(text)
        assert "[Applause]" not in result

    def test_clean_transcript_removes_multiple_artifacts(self, source):
        """Test removing multiple artifact types."""
        text = "[Music] Hello [Laughter] and [Applause]"
        result = source._clean_transcript(text)
        assert "[Music]" not in result
        assert "[Laughter]" not in result
        assert "[Applause]" not in result
        assert "Hello" in result

    def test_clean_transcript_normalizes_whitespace(self, source):
        """Test normalizing whitespace."""
        text = "Hello    world\n\ntest"
        result = source._clean_transcript(text)
        assert "  " not in result
        assert "\n" not in result

    def test_clean_transcript_strips_text(self, source):
        """Test stripping leading/trailing whitespace."""
        text = "  Hello world  "
        result = source._clean_transcript(text)
        assert result == "Hello world"


class TestGetTranscript:
    """Tests for _get_transcript method."""

    @pytest.fixture
    def source(self):
        """Create a YouTubeSource with mocked settings."""
        with patch("signalsift.sources.youtube.get_settings") as mock_settings:
            mock = MagicMock()
            mock.youtube.transcript_language = "en"
            mock.youtube.transcript_max_length = 10000
            mock_settings.return_value = mock
            return YouTubeSource()

    def test_get_transcript_success(self, source):
        """Test successful transcript fetch."""
        mock_transcript = [
            MagicMock(text="Hello"),
            MagicMock(text="world"),
            MagicMock(text="test"),
        ]
        source._transcript_api.fetch = MagicMock(return_value=mock_transcript)

        result = source._get_transcript("video123")

        assert result is not None
        assert "Hello" in result
        assert "world" in result

    def test_get_transcript_no_transcript(self, source):
        """Test when no transcript available."""
        from youtube_transcript_api._errors import NoTranscriptFound

        source._transcript_api.fetch = MagicMock(
            side_effect=NoTranscriptFound("video123", [], None)
        )

        result = source._get_transcript("video123")

        assert result is None

    def test_get_transcript_disabled(self, source):
        """Test when transcripts are disabled."""
        from youtube_transcript_api._errors import TranscriptsDisabled

        source._transcript_api.fetch = MagicMock(side_effect=TranscriptsDisabled("video123"))

        result = source._get_transcript("video123")

        assert result is None

    def test_get_transcript_video_unavailable(self, source):
        """Test when video is unavailable."""
        from youtube_transcript_api._errors import VideoUnavailable

        source._transcript_api.fetch = MagicMock(side_effect=VideoUnavailable("video123"))

        result = source._get_transcript("video123")

        assert result is None


class TestContentItemToVideo:
    """Tests for content_item_to_video method."""

    @pytest.fixture
    def source(self):
        """Create a YouTubeSource with mocked settings."""
        with patch("signalsift.sources.youtube.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock()
            return YouTubeSource()

    def test_content_item_to_video_basic(self, source):
        """Test converting ContentItem to YouTubeVideo."""
        item = ContentItem(
            id="abc123",
            source_type="youtube",
            source_id="channel123",
            title="Test Video Title",
            content="This is the transcript content",
            url="https://www.youtube.com/watch?v=abc123",
            created_at=datetime(2024, 1, 15, 12, 0, 0),
            metadata={
                "channel_name": "Test Channel",
                "description": "Video description",
                "duration_seconds": 600,
                "view_count": 10000,
                "like_count": 500,
                "transcript_available": True,
            },
        )

        video = source.content_item_to_video(item)

        assert video.id == "abc123"
        assert video.channel_id == "channel123"
        assert video.channel_name == "Test Channel"
        assert video.title == "Test Video Title"
        assert video.description == "Video description"
        assert video.duration_seconds == 600
        assert video.view_count == 10000
        assert video.like_count == 500
        assert video.transcript == "This is the transcript content"
        assert video.transcript_available is True
        assert video.content_hash is not None

    def test_content_item_to_video_no_transcript(self, source):
        """Test converting ContentItem without transcript."""
        item = ContentItem(
            id="xyz789",
            source_type="youtube",
            source_id="channel456",
            title="No Transcript Video",
            content="",
            url="https://www.youtube.com/watch?v=xyz789",
            created_at=datetime(2024, 1, 10, 10, 0, 0),
            metadata={
                "channel_name": "Another Channel",
                "duration_seconds": 300,
                "view_count": 5000,
                "like_count": 100,
                "transcript_available": False,
            },
        )

        video = source.content_item_to_video(item)

        assert video.transcript is None
        assert video.transcript_available is False


class TestFetch:
    """Tests for fetch method."""

    @pytest.fixture
    def source(self):
        """Create a YouTubeSource with mocked settings."""
        with patch("signalsift.sources.youtube.get_settings") as mock_settings:
            mock = MagicMock()
            mock.youtube.videos_per_channel = 10
            mock_settings.return_value = mock
            return YouTubeSource()

    def test_fetch_no_sources(self, source):
        """Test fetch when no sources are configured."""
        with patch("signalsift.sources.youtube.get_sources_by_type", return_value=[]):
            result = source.fetch()

            assert result == []

    def test_fetch_with_sources(self, source):
        """Test fetch with configured sources."""
        mock_source = MagicMock()
        mock_source.source_id = "channel123"
        mock_source.display_name = "Test Channel"
        mock_source.tier = 1

        with (
            patch("signalsift.sources.youtube.get_sources_by_type", return_value=[mock_source]),
            patch.object(source, "_fetch_channel", return_value=[]) as mock_fetch,
            patch("signalsift.sources.youtube.update_source_last_fetched"),
            patch("time.sleep"),
        ):
            result = source.fetch(since=datetime(2024, 1, 1), limit=5)

            mock_fetch.assert_called_once()
            assert result == []


class TestFetchChannel:
    """Tests for fetch_channel method."""

    @pytest.fixture
    def source(self):
        """Create a YouTubeSource with mocked settings."""
        with patch("signalsift.sources.youtube.get_settings") as mock_settings:
            mock = MagicMock()
            mock.youtube.videos_per_channel = 10
            mock_settings.return_value = mock
            return YouTubeSource()

    def test_fetch_channel_calls_internal_method(self, source):
        """Test that fetch_channel delegates to _fetch_channel."""
        with patch.object(source, "_fetch_channel", return_value=[]) as mock_fetch:
            result = source.fetch_channel(
                channel_id="channel123",
                channel_name="Test Channel",
                since=datetime(2024, 1, 1),
                limit=5,
            )

            mock_fetch.assert_called_once()
            assert result == []

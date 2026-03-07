"""Tests for Reddit RSS source adapter."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from signalsift.sources.reddit_rss import RedditRSSSource


class TestRedditRSSSource:
    """Tests for RedditRSSSource class."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.reddit.posts_per_subreddit = 25
        settings.reddit.max_age_days = 7
        settings.reddit.request_delay_seconds = 0.1
        return settings

    @pytest.fixture
    def source(self, mock_settings):
        """Create RedditRSSSource with mocked settings."""
        with patch("signalsift.sources.reddit_rss.get_settings", return_value=mock_settings):
            return RedditRSSSource()

    def test_get_source_type(self, source):
        """Test source type identifier."""
        assert source.get_source_type() == "reddit"

    def test_test_connection_success(self, source):
        """Test successful connection test."""
        with patch.object(source._session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            assert source.test_connection() is True
            mock_get.assert_called_once()

    def test_test_connection_failure(self, source):
        """Test failed connection test."""
        with patch.object(source._session, "get") as mock_get:
            mock_get.side_effect = Exception("Connection failed")

            assert source.test_connection() is False

    def test_test_connection_non_200(self, source):
        """Test connection test with non-200 response."""
        with patch.object(source._session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 503
            mock_get.return_value = mock_response

            assert source.test_connection() is False


class TestExtractPostId:
    """Tests for _extract_post_id method."""

    @pytest.fixture
    def source(self):
        """Create source with mocked settings."""
        with patch("signalsift.sources.reddit_rss.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock()
            return RedditRSSSource()

    def test_extract_post_id_valid_link(self, source):
        """Test extracting post ID from valid Reddit link."""
        entry = {"link": "https://www.reddit.com/r/SEO/comments/abc123/post_title"}
        assert source._extract_post_id(entry) == "abc123"

    def test_extract_post_id_no_comments(self, source):
        """Test extracting post ID when no /comments/ in link."""
        entry = {"link": "https://www.reddit.com/r/SEO/"}
        assert source._extract_post_id(entry) is None

    def test_extract_post_id_empty_link(self, source):
        """Test extracting post ID with empty link."""
        entry = {"link": ""}
        assert source._extract_post_id(entry) is None

    def test_extract_post_id_no_link(self, source):
        """Test extracting post ID with no link field."""
        entry = {}
        assert source._extract_post_id(entry) is None


class TestExtractContent:
    """Tests for _extract_content method."""

    @pytest.fixture
    def source(self):
        """Create source with mocked settings."""
        with patch("signalsift.sources.reddit_rss.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock()
            return RedditRSSSource()

    def _make_entry(self, **kwargs):
        """Create a mock feedparser entry with attribute access."""
        entry = MagicMock()
        # Set up __contains__ for 'in' checks
        keys = set(kwargs.keys())
        entry.__contains__ = lambda self, x: x in keys

        for key, value in kwargs.items():
            setattr(entry, key, value)

        # Ensure missing attributes return MagicMock that evaluates to False
        for key in ["content", "summary"]:
            if key not in kwargs:
                mock_attr = MagicMock()
                mock_attr.__bool__ = lambda self: False
                setattr(entry, key, mock_attr)

        return entry

    def test_extract_content_from_content_field(self, source):
        """Test extracting content from content field."""
        entry = self._make_entry(content=[{"value": "<p>Test content here</p>"}])
        result = source._extract_content(entry)
        assert "Test content here" in result

    def test_extract_content_from_summary(self, source):
        """Test extracting content from summary field."""
        entry = self._make_entry(summary="<p>Summary content</p>")
        result = source._extract_content(entry)
        assert "Summary content" in result

    def test_extract_content_strips_html(self, source):
        """Test that HTML tags are stripped."""
        entry = self._make_entry(
            summary="<div><p><strong>Bold</strong> and <em>italic</em></p></div>"
        )
        result = source._extract_content(entry)
        assert "Bold" in result
        assert "italic" in result
        assert "<" not in result

    def test_extract_content_decodes_entities(self, source):
        """Test that HTML entities are decoded."""
        entry = self._make_entry(summary="Test &amp; more &lt;content&gt;")
        result = source._extract_content(entry)
        assert "Test & more <content>" in result

    def test_extract_content_removes_link_markers(self, source):
        """Test that [link] [comments] markers are removed."""
        entry = self._make_entry(summary="Content here [link] [comments]")
        result = source._extract_content(entry)
        assert "[link]" not in result
        assert "[comments]" not in result
        assert "Content here" in result

    def test_extract_content_empty(self, source):
        """Test extracting content when empty."""
        entry = MagicMock()
        entry.__contains__ = lambda self, x: False
        assert source._extract_content(entry) == ""


class TestProcessEntry:
    """Tests for _process_entry method."""

    @pytest.fixture
    def source(self):
        """Create source with mocked settings."""
        with patch("signalsift.sources.reddit_rss.get_settings") as mock_settings:
            mock = MagicMock()
            mock.reddit.max_age_days = 7
            mock_settings.return_value = mock
            return RedditRSSSource()

    def test_process_entry_valid(self, source):
        """Test processing a valid RSS entry."""
        # Create a mock entry that behaves like feedparser entry
        entry = MagicMock()
        entry.get = MagicMock(
            side_effect=lambda k, d=None: {
                "link": "https://www.reddit.com/r/SEO/comments/xyz789/test_post",
                "title": "Test Post Title",
                "published": "Mon, 01 Jan 2024 12:00:00 GMT",
            }.get(k, d)
        )
        entry.__contains__ = lambda self, x: x in ["content", "summary", "author_detail"]
        entry.content = [{"value": "<p>Test content here</p>"}]
        entry.summary = ""
        entry.author_detail = MagicMock()
        entry.author_detail.get = lambda k, d=None: {"name": "testuser"}.get(k, d)

        since = datetime(2023, 1, 1)

        with patch("signalsift.sources.reddit_rss.thread_exists", return_value=False):
            result = source._process_entry(entry, "SEO", 2, since)

        assert result is not None
        assert result.id == "xyz789"
        assert result.title == "Test Post Title"
        assert result.source_id == "SEO"

    def test_process_entry_too_old(self, source):
        """Test processing entry that is too old."""
        entry = {
            "link": "https://www.reddit.com/r/SEO/comments/xyz789/test_post",
            "title": "Old Post",
            "summary": "<p>Content</p>",
            "published": "Mon, 01 Jan 2020 12:00:00 GMT",
        }
        since = datetime(2023, 1, 1)

        with patch("signalsift.sources.reddit_rss.thread_exists", return_value=False):
            result = source._process_entry(entry, "SEO", 2, since)

        assert result is None

    def test_process_entry_already_exists(self, source):
        """Test processing entry that already exists in cache."""
        entry = {
            "link": "https://www.reddit.com/r/SEO/comments/xyz789/test_post",
            "title": "Test Post",
            "summary": "<p>Content</p>",
            "published": "Mon, 01 Jan 2024 12:00:00 GMT",
        }
        since = datetime(2023, 1, 1)

        with patch("signalsift.sources.reddit_rss.thread_exists", return_value=True):
            result = source._process_entry(entry, "SEO", 2, since)

        assert result is None

    def test_process_entry_no_title(self, source):
        """Test processing entry with no title."""
        entry = {
            "link": "https://www.reddit.com/r/SEO/comments/xyz789/test_post",
            "title": "",
            "summary": "<p>Content</p>",
        }
        since = datetime(2023, 1, 1)

        with patch("signalsift.sources.reddit_rss.thread_exists", return_value=False):
            result = source._process_entry(entry, "SEO", 2, since)

        assert result is None

    def test_process_entry_removed_content(self, source):
        """Test processing entry with [removed] content."""
        entry = {
            "link": "https://www.reddit.com/r/SEO/comments/xyz789/test_post",
            "title": "Test Post",
            "summary": "[removed]",
            "published": "Mon, 01 Jan 2024 12:00:00 GMT",
        }
        since = datetime(2023, 1, 1)

        with patch("signalsift.sources.reddit_rss.thread_exists", return_value=False):
            result = source._process_entry(entry, "SEO", 2, since)

        assert result is None


class TestContentItemToThread:
    """Tests for content_item_to_thread method."""

    @pytest.fixture
    def source(self):
        """Create source with mocked settings."""
        with patch("signalsift.sources.reddit_rss.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock()
            return RedditRSSSource()

    def test_content_item_to_thread(self, source):
        """Test converting ContentItem to RedditThread."""
        from signalsift.sources.base import ContentItem

        item = ContentItem(
            id="test123",
            source_type="reddit",
            source_id="SEO",
            title="Test Title",
            content="Test content body",
            url="https://reddit.com/r/SEO/comments/test123",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            metadata={
                "author": "testuser",
                "score": 100,
                "num_comments": 25,
                "flair": "Discussion",
            },
        )

        thread = source.content_item_to_thread(item)

        assert thread.id == "test123"
        assert thread.subreddit == "SEO"
        assert thread.title == "Test Title"
        assert thread.selftext == "Test content body"
        assert thread.author == "testuser"
        assert thread.score == 100
        assert thread.num_comments == 25
        assert thread.flair == "Discussion"
        assert thread.content_hash is not None


class TestFetchSubreddit:
    """Tests for fetch_subreddit method."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.reddit.posts_per_subreddit = 25
        settings.reddit.max_age_days = 7
        settings.reddit.request_delay_seconds = 0
        return settings

    @pytest.fixture
    def source(self, mock_settings):
        """Create source with mocked settings."""
        with patch("signalsift.sources.reddit_rss.get_settings", return_value=mock_settings):
            return RedditRSSSource()

    def test_fetch_subreddit_404(self, source):
        """Test fetching from non-existent subreddit."""
        with patch.object(source._session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response

            result = source.fetch_subreddit("nonexistent_sub")

            assert result == []

    def test_fetch_subreddit_rate_limited(self, source):
        """Test handling rate limit (429) response."""
        with patch.object(source._session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_get.return_value = mock_response

            with patch("time.sleep"):  # Don't actually sleep
                result = source.fetch_subreddit("test_sub", limit=5)

            assert result == []


class TestFetch:
    """Tests for fetch method."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.reddit.posts_per_subreddit = 25
        settings.reddit.max_age_days = 7
        settings.reddit.request_delay_seconds = 0
        return settings

    @pytest.fixture
    def source(self, mock_settings):
        """Create source with mocked settings."""
        with patch("signalsift.sources.reddit_rss.get_settings", return_value=mock_settings):
            return RedditRSSSource()

    def test_fetch_no_sources(self, source):
        """Test fetching when no sources are configured."""
        with patch("signalsift.sources.reddit_rss.get_sources_by_type", return_value=[]):
            result = source.fetch()

        assert result == []

    def test_fetch_with_sources(self, source):
        """Test fetching with configured sources."""
        mock_source = MagicMock()
        mock_source.source_id = "SEO"
        mock_source.tier = 1

        with (
            patch("signalsift.sources.reddit_rss.get_sources_by_type", return_value=[mock_source]),
            patch.object(source, "_fetch_subreddit", return_value=[]) as mock_fetch,
            patch("signalsift.sources.reddit_rss.update_source_last_fetched"),
            patch("time.sleep"),
        ):
            result = source.fetch(since=datetime(2024, 1, 1), limit=10)

            mock_fetch.assert_called_once()
            assert result == []

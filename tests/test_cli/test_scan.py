"""Tests for scan CLI command."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from signalsift.cli.main import cli
from signalsift.sources.base import ContentItem


class TestScanCommand:
    """Tests for the scan command."""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner."""
        return CliRunner()

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.reddit.mode = "rss"
        settings.reddit.max_age_days = 7
        settings.reddit.posts_per_subreddit = 25
        settings.reddit.request_delay_seconds = 0
        settings.youtube.videos_per_channel = 10
        settings.has_reddit_credentials.return_value = False
        settings.has_youtube_credentials.return_value = False
        return settings

    def test_scan_help(self, runner):
        """Test scan --help shows usage."""
        with (
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.cli.main.setup_logging"),
        ):
            result = runner.invoke(cli, ["scan", "--help"])

            assert result.exit_code == 0
            assert "Fetch new content" in result.output
            assert "--reddit-only" in result.output
            assert "--youtube-only" in result.output
            assert "--hackernews-only" in result.output

    def test_scan_no_credentials(self, runner, mock_settings):
        """Test scan with no credentials configured."""
        with (
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.cli.main.setup_logging"),
            patch("signalsift.cli.scan.get_settings", return_value=mock_settings),
            patch("signalsift.cli.scan.RedditRSSSource") as mock_rss,
        ):
            mock_rss.return_value.fetch.return_value = []
            result = runner.invoke(cli, ["scan"])

            # Should complete but may warn about credentials
            assert result.exit_code == 0

    def test_scan_reddit_only_flag(self, runner, mock_settings):
        """Test scan --reddit-only flag."""
        mock_settings.reddit.mode = "rss"

        with (
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.cli.main.setup_logging"),
            patch("signalsift.cli.scan.get_settings", return_value=mock_settings),
            patch("signalsift.cli.scan.RedditRSSSource") as mock_reddit,
        ):
            mock_source = MagicMock()
            mock_source.fetch.return_value = []
            mock_reddit.return_value = mock_source

            result = runner.invoke(cli, ["scan", "--reddit-only"])

            assert result.exit_code == 0
            # Reddit source should be used
            mock_reddit.assert_called()

    def test_scan_youtube_only_flag(self, runner, mock_settings):
        """Test scan --youtube-only flag."""
        mock_settings.has_youtube_credentials.return_value = True
        mock_settings.youtube.api_key = "test_key"

        with (
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.cli.main.setup_logging"),
            patch("signalsift.cli.scan.get_settings", return_value=mock_settings),
            patch("signalsift.cli.scan.YouTubeSource") as mock_youtube,
        ):
            mock_source = MagicMock()
            mock_source.fetch.return_value = []
            mock_youtube.return_value = mock_source

            result = runner.invoke(cli, ["scan", "--youtube-only"])

            # Should complete
            assert result.exit_code == 0

    def test_scan_hackernews_only_flag(self, runner, mock_settings):
        """Test scan --hackernews-only flag."""
        with (
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.cli.main.setup_logging"),
            patch("signalsift.cli.scan.get_settings", return_value=mock_settings),
        ):
            result = runner.invoke(cli, ["scan", "--hackernews-only"])

            assert result.exit_code == 0

    def test_scan_days_option(self, runner, mock_settings):
        """Test scan --days option."""
        mock_settings.reddit.mode = "rss"

        with (
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.cli.main.setup_logging"),
            patch("signalsift.cli.scan.get_settings", return_value=mock_settings),
            patch("signalsift.cli.scan.RedditRSSSource") as mock_reddit,
        ):
            mock_source = MagicMock()
            mock_source.fetch.return_value = []
            mock_reddit.return_value = mock_source

            result = runner.invoke(cli, ["scan", "--reddit-only", "--days", "3"])

            assert result.exit_code == 0

    def test_scan_limit_option(self, runner, mock_settings):
        """Test scan --limit option."""
        mock_settings.reddit.mode = "rss"

        with (
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.cli.main.setup_logging"),
            patch("signalsift.cli.scan.get_settings", return_value=mock_settings),
            patch("signalsift.cli.scan.RedditRSSSource") as mock_reddit,
        ):
            mock_source = MagicMock()
            mock_source.fetch.return_value = []
            mock_reddit.return_value = mock_source

            result = runner.invoke(cli, ["scan", "--reddit-only", "--limit", "10"])

            assert result.exit_code == 0

    def test_scan_dry_run_flag(self, runner, mock_settings):
        """Test scan --dry-run flag."""
        mock_settings.reddit.mode = "rss"

        mock_item = ContentItem(
            id="test123",
            source_type="reddit",
            source_id="SEO",
            title="Test Post",
            content="Test content",
            url="https://reddit.com/r/SEO/test",
            created_at=datetime.now(),
            metadata={},
        )

        with (
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.cli.main.setup_logging"),
            patch("signalsift.cli.scan.get_settings", return_value=mock_settings),
            patch("signalsift.cli.scan.RedditRSSSource") as mock_reddit,
            patch("signalsift.cli.scan.process_reddit_thread") as mock_process,
        ):
            mock_source = MagicMock()
            mock_source.fetch.return_value = [mock_item]
            mock_reddit.return_value = mock_source
            mock_process.return_value = MagicMock(title="Test Post", relevance_score=75.0)

            result = runner.invoke(cli, ["scan", "--reddit-only", "--dry-run"])

            assert result.exit_code == 0
            assert "dry run" in result.output.lower() or "would" in result.output.lower()

    def test_scan_subreddits_option(self, runner, mock_settings):
        """Test scan --subreddits option."""
        mock_settings.reddit.mode = "rss"

        with (
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.cli.main.setup_logging"),
            patch("signalsift.cli.scan.get_settings", return_value=mock_settings),
            patch("signalsift.cli.scan.RedditRSSSource") as mock_reddit,
        ):
            mock_source = MagicMock()
            mock_source.fetch_subreddit.return_value = []
            mock_reddit.return_value = mock_source

            result = runner.invoke(cli, ["scan", "--subreddits", "SEO,marketing"])

            assert result.exit_code == 0

    def test_scan_channels_option(self, runner, mock_settings):
        """Test scan --channels option."""
        mock_settings.has_youtube_credentials.return_value = True
        mock_settings.youtube.api_key = "test_key"

        with (
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.cli.main.setup_logging"),
            patch("signalsift.cli.scan.get_settings", return_value=mock_settings),
            patch("signalsift.cli.scan.RedditRSSSource") as mock_rss,
            patch("signalsift.cli.scan.YouTubeSource") as mock_youtube,
        ):
            mock_rss.return_value.fetch.return_value = []
            mock_source = MagicMock()
            mock_source.fetch_channel.return_value = []
            mock_source.fetch.return_value = []
            mock_youtube.return_value = mock_source

            result = runner.invoke(cli, ["scan", "--channels", "UC123,UC456"])

            assert result.exit_code == 0


class TestScanProcessing:
    """Tests for scan result processing."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.reddit.mode = "rss"
        settings.reddit.max_age_days = 7
        settings.reddit.posts_per_subreddit = 25
        settings.reddit.request_delay_seconds = 0
        settings.youtube.videos_per_channel = 10
        settings.has_reddit_credentials.return_value = False
        settings.has_youtube_credentials.return_value = False
        return settings

    def test_scan_processes_reddit_content(self, mock_settings):
        """Test that scan processes Reddit content."""
        runner = CliRunner()

        mock_item = ContentItem(
            id="abc123",
            source_type="reddit",
            source_id="SEO",
            title="SEO Tips",
            content="Great SEO tips here",
            url="https://reddit.com/r/SEO/abc123",
            created_at=datetime.now(),
            metadata={"author": "testuser", "score": 100, "num_comments": 50},
        )

        with (
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.cli.main.setup_logging"),
            patch("signalsift.cli.scan.get_settings", return_value=mock_settings),
            patch("signalsift.cli.scan.RedditRSSSource") as mock_reddit,
            patch("signalsift.cli.scan.insert_reddit_threads_batch"),
            patch("signalsift.cli.scan.process_reddit_thread") as mock_process,
        ):
            mock_source = MagicMock()
            mock_source.fetch.return_value = [mock_item]
            mock_source.content_item_to_thread.return_value = MagicMock()
            mock_reddit.return_value = mock_source

            mock_process.return_value = MagicMock()

            result = runner.invoke(cli, ["scan", "--reddit-only"])

            assert result.exit_code == 0


class TestScanErrors:
    """Tests for scan error handling."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.reddit.mode = "rss"
        settings.reddit.max_age_days = 7
        settings.reddit.posts_per_subreddit = 25
        settings.reddit.request_delay_seconds = 0
        settings.youtube.videos_per_channel = 10
        settings.has_reddit_credentials.return_value = False
        settings.has_youtube_credentials.return_value = False
        return settings

    def test_scan_handles_reddit_error(self, mock_settings):
        """Test that scan handles Reddit errors gracefully."""
        from signalsift.exceptions import RedditError

        runner = CliRunner()

        with (
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.cli.main.setup_logging"),
            patch("signalsift.cli.scan.get_settings", return_value=mock_settings),
            patch("signalsift.cli.scan.RedditRSSSource") as mock_reddit,
        ):
            mock_source = MagicMock()
            mock_source.fetch.side_effect = RedditError("API error")
            mock_reddit.return_value = mock_source

            result = runner.invoke(cli, ["scan", "--reddit-only"])

            # Should handle error gracefully
            assert result.exit_code == 0

    def test_scan_handles_youtube_error(self, mock_settings):
        """Test that scan handles YouTube errors gracefully."""
        from signalsift.exceptions import YouTubeError

        runner = CliRunner()
        mock_settings.has_youtube_credentials.return_value = True
        mock_settings.youtube.api_key = "test_key"

        with (
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.cli.main.setup_logging"),
            patch("signalsift.cli.scan.get_settings", return_value=mock_settings),
            patch("signalsift.cli.scan.YouTubeSource") as mock_youtube,
        ):
            mock_source = MagicMock()
            mock_source.fetch.side_effect = YouTubeError("API error")
            mock_youtube.return_value = mock_source

            result = runner.invoke(cli, ["scan", "--youtube-only"])

            # Should handle error gracefully
            assert result.exit_code == 0

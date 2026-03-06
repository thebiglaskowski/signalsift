"""Tests for settings configuration module."""

from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from signalsift.config.settings import (
    DatabaseSettings,
    LoggingSettings,
    RedditSettings,
    ReportSettings,
    ScoringSettings,
    ScoringWeights,
    Settings,
    YouTubeSettings,
    get_settings,
)


class TestDatabaseSettings:
    """Tests for DatabaseSettings model."""

    def test_default_path(self):
        """Test that default path is set."""
        settings = DatabaseSettings()
        assert settings.path is not None

    def test_custom_path(self):
        """Test setting a custom path."""
        settings = DatabaseSettings(path=Path("/custom/path.db"))
        assert settings.path == Path("/custom/path.db")


class TestRedditSettings:
    """Tests for RedditSettings model."""

    def test_default_values(self):
        """Test default values."""
        settings = RedditSettings()
        assert settings.mode == "rss"
        assert settings.client_id == ""
        assert settings.client_secret == ""
        assert settings.include_comments is False

    def test_api_mode_validation(self):
        """Test valid API mode."""
        settings = RedditSettings(mode="api")
        assert settings.mode == "api"

    def test_rss_mode_validation(self):
        """Test valid RSS mode."""
        settings = RedditSettings(mode="rss")
        assert settings.mode == "rss"

    def test_mode_case_insensitive(self):
        """Test that mode is case insensitive."""
        settings = RedditSettings(mode="RSS")
        assert settings.mode == "rss"

    def test_invalid_mode_raises_error(self):
        """Test that invalid mode raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            RedditSettings(mode="invalid_mode")

        assert "Invalid Reddit mode" in str(exc_info.value)

    def test_custom_values(self):
        """Test setting custom values."""
        settings = RedditSettings(
            mode="api",
            client_id="test_client",
            client_secret="test_secret",
            min_score=50,
            min_comments=10,
        )
        assert settings.mode == "api"
        assert settings.client_id == "test_client"
        assert settings.client_secret == "test_secret"
        assert settings.min_score == 50
        assert settings.min_comments == 10


class TestYouTubeSettings:
    """Tests for YouTubeSettings model."""

    def test_default_values(self):
        """Test default values."""
        settings = YouTubeSettings()
        assert settings.api_key == ""
        assert settings.include_search is True

    def test_custom_values(self):
        """Test setting custom values."""
        settings = YouTubeSettings(
            api_key="test_key",
            min_duration_seconds=120,
            max_duration_seconds=1800,
        )
        assert settings.api_key == "test_key"
        assert settings.min_duration_seconds == 120
        assert settings.max_duration_seconds == 1800


class TestScoringWeights:
    """Tests for ScoringWeights model."""

    def test_default_values(self):
        """Test default weight values."""
        weights = ScoringWeights()
        assert weights.engagement == 1.0
        assert weights.keywords == 1.2
        assert weights.content_quality == 1.0
        assert weights.source_tier == 0.8

    def test_custom_values(self):
        """Test setting custom weight values."""
        weights = ScoringWeights(engagement=2.0, keywords=1.5)
        assert weights.engagement == 2.0
        assert weights.keywords == 1.5


class TestScoringSettings:
    """Tests for ScoringSettings model."""

    def test_default_values(self):
        """Test default values."""
        settings = ScoringSettings()
        assert settings.min_relevance_score is not None
        assert settings.weights is not None

    def test_custom_weights(self):
        """Test setting custom weights."""
        weights = ScoringWeights(engagement=2.0)
        settings = ScoringSettings(weights=weights)
        assert settings.weights.engagement == 2.0


class TestReportSettings:
    """Tests for ReportSettings model."""

    def test_default_values(self):
        """Test default values."""
        settings = ReportSettings()
        assert settings.filename_format == "{date}.md"
        assert settings.include_full_index is True

    def test_custom_values(self):
        """Test setting custom values."""
        settings = ReportSettings(
            filename_format="report_{date}.md",
            max_items_per_section=20,
        )
        assert settings.filename_format == "report_{date}.md"
        assert settings.max_items_per_section == 20


class TestLoggingSettings:
    """Tests for LoggingSettings model."""

    def test_default_values(self):
        """Test default values."""
        settings = LoggingSettings()
        assert settings.level is not None

    def test_valid_log_levels(self):
        """Test all valid log levels."""
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            settings = LoggingSettings(level=level)
            assert settings.level == level

    def test_level_case_insensitive(self):
        """Test that level is case insensitive."""
        settings = LoggingSettings(level="info")
        assert settings.level == "INFO"

    def test_invalid_level_raises_error(self):
        """Test that invalid level raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            LoggingSettings(level="INVALID")

        assert "Invalid log level" in str(exc_info.value)


class TestSettings:
    """Tests for main Settings class."""

    def test_default_settings(self):
        """Test default settings creation."""
        with patch.dict("os.environ", {}, clear=True):
            settings = Settings()
            assert settings.database is not None
            assert settings.reddit is not None
            assert settings.youtube is not None

    def test_has_reddit_credentials_false(self):
        """Test has_reddit_credentials returns False when not set."""
        with patch.dict("os.environ", {}, clear=True):
            settings = Settings()
            assert settings.has_reddit_credentials() is False

    def test_has_reddit_credentials_true(self):
        """Test has_reddit_credentials returns True when set."""
        settings = Settings()
        settings.reddit.client_id = "test_id"
        settings.reddit.client_secret = "test_secret"
        assert settings.has_reddit_credentials() is True

    def test_has_reddit_credentials_partial(self):
        """Test has_reddit_credentials returns False with partial credentials."""
        settings = Settings()
        settings.reddit.client_id = "test_id"
        settings.reddit.client_secret = ""
        assert settings.has_reddit_credentials() is False

    def test_has_youtube_credentials_false(self):
        """Test has_youtube_credentials returns False when not set."""
        settings = Settings()
        settings.youtube.api_key = ""
        assert settings.has_youtube_credentials() is False

    def test_has_youtube_credentials_true(self):
        """Test has_youtube_credentials returns True when set."""
        settings = Settings()
        settings.youtube.api_key = "test_key"
        assert settings.has_youtube_credentials() is True

    def test_ensure_directories_creates_dirs(self, tmp_path):
        """Test that ensure_directories creates required directories."""
        db_path = tmp_path / "data" / "test.db"
        reports_path = tmp_path / "reports"
        logs_path = tmp_path / "logs" / "app.log"

        settings = Settings()
        settings.database.path = db_path
        settings.reports.output_directory = reports_path
        settings.logging.file = logs_path

        settings.ensure_directories()

        assert db_path.parent.exists()
        assert reports_path.exists()
        assert logs_path.parent.exists()

    def test_model_post_init_merges_reddit_credentials(self):
        """Test that environment variables are merged into nested settings."""
        with patch.dict(
            "os.environ",
            {
                "REDDIT_CLIENT_ID": "env_client_id",
                "REDDIT_CLIENT_SECRET": "env_client_secret",
            },
        ):
            settings = Settings()
            # The env vars should be merged into reddit settings
            assert settings.reddit.client_id == "env_client_id"
            assert settings.reddit.client_secret == "env_client_secret"

    def test_model_post_init_merges_youtube_credentials(self):
        """Test that YouTube API key environment variable is merged."""
        with patch.dict(
            "os.environ",
            {"YOUTUBE_API_KEY": "env_api_key"},
        ):
            settings = Settings()
            assert settings.youtube.api_key == "env_api_key"

    def test_model_post_init_does_not_override_existing(self):
        """Test that existing nested values are not overridden."""
        # This tests the case where nested settings already have values
        with patch.dict(
            "os.environ",
            {"REDDIT_CLIENT_ID": "env_client_id"},
        ):
            settings = Settings(
                reddit=RedditSettings(client_id="explicit_id"),
            )
            # Explicit value should be preserved
            assert settings.reddit.client_id == "explicit_id"


class TestGetSettings:
    """Tests for get_settings function."""

    def test_returns_settings_instance(self):
        """Test that get_settings returns a Settings instance."""
        # Clear the cache first
        get_settings.cache_clear()

        with patch("signalsift.config.settings.Settings.ensure_directories"):
            settings = get_settings()
            assert isinstance(settings, Settings)

    def test_caches_settings(self):
        """Test that get_settings caches the instance."""
        get_settings.cache_clear()

        with patch("signalsift.config.settings.Settings.ensure_directories"):
            settings1 = get_settings()
            settings2 = get_settings()
            assert settings1 is settings2

    def test_calls_ensure_directories(self):
        """Test that get_settings calls ensure_directories."""
        get_settings.cache_clear()

        with patch("signalsift.config.settings.Settings.ensure_directories") as mock_ensure:
            get_settings()
            mock_ensure.assert_called_once()

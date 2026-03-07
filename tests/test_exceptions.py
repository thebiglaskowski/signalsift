"""Tests for custom exceptions."""

import pytest

from signalsift.exceptions import (
    ConfigurationError,
    DatabaseError,
    HackerNewsError,
    RateLimitError,
    RedditError,
    ReportError,
    RetryExhaustedError,
    SignalSiftError,
    SourceError,
    YouTubeError,
)


class TestSignalSiftError:
    """Tests for base SignalSiftError."""

    def test_base_exception_creation(self):
        """Test creating base exception."""
        error = SignalSiftError("Test error")
        assert str(error) == "Test error"

    def test_base_exception_is_exception(self):
        """Test that SignalSiftError is an Exception."""
        error = SignalSiftError("Test")
        assert isinstance(error, Exception)


class TestConfigurationError:
    """Tests for ConfigurationError."""

    def test_creation(self):
        """Test creating ConfigurationError."""
        error = ConfigurationError("Invalid config")
        assert str(error) == "Invalid config"

    def test_inherits_from_signalsift_error(self):
        """Test inheritance."""
        error = ConfigurationError("Test")
        assert isinstance(error, SignalSiftError)


class TestDatabaseError:
    """Tests for DatabaseError."""

    def test_creation(self):
        """Test creating DatabaseError."""
        error = DatabaseError("Database connection failed")
        assert str(error) == "Database connection failed"

    def test_inherits_from_signalsift_error(self):
        """Test inheritance."""
        error = DatabaseError("Test")
        assert isinstance(error, SignalSiftError)


class TestSourceError:
    """Tests for SourceError."""

    def test_creation(self):
        """Test creating SourceError."""
        error = SourceError("Source unavailable")
        assert str(error) == "Source unavailable"

    def test_inherits_from_signalsift_error(self):
        """Test inheritance."""
        error = SourceError("Test")
        assert isinstance(error, SignalSiftError)


class TestRedditError:
    """Tests for RedditError."""

    def test_creation(self):
        """Test creating RedditError."""
        error = RedditError("Reddit API failed")
        assert str(error) == "Reddit API failed"

    def test_inherits_from_source_error(self):
        """Test inheritance."""
        error = RedditError("Test")
        assert isinstance(error, SourceError)
        assert isinstance(error, SignalSiftError)


class TestYouTubeError:
    """Tests for YouTubeError."""

    def test_creation(self):
        """Test creating YouTubeError."""
        error = YouTubeError("YouTube API quota exceeded")
        assert str(error) == "YouTube API quota exceeded"

    def test_inherits_from_source_error(self):
        """Test inheritance."""
        error = YouTubeError("Test")
        assert isinstance(error, SourceError)


class TestHackerNewsError:
    """Tests for HackerNewsError."""

    def test_creation(self):
        """Test creating HackerNewsError."""
        error = HackerNewsError("HN API timeout")
        assert str(error) == "HN API timeout"

    def test_inherits_from_source_error(self):
        """Test inheritance."""
        error = HackerNewsError("Test")
        assert isinstance(error, SourceError)


class TestReportError:
    """Tests for ReportError."""

    def test_creation(self):
        """Test creating ReportError."""
        error = ReportError("Failed to generate report")
        assert str(error) == "Failed to generate report"

    def test_inherits_from_signalsift_error(self):
        """Test inheritance."""
        error = ReportError("Test")
        assert isinstance(error, SignalSiftError)


class TestRetryExhaustedError:
    """Tests for RetryExhaustedError."""

    def test_creation_without_last_error(self):
        """Test creating RetryExhaustedError without last error."""
        error = RetryExhaustedError(source="reddit", attempts=3)

        assert error.source == "reddit"
        assert error.attempts == 3
        assert error.last_error is None
        assert "All 3 retry attempts failed for reddit" in str(error)

    def test_creation_with_last_error(self):
        """Test creating RetryExhaustedError with last error."""
        original_error = ValueError("Connection timeout")
        error = RetryExhaustedError(source="youtube", attempts=5, last_error=original_error)

        assert error.source == "youtube"
        assert error.attempts == 5
        assert error.last_error is original_error
        assert "All 5 retry attempts failed for youtube" in str(error)
        assert "Connection timeout" in str(error)

    def test_inherits_from_source_error(self):
        """Test inheritance."""
        error = RetryExhaustedError(source="test", attempts=1)
        assert isinstance(error, SourceError)
        assert isinstance(error, SignalSiftError)

    def test_can_be_raised_and_caught(self):
        """Test that error can be raised and caught."""
        with pytest.raises(RetryExhaustedError) as exc_info:
            raise RetryExhaustedError(source="api", attempts=3)

        assert exc_info.value.source == "api"
        assert exc_info.value.attempts == 3


class TestRateLimitError:
    """Tests for RateLimitError."""

    def test_creation_without_retry_after(self):
        """Test creating RateLimitError without retry_after."""
        error = RateLimitError(source="reddit")

        assert error.source == "reddit"
        assert error.retry_after is None
        assert "Rate limited by reddit" in str(error)
        assert "Retry after" not in str(error)

    def test_creation_with_retry_after(self):
        """Test creating RateLimitError with retry_after."""
        error = RateLimitError(source="youtube", retry_after=60)

        assert error.source == "youtube"
        assert error.retry_after == 60
        assert "Rate limited by youtube" in str(error)
        assert "Retry after 60 seconds" in str(error)

    def test_inherits_from_source_error(self):
        """Test inheritance."""
        error = RateLimitError(source="test")
        assert isinstance(error, SourceError)
        assert isinstance(error, SignalSiftError)

    def test_can_be_raised_and_caught(self):
        """Test that error can be raised and caught."""
        with pytest.raises(RateLimitError) as exc_info:
            raise RateLimitError(source="api", retry_after=30)

        assert exc_info.value.source == "api"
        assert exc_info.value.retry_after == 30


class TestExceptionHierarchy:
    """Tests for exception inheritance hierarchy."""

    def test_catch_all_source_errors(self):
        """Test catching all source errors with base class."""
        errors = [
            RedditError("reddit"),
            YouTubeError("youtube"),
            HackerNewsError("hn"),
            RetryExhaustedError(source="test", attempts=1),
            RateLimitError(source="test"),
        ]

        for error in errors:
            assert isinstance(error, SourceError)

    def test_catch_all_signalsift_errors(self):
        """Test catching all errors with base SignalSiftError."""
        errors = [
            ConfigurationError("config"),
            DatabaseError("db"),
            SourceError("source"),
            RedditError("reddit"),
            YouTubeError("youtube"),
            ReportError("report"),
            HackerNewsError("hn"),
        ]

        for error in errors:
            assert isinstance(error, SignalSiftError)

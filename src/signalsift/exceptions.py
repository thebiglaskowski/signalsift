"""Custom exceptions for SignalSift."""


class SignalSiftError(Exception):
    """Base exception for SignalSift."""

    pass


class ConfigurationError(SignalSiftError):
    """Raised when there's a configuration issue."""

    pass


class DatabaseError(SignalSiftError):
    """Raised when there's a database issue."""

    pass


class SourceError(SignalSiftError):
    """Raised when there's an issue with a data source."""

    pass


class RedditError(SourceError):
    """Raised when there's an issue with the Reddit API."""

    pass


class YouTubeError(SourceError):
    """Raised when there's an issue with the YouTube API."""

    pass


class ReportError(SignalSiftError):
    """Raised when there's an issue generating a report."""

    pass


class HackerNewsError(SourceError):
    """Raised when there's an issue with the Hacker News API."""

    pass


class RetryExhaustedError(SourceError):
    """Raised when all retry attempts have failed."""

    def __init__(self, source: str, attempts: int, last_error: Exception | None = None) -> None:
        self.source = source
        self.attempts = attempts
        self.last_error = last_error
        message = f"All {attempts} retry attempts failed for {source}"
        if last_error:
            message += f": {last_error}"
        super().__init__(message)


class RateLimitError(SourceError):
    """Raised when rate limited by an API."""

    def __init__(self, source: str, retry_after: int | None = None) -> None:
        self.source = source
        self.retry_after = retry_after
        message = f"Rate limited by {source}"
        if retry_after:
            message += f". Retry after {retry_after} seconds"
        super().__init__(message)

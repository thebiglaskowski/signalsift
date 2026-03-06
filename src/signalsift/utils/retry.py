"""Retry utilities with exponential backoff for SignalSift."""

from __future__ import annotations

import contextlib
import functools
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, ParamSpec, TypeVar

import requests

from signalsift.utils.logging import get_logger

logger = get_logger(__name__)

P = ParamSpec("P")
T = TypeVar("T")

# Default retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 1.0  # seconds
DEFAULT_MAX_DELAY = 60.0  # seconds
DEFAULT_EXPONENTIAL_BASE = 2.0

# HTTP status codes that should trigger retry
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = DEFAULT_MAX_RETRIES
    base_delay: float = DEFAULT_BASE_DELAY
    max_delay: float = DEFAULT_MAX_DELAY
    exponential_base: float = DEFAULT_EXPONENTIAL_BASE
    jitter: bool = True
    retryable_exceptions: tuple[type[Exception], ...] = field(
        default_factory=lambda: (requests.RequestException,)
    )
    retryable_status_codes: frozenset[int] = RETRYABLE_STATUS_CODES

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.base_delay <= 0:
            raise ValueError("base_delay must be positive")
        if self.max_delay < self.base_delay:
            raise ValueError("max_delay must be >= base_delay")


def calculate_backoff_delay(
    attempt: int,
    config: RetryConfig,
) -> float:
    """
    Calculate delay with exponential backoff and optional jitter.

    Args:
        attempt: Current attempt number (0-indexed).
        config: Retry configuration.

    Returns:
        Delay in seconds before next attempt.
    """
    delay = config.base_delay * (config.exponential_base**attempt)
    delay = min(delay, config.max_delay)

    if config.jitter:
        # Add random jitter (0-25% of delay)
        jitter_amount = delay * 0.25 * random.random()
        delay += jitter_amount

    return delay


def with_retry(
    config: RetryConfig | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator for retrying functions with exponential backoff.

    Usage:
        @with_retry(RetryConfig(max_retries=5))
        def fetch_data():
            response = requests.get(url)
            response.raise_for_status()
            return response.json()

    Args:
        config: Retry configuration. Uses defaults if None.

    Returns:
        Decorated function with retry logic.
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception: Exception | None = None

            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e

                    # Check if it's a response with non-retryable status
                    if (
                        isinstance(e, requests.HTTPError)
                        and e.response is not None
                        and e.response.status_code not in config.retryable_status_codes
                    ):
                        raise

                    if attempt < config.max_retries:
                        delay = calculate_backoff_delay(attempt, config)
                        logger.warning(
                            f"Attempt {attempt + 1}/{config.max_retries + 1} failed: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {config.max_retries + 1} attempts failed for {func.__name__}"
                        )
                        raise

            # This should never be reached, but satisfies type checker
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected retry loop exit")

        return wrapper

    return decorator


def retry_request(
    method: str,
    url: str,
    session: requests.Session | None = None,
    config: RetryConfig | None = None,
    **kwargs: Any,
) -> requests.Response:
    """
    Make an HTTP request with retry logic.

    Args:
        method: HTTP method (GET, POST, etc.).
        url: Request URL.
        session: Optional requests session.
        config: Retry configuration.
        **kwargs: Additional arguments passed to requests.

    Returns:
        Response object.

    Raises:
        requests.RequestException: If all retries fail.
    """
    if config is None:
        config = RetryConfig()

    if session is None:
        session = requests.Session()

    last_exception: Exception | None = None

    for attempt in range(config.max_retries + 1):
        try:
            response = session.request(method, url, **kwargs)

            # Check if status code should trigger retry
            if response.status_code in config.retryable_status_codes:
                if attempt < config.max_retries:
                    delay = calculate_backoff_delay(attempt, config)

                    # Check for Retry-After header
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        with contextlib.suppress(ValueError):
                            delay = max(delay, float(retry_after))

                    logger.warning(
                        f"Request to {url} returned {response.status_code}. "
                        f"Retrying in {delay:.1f}s (attempt {attempt + 1}/{config.max_retries + 1})..."
                    )
                    time.sleep(delay)
                    continue
                else:
                    # All retries exhausted, raise for status
                    response.raise_for_status()

            return response

        except config.retryable_exceptions as e:
            last_exception = e

            if attempt < config.max_retries:
                delay = calculate_backoff_delay(attempt, config)
                logger.warning(
                    f"Request to {url} failed: {e}. "
                    f"Retrying in {delay:.1f}s (attempt {attempt + 1}/{config.max_retries + 1})..."
                )
                time.sleep(delay)
            else:
                logger.error(f"All {config.max_retries + 1} attempts failed for {url}")
                raise

    # Should never reach here
    if last_exception:
        raise last_exception
    raise RuntimeError("Unexpected retry loop exit")


# Convenience configurations for different scenarios
AGGRESSIVE_RETRY = RetryConfig(
    max_retries=5,
    base_delay=0.5,
    max_delay=30.0,
)

CONSERVATIVE_RETRY = RetryConfig(
    max_retries=2,
    base_delay=2.0,
    max_delay=10.0,
)

API_RETRY = RetryConfig(
    max_retries=3,
    base_delay=1.0,
    max_delay=60.0,
    retryable_status_codes=frozenset({429, 500, 502, 503, 504, 520, 521, 522, 523, 524}),
)

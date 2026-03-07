"""Tests for retry utilities."""

import time
from unittest.mock import MagicMock

import pytest
import requests

from signalsift.utils.retry import (
    RetryConfig,
    calculate_backoff_delay,
    retry_request,
    with_retry,
)


class TestRetryConfig:
    """Tests for RetryConfig."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.jitter is True

    def test_custom_values(self) -> None:
        """Test custom configuration."""
        config = RetryConfig(
            max_retries=5,
            base_delay=2.0,
            max_delay=30.0,
            jitter=False,
        )
        assert config.max_retries == 5
        assert config.base_delay == 2.0

    def test_invalid_max_retries(self) -> None:
        """Test validation of max_retries."""
        with pytest.raises(ValueError, match="max_retries must be non-negative"):
            RetryConfig(max_retries=-1)

    def test_invalid_base_delay(self) -> None:
        """Test validation of base_delay."""
        with pytest.raises(ValueError, match="base_delay must be positive"):
            RetryConfig(base_delay=0)

    def test_invalid_max_delay(self) -> None:
        """Test validation of max_delay."""
        with pytest.raises(ValueError, match="max_delay must be >= base_delay"):
            RetryConfig(base_delay=10.0, max_delay=5.0)


class TestBackoffCalculation:
    """Tests for backoff delay calculation."""

    def test_exponential_backoff(self) -> None:
        """Test exponential backoff without jitter."""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)

        assert calculate_backoff_delay(0, config) == 1.0
        assert calculate_backoff_delay(1, config) == 2.0
        assert calculate_backoff_delay(2, config) == 4.0
        assert calculate_backoff_delay(3, config) == 8.0

    def test_max_delay_cap(self) -> None:
        """Test that delay is capped at max_delay."""
        config = RetryConfig(base_delay=1.0, max_delay=5.0, jitter=False)

        # 2^10 = 1024, but should be capped at 5
        assert calculate_backoff_delay(10, config) == 5.0

    def test_jitter_adds_variance(self) -> None:
        """Test that jitter adds randomness."""
        config = RetryConfig(base_delay=1.0, jitter=True)

        # Run multiple times and check for variance
        delays = [calculate_backoff_delay(0, config) for _ in range(100)]

        # All should be >= base_delay
        assert all(d >= 1.0 for d in delays)

        # Should have some variance (not all identical)
        assert len(set(delays)) > 1


class TestWithRetryDecorator:
    """Tests for the with_retry decorator."""

    def test_success_on_first_attempt(self) -> None:
        """Test function that succeeds immediately."""
        call_count = 0

        @with_retry(RetryConfig(max_retries=3))
        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_func()
        assert result == "success"
        assert call_count == 1

    def test_success_after_retry(self) -> None:
        """Test function that succeeds after retries."""
        call_count = 0

        @with_retry(RetryConfig(max_retries=3, base_delay=0.01, jitter=False))
        def eventually_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise requests.RequestException("Temporary failure")
            return "success"

        result = eventually_succeeds()
        assert result == "success"
        assert call_count == 3

    def test_all_retries_exhausted(self) -> None:
        """Test function that always fails."""

        @with_retry(RetryConfig(max_retries=2, base_delay=0.01, jitter=False))
        def always_fails():
            raise requests.RequestException("Permanent failure")

        with pytest.raises(requests.RequestException):
            always_fails()

    def test_non_retryable_exception(self) -> None:
        """Test that non-retryable exceptions are raised immediately."""
        call_count = 0

        @with_retry(RetryConfig(max_retries=3))
        def raises_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not retryable")

        with pytest.raises(ValueError):
            raises_value_error()

        # Should only be called once
        assert call_count == 1


class TestRetryRequest:
    """Tests for retry_request function."""

    def test_successful_request(self) -> None:
        """Test successful request on first attempt."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_session.request.return_value = mock_response

        response = retry_request(
            "GET",
            "https://example.com/api",
            session=mock_session,
            config=RetryConfig(max_retries=3),
        )

        assert response.status_code == 200
        assert mock_session.request.call_count == 1

    def test_retry_on_429(self) -> None:
        """Test retry on rate limit (429)."""
        mock_session = MagicMock()

        # First call returns 429, second returns 200
        mock_429 = MagicMock()
        mock_429.status_code = 429
        mock_429.headers = {}

        mock_200 = MagicMock()
        mock_200.status_code = 200

        mock_session.request.side_effect = [mock_429, mock_200]

        response = retry_request(
            "GET",
            "https://example.com/api",
            session=mock_session,
            config=RetryConfig(max_retries=3, base_delay=0.01, jitter=False),
        )

        assert response.status_code == 200
        assert mock_session.request.call_count == 2

    def test_retry_on_connection_error(self) -> None:
        """Test retry on connection error."""
        mock_session = MagicMock()

        # First call raises error, second succeeds
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_session.request.side_effect = [
            requests.ConnectionError("Connection failed"),
            mock_response,
        ]

        response = retry_request(
            "GET",
            "https://example.com/api",
            session=mock_session,
            config=RetryConfig(max_retries=3, base_delay=0.01, jitter=False),
        )

        assert response.status_code == 200
        assert mock_session.request.call_count == 2

    def test_respects_retry_after_header(self) -> None:
        """Test that Retry-After header is respected."""
        mock_session = MagicMock()

        mock_429 = MagicMock()
        mock_429.status_code = 429
        mock_429.headers = {"Retry-After": "0.05"}  # 50ms

        mock_200 = MagicMock()
        mock_200.status_code = 200

        mock_session.request.side_effect = [mock_429, mock_200]

        start_time = time.time()
        response = retry_request(
            "GET",
            "https://example.com/api",
            session=mock_session,
            config=RetryConfig(max_retries=3, base_delay=0.01, jitter=False),
        )
        elapsed = time.time() - start_time

        assert response.status_code == 200
        # Should have waited at least the Retry-After time
        assert elapsed >= 0.04  # Allow some tolerance

    def test_no_retry_on_400(self) -> None:
        """Test that 400 errors are not retried."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 400

        mock_session.request.return_value = mock_response

        response = retry_request(
            "GET",
            "https://example.com/api",
            session=mock_session,
            config=RetryConfig(max_retries=3),
        )

        # Should return immediately without retry
        assert response.status_code == 400
        assert mock_session.request.call_count == 1

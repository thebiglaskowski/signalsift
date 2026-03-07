"""Tests for formatting utilities."""

from datetime import datetime

from signalsift.utils.formatting import (
    format_date,
    format_duration,
    format_file_size,
    format_number,
    format_relative_time,
    format_timestamp,
    truncate_text,
)


class TestFormatNumber:
    """Tests for format_number function."""

    def test_format_number_small(self):
        """Test formatting small numbers."""
        assert format_number(0) == "0"
        assert format_number(100) == "100"
        assert format_number(999) == "999"

    def test_format_number_thousands(self):
        """Test formatting thousands."""
        assert format_number(1000) == "1.0K"
        assert format_number(1500) == "1.5K"
        assert format_number(10000) == "10.0K"
        assert format_number(999999) == "1000.0K"

    def test_format_number_millions(self):
        """Test formatting millions."""
        assert format_number(1000000) == "1.0M"
        assert format_number(1500000) == "1.5M"
        assert format_number(10000000) == "10.0M"

    def test_format_number_float(self):
        """Test formatting float values."""
        assert format_number(1234.5) == "1.2K"
        assert format_number(1000000.5) == "1.0M"


class TestFormatTimestamp:
    """Tests for format_timestamp function."""

    def test_format_timestamp_basic(self):
        """Test basic timestamp formatting."""
        # January 1, 2024 12:00:00
        timestamp = datetime(2024, 1, 1, 12, 0, 0).timestamp()
        result = format_timestamp(timestamp)
        assert "2024-01-01" in result
        assert "12:00:00" in result

    def test_format_timestamp_integer(self):
        """Test with integer timestamp."""
        result = format_timestamp(0)  # Unix epoch
        assert "1970" in result or "1969" in result  # Depends on timezone


class TestFormatDate:
    """Tests for format_date function."""

    def test_format_date_basic(self):
        """Test basic date formatting."""
        timestamp = datetime(2024, 6, 15).timestamp()
        result = format_date(timestamp)
        assert result == "2024-06-15"

    def test_format_date_different_dates(self):
        """Test various dates."""
        assert format_date(datetime(2023, 1, 1).timestamp()) == "2023-01-01"
        assert format_date(datetime(2024, 12, 31).timestamp()) == "2024-12-31"


class TestFormatDuration:
    """Tests for format_duration function."""

    def test_format_duration_seconds_only(self):
        """Test formatting seconds only."""
        assert format_duration(45) == "0:45"

    def test_format_duration_minutes_seconds(self):
        """Test formatting minutes and seconds."""
        assert format_duration(90) == "1:30"
        assert format_duration(150) == "2:30"
        assert format_duration(600) == "10:00"

    def test_format_duration_hours(self):
        """Test formatting with hours."""
        assert format_duration(3600) == "1:00:00"
        assert format_duration(3665) == "1:01:05"
        assert format_duration(7200) == "2:00:00"

    def test_format_duration_zero(self):
        """Test zero duration."""
        assert format_duration(0) == "0:00"

    def test_format_duration_none(self):
        """Test None duration."""
        assert format_duration(None) == "N/A"

    def test_format_duration_negative(self):
        """Test negative duration."""
        assert format_duration(-1) == "N/A"


class TestTruncateText:
    """Tests for truncate_text function."""

    def test_truncate_text_short(self):
        """Test that short text is not truncated."""
        text = "Short"
        assert truncate_text(text, max_length=50) == text

    def test_truncate_text_exact_length(self):
        """Test text at exact max length."""
        text = "Exactly"
        assert truncate_text(text, max_length=7) == text

    def test_truncate_text_long(self):
        """Test truncating long text."""
        text = "This is a very long text that needs truncation"
        result = truncate_text(text, max_length=20)
        assert len(result) == 20
        assert result.endswith("...")

    def test_truncate_text_custom_suffix(self):
        """Test custom suffix."""
        text = "Long text here for testing"
        result = truncate_text(text, max_length=15, suffix="…")
        assert result.endswith("…")
        assert len(result) == 15

    def test_truncate_text_empty(self):
        """Test empty text."""
        assert truncate_text("") == ""
        assert truncate_text(None) == ""


class TestFormatFileSize:
    """Tests for format_file_size function."""

    def test_format_file_size_bytes(self):
        """Test formatting bytes."""
        assert format_file_size(0) == "0.0 B"
        assert format_file_size(100) == "100.0 B"
        assert format_file_size(1023) == "1023.0 B"

    def test_format_file_size_kilobytes(self):
        """Test formatting kilobytes."""
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(1536) == "1.5 KB"
        assert format_file_size(10240) == "10.0 KB"

    def test_format_file_size_megabytes(self):
        """Test formatting megabytes."""
        assert format_file_size(1024 * 1024) == "1.0 MB"
        assert format_file_size(1024 * 1024 * 2.5) == "2.5 MB"

    def test_format_file_size_gigabytes(self):
        """Test formatting gigabytes."""
        assert format_file_size(1024**3) == "1.0 GB"

    def test_format_file_size_terabytes(self):
        """Test formatting terabytes."""
        assert format_file_size(1024**4) == "1.0 TB"


class TestFormatRelativeTime:
    """Tests for format_relative_time function."""

    def test_format_relative_time_just_now(self):
        """Test 'just now' formatting."""
        now = datetime.now().timestamp()
        assert format_relative_time(now) == "just now"
        assert format_relative_time(now - 30) == "just now"

    def test_format_relative_time_minutes(self):
        """Test minutes formatting."""
        now = datetime.now().timestamp()
        assert format_relative_time(now - 60) == "1 minute ago"
        assert format_relative_time(now - 120) == "2 minutes ago"
        assert format_relative_time(now - 300) == "5 minutes ago"

    def test_format_relative_time_hours(self):
        """Test hours formatting."""
        now = datetime.now().timestamp()
        assert format_relative_time(now - 3600) == "1 hour ago"
        assert format_relative_time(now - 7200) == "2 hours ago"

    def test_format_relative_time_days(self):
        """Test days formatting."""
        now = datetime.now().timestamp()
        assert format_relative_time(now - 86400) == "1 day ago"
        assert format_relative_time(now - 172800) == "2 days ago"

    def test_format_relative_time_weeks(self):
        """Test weeks formatting."""
        now = datetime.now().timestamp()
        assert format_relative_time(now - 604800) == "1 week ago"
        assert format_relative_time(now - 1209600) == "2 weeks ago"

    def test_format_relative_time_old(self):
        """Test old dates return formatted date."""
        old_timestamp = datetime(2020, 1, 1).timestamp()
        result = format_relative_time(old_timestamp)
        assert "2020-01-01" in result

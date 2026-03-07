"""Output formatting utilities for SignalSift."""

from datetime import datetime


def format_number(value: int | float) -> str:
    """
    Format large numbers with K/M suffixes.

    Args:
        value: The number to format.

    Returns:
        Formatted string (e.g., "1.5K", "2.3M").
    """
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return str(int(value))


def format_timestamp(timestamp: int | float) -> str:
    """
    Format a Unix timestamp as a human-readable date.

    Args:
        timestamp: Unix timestamp.

    Returns:
        Formatted date string.
    """
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_date(timestamp: int | float) -> str:
    """
    Format a Unix timestamp as a date only.

    Args:
        timestamp: Unix timestamp.

    Returns:
        Formatted date string (YYYY-MM-DD).
    """
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y-%m-%d")


def format_duration(seconds: int) -> str:
    """
    Format a duration in seconds as HH:MM:SS or MM:SS.

    Args:
        seconds: Duration in seconds.

    Returns:
        Formatted duration string.
    """
    if seconds is None or seconds < 0:
        return "N/A"

    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)

    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def truncate_text(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length.

    Args:
        text: Text to truncate.
        max_length: Maximum length.
        suffix: Suffix to add if truncated.

    Returns:
        Truncated text.
    """
    if not text:
        return ""

    if len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)] + suffix


def format_file_size(size_bytes: int) -> str:
    """
    Format a file size in bytes as a human-readable string.

    Args:
        size_bytes: Size in bytes.

    Returns:
        Formatted size string (e.g., "2.5 MB").
    """
    size: float = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def format_relative_time(timestamp: int | float) -> str:
    """
    Format a timestamp as relative time (e.g., "2 days ago").

    Args:
        timestamp: Unix timestamp.

    Returns:
        Relative time string.
    """
    now = datetime.now()
    dt = datetime.fromtimestamp(timestamp)
    diff = now - dt

    seconds = diff.total_seconds()

    if seconds < 60:
        return "just now"
    if seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    if seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    if seconds < 604800:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
    if seconds < 2592000:
        weeks = int(seconds / 604800)
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"

    return format_date(timestamp)

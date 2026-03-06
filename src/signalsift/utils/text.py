"""Text processing utilities for SignalSift."""

import hashlib
import re
import unicodedata


def clean_text(text: str) -> str:
    """
    Clean text by removing extra whitespace and normalizing characters.

    Args:
        text: The text to clean.

    Returns:
        Cleaned text.
    """
    if not text:
        return ""

    # Normalize Unicode characters
    text = unicodedata.normalize("NFKC", text)

    # Replace multiple whitespace with single space
    text = re.sub(r"\s+", " ", text)

    # Remove zero-width characters
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)

    return text.strip()


def extract_excerpt(text: str, max_length: int = 300) -> str:
    """
    Extract an excerpt from text, trying to break at sentence boundaries.

    Args:
        text: The source text.
        max_length: Maximum length of excerpt.

    Returns:
        Extracted excerpt with ellipsis if truncated.
    """
    if not text:
        return ""

    text = clean_text(text)

    if len(text) <= max_length:
        return text

    truncated = text[:max_length]

    for punct in [". ", "! ", "? "]:
        last_pos = truncated.rfind(punct)
        if last_pos > max_length * 0.5:
            return truncated[: last_pos + 1]

    last_space = truncated.rfind(" ")
    if last_space > max_length * 0.7:
        return truncated[:last_space] + "..."

    return truncated + "..."


def hash_content(content: str) -> str:
    """
    Generate a SHA256 hash of content.

    Args:
        content: The content to hash.

    Returns:
        Hex-encoded SHA256 hash.
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def strip_markdown(text: str) -> str:
    """
    Remove basic markdown formatting from text.

    Args:
        text: Text potentially containing markdown.

    Returns:
        Plain text without markdown formatting.
    """
    if not text:
        return ""

    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`[^`]+`", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", "", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"_([^_]+)_", r"\1", text)
    text = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)

    return clean_text(text)


def contains_metrics(text: str) -> bool:
    """
    Check if text contains numeric metrics or statistics.

    Args:
        text: Text to check.

    Returns:
        True if metrics are found.
    """
    patterns = [
        r"\d+%",
        r"\$[\d,]+",
        r"\d+k\b",
        r"\d+\s*(views|visitors|users|clicks|sessions|traffic)",
        r"(increased|grew|boosted|improved)\s+by\s+\d+",
        r"\d+\s*x\b",
        r"\d{1,3}(,\d{3})+",
    ]

    text_lower = text.lower()
    return any(re.search(pattern, text_lower, re.IGNORECASE) for pattern in patterns)


def normalize_keyword(keyword: str) -> str:
    """
    Normalize a keyword for matching.

    Args:
        keyword: The keyword to normalize.

    Returns:
        Normalized keyword.
    """
    keyword = keyword.lower()
    keyword = re.sub(r"\s+", " ", keyword).strip()
    return keyword

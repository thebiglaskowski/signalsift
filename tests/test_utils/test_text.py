"""Tests for text processing utilities."""

from signalsift.utils.text import (
    clean_text,
    contains_metrics,
    extract_excerpt,
    hash_content,
    normalize_keyword,
    strip_markdown,
)


class TestCleanText:
    """Tests for clean_text function."""

    def test_clean_text_empty(self):
        """Test cleaning empty text."""
        assert clean_text("") == ""
        assert clean_text(None) == ""

    def test_clean_text_whitespace(self):
        """Test normalizing whitespace."""
        assert clean_text("hello   world") == "hello world"
        assert clean_text("hello\n\nworld") == "hello world"
        assert clean_text("hello\t\tworld") == "hello world"

    def test_clean_text_strips(self):
        """Test stripping leading/trailing whitespace."""
        assert clean_text("  hello  ") == "hello"
        assert clean_text("\n\nhello\n\n") == "hello"

    def test_clean_text_zero_width(self):
        """Test removing zero-width characters."""
        assert clean_text("hello\u200bworld") == "helloworld"
        assert clean_text("hello\u200cworld") == "helloworld"
        assert clean_text("hello\u200dworld") == "helloworld"
        assert clean_text("hello\ufeffworld") == "helloworld"

    def test_clean_text_unicode_normalization(self):
        """Test Unicode normalization."""
        # NFKC normalization converts full-width chars
        text_with_fullwidth = "ＨｅｌｌｏWorld"
        result = clean_text(text_with_fullwidth)
        assert "Hello" in result


class TestExtractExcerpt:
    """Tests for extract_excerpt function."""

    def test_extract_excerpt_empty(self):
        """Test extracting from empty text."""
        assert extract_excerpt("") == ""
        assert extract_excerpt(None) == ""

    def test_extract_excerpt_short_text(self):
        """Test that short text is returned as-is."""
        text = "Short text here."
        assert extract_excerpt(text, max_length=100) == text

    def test_extract_excerpt_truncates_at_sentence(self):
        """Test truncation at sentence boundary."""
        text = "First sentence here. Second sentence here. Third sentence."
        result = extract_excerpt(text, max_length=40)
        assert result.endswith(".")
        assert len(result) <= 40

    def test_extract_excerpt_truncates_at_space(self):
        """Test truncation at word boundary when no sentence end."""
        text = "This is a very long sentence that keeps going and going without any punctuation"
        result = extract_excerpt(text, max_length=50)
        assert result.endswith("...")
        assert len(result) <= 53  # max_length + "..."

    def test_extract_excerpt_preserves_exclamation(self):
        """Test truncation at exclamation point."""
        text = "Wow! This is amazing! Look at this feature!"
        result = extract_excerpt(text, max_length=30)
        assert "!" in result

    def test_extract_excerpt_preserves_question(self):
        """Test truncation at question mark."""
        text = "Did you know? This is interesting? Very much so?"
        result = extract_excerpt(text, max_length=30)
        assert "?" in result


class TestHashContent:
    """Tests for hash_content function."""

    def test_hash_content_basic(self):
        """Test basic content hashing."""
        result = hash_content("hello world")
        assert isinstance(result, str)
        assert len(result) == 64  # SHA256 hex

    def test_hash_content_deterministic(self):
        """Test that same content produces same hash."""
        hash1 = hash_content("test content")
        hash2 = hash_content("test content")
        assert hash1 == hash2

    def test_hash_content_different(self):
        """Test that different content produces different hashes."""
        hash1 = hash_content("content a")
        hash2 = hash_content("content b")
        assert hash1 != hash2

    def test_hash_content_unicode(self):
        """Test hashing Unicode content."""
        result = hash_content("你好世界")
        assert isinstance(result, str)
        assert len(result) == 64


class TestStripMarkdown:
    """Tests for strip_markdown function."""

    def test_strip_markdown_empty(self):
        """Test stripping empty text."""
        assert strip_markdown("") == ""
        assert strip_markdown(None) == ""

    def test_strip_markdown_code_blocks(self):
        """Test removing code blocks."""
        text = "Before ```python\ncode here\n``` After"
        result = strip_markdown(text)
        assert "```" not in result
        assert "code here" not in result
        assert "Before" in result
        assert "After" in result

    def test_strip_markdown_inline_code(self):
        """Test removing inline code."""
        text = "Use `inline code` here"
        result = strip_markdown(text)
        assert "`" not in result
        assert "inline code" not in result

    def test_strip_markdown_links(self):
        """Test converting links to text."""
        text = "Check [this link](https://example.com) out"
        result = strip_markdown(text)
        assert "this link" in result
        assert "https://example.com" not in result
        assert "[" not in result
        assert "]" not in result

    def test_strip_markdown_images(self):
        """Test removing images."""
        text = "See ![alt text](image.png) here"
        result = strip_markdown(text)
        assert "![" not in result
        assert "image.png" not in result

    def test_strip_markdown_bold(self):
        """Test removing bold formatting."""
        text = "This is **bold** text"
        result = strip_markdown(text)
        assert "**" not in result
        assert "bold" in result

    def test_strip_markdown_italic(self):
        """Test removing italic formatting."""
        text = "This is *italic* text"
        result = strip_markdown(text)
        assert "*" not in result
        assert "italic" in result

    def test_strip_markdown_underscore_bold(self):
        """Test removing underscore bold."""
        text = "This is __bold__ text"
        result = strip_markdown(text)
        assert "__" not in result
        assert "bold" in result

    def test_strip_markdown_underscore_italic(self):
        """Test removing underscore italic."""
        text = "This is _italic_ text"
        result = strip_markdown(text)
        assert "_" not in result
        assert "italic" in result

    def test_strip_markdown_headers(self):
        """Test removing header markers."""
        text = "# Header 1\n## Header 2\n### Header 3"
        result = strip_markdown(text)
        assert "#" not in result
        assert "Header 1" in result

    def test_strip_markdown_blockquotes(self):
        """Test removing blockquote markers."""
        text = "> This is a quote\n> And more"
        result = strip_markdown(text)
        assert ">" not in result
        assert "This is a quote" in result

    def test_strip_markdown_horizontal_rules(self):
        """Test removing horizontal rules."""
        text = "Before\n---\nAfter\n***\nEnd"
        result = strip_markdown(text)
        assert "---" not in result
        assert "***" not in result


class TestContainsMetrics:
    """Tests for contains_metrics function."""

    def test_contains_metrics_percentage(self):
        """Test detecting percentages."""
        assert contains_metrics("Traffic increased by 25%")
        assert contains_metrics("50% improvement")

    def test_contains_metrics_dollar_amounts(self):
        """Test detecting dollar amounts."""
        assert contains_metrics("Made $5,000 this month")
        assert contains_metrics("Revenue of $100")
        assert contains_metrics("Earned $10,000")

    def test_contains_metrics_thousands(self):
        """Test detecting K notation."""
        assert contains_metrics("Got 10k visitors")
        assert contains_metrics("50K views")

    def test_contains_metrics_traffic(self):
        """Test detecting traffic metrics."""
        assert contains_metrics("Got 1000 visitors today")
        assert contains_metrics("500 views on the article")
        assert contains_metrics("10 clicks so far")
        assert contains_metrics("25 users signed up")

    def test_contains_metrics_growth(self):
        """Test detecting growth language."""
        assert contains_metrics("Traffic increased by 50")
        assert contains_metrics("Revenue grew by 100")
        assert contains_metrics("Improved by 20 points")

    def test_contains_metrics_multiplier(self):
        """Test detecting multipliers."""
        assert contains_metrics("Results improved 3x")
        assert contains_metrics("10X growth")

    def test_contains_metrics_large_numbers(self):
        """Test detecting large comma-separated numbers."""
        assert contains_metrics("Got 1,000,000 impressions")
        assert contains_metrics("100,000 monthly visitors")

    def test_contains_metrics_no_metrics(self):
        """Test text without metrics."""
        assert not contains_metrics("This is just regular text")
        assert not contains_metrics("No numbers here")
        assert not contains_metrics("")


class TestNormalizeKeyword:
    """Tests for normalize_keyword function."""

    def test_normalize_keyword_lowercase(self):
        """Test lowercasing keywords."""
        assert normalize_keyword("SEO") == "seo"
        assert normalize_keyword("Content Marketing") == "content marketing"

    def test_normalize_keyword_whitespace(self):
        """Test normalizing whitespace in keywords."""
        assert normalize_keyword("  seo  ") == "seo"
        assert normalize_keyword("content   marketing") == "content marketing"
        assert normalize_keyword("link\t\tbuilding") == "link building"

    def test_normalize_keyword_mixed(self):
        """Test mixed normalization."""
        assert normalize_keyword("  SEO   Tools  ") == "seo tools"

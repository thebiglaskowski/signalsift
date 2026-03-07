"""Tests for quote extraction module."""

import pytest

from signalsift.processing.quotes import (
    Quote,
    QuoteExtractor,
    extract_quotes,
    get_best_quote,
    get_extractor,
)
from signalsift.processing.sentiment import SentimentCategory


class TestQuoteDataclass:
    """Tests for Quote dataclass."""

    def test_quote_creation(self):
        """Test creating a Quote instance."""
        quote = Quote(
            text="This is a great insight about SEO.",
            score=0.75,
            has_metrics=False,
            sentiment=SentimentCategory.POSITIVE,
            quote_type="insight",
            source_position=100,
        )

        assert quote.text == "This is a great insight about SEO."
        assert quote.score == 0.75
        assert quote.has_metrics is False
        assert quote.sentiment == SentimentCategory.POSITIVE
        assert quote.quote_type == "insight"
        assert quote.source_position == 100

    def test_quote_with_metrics(self):
        """Test Quote with metrics flag."""
        quote = Quote(
            text="Traffic increased by 50% after implementing this.",
            score=0.9,
            has_metrics=True,
            sentiment=SentimentCategory.POSITIVE,
            quote_type="metric",
            source_position=0,
        )

        assert quote.has_metrics is True
        assert quote.quote_type == "metric"


class TestQuoteExtractorInit:
    """Tests for QuoteExtractor initialization."""

    def test_default_initialization(self):
        """Test default initialization values."""
        extractor = QuoteExtractor()

        assert extractor.min_length == 40
        assert extractor.max_length == 300
        assert extractor.min_score == 0.3

    def test_custom_initialization(self):
        """Test custom initialization values."""
        extractor = QuoteExtractor(
            min_length=50,
            max_length=200,
            min_score=0.5,
        )

        assert extractor.min_length == 50
        assert extractor.max_length == 200
        assert extractor.min_score == 0.5


class TestQuoteExtractorSplitSentences:
    """Tests for sentence splitting."""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance."""
        return QuoteExtractor()

    def test_split_basic_sentences(self, extractor):
        """Test splitting basic sentences."""
        text = "First sentence. Second sentence. Third sentence."
        sentences = extractor._split_sentences(text)

        assert len(sentences) == 3
        assert sentences[0] == "First sentence."
        assert sentences[1] == "Second sentence."
        assert sentences[2] == "Third sentence."

    def test_split_with_exclamation(self, extractor):
        """Test splitting with exclamation marks."""
        text = "Wow! That's amazing! Really good."
        sentences = extractor._split_sentences(text)

        assert len(sentences) == 3

    def test_split_with_question(self, extractor):
        """Test splitting with question marks."""
        text = "Is this working? Yes it is. Great?"
        sentences = extractor._split_sentences(text)

        assert len(sentences) == 3

    def test_split_preserves_abbreviations(self, extractor):
        """Test that abbreviations are preserved."""
        text = "Dr. Smith said this works. Mr. Jones agreed."
        sentences = extractor._split_sentences(text)

        # Should be 2 sentences, not split on Dr. or Mr.
        assert len(sentences) == 2


class TestQuoteExtractorIsWeakSentence:
    """Tests for weak sentence detection."""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance."""
        return QuoteExtractor()

    def test_weak_start_um(self, extractor):
        """Test detection of 'um' starter."""
        assert extractor._is_weak_sentence("Um, I think this is good") is True

    def test_weak_start_like(self, extractor):
        """Test detection of 'like' starter."""
        assert extractor._is_weak_sentence("Like, this is a thing") is True

    def test_weak_start_so(self, extractor):
        """Test detection of 'so' starter."""
        assert extractor._is_weak_sentence("So, I was thinking about this") is True

    def test_weak_start_well(self, extractor):
        """Test detection of 'well' starter."""
        assert extractor._is_weak_sentence("Well, it depends on the situation") is True

    def test_question_is_weak(self, extractor):
        """Test that questions are considered weak."""
        assert extractor._is_weak_sentence("Is this a good idea or not?") is True

    def test_short_word_count_weak(self, extractor):
        """Test that very short sentences are weak."""
        assert extractor._is_weak_sentence("Good point.") is True
        assert extractor._is_weak_sentence("Nice work there.") is True

    def test_excessive_punctuation_weak(self, extractor):
        """Test that excessive punctuation is weak."""
        assert extractor._is_weak_sentence("What!!!??? This is crazy!!!") is True

    def test_strong_sentence_not_weak(self, extractor):
        """Test that strong sentences are not weak."""
        assert (
            extractor._is_weak_sentence(
                "The key strategy that worked was focusing on long-tail keywords."
            )
            is False
        )


class TestQuoteExtractorScoreSentence:
    """Tests for sentence scoring."""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance."""
        return QuoteExtractor()

    def test_score_with_metrics(self, extractor):
        """Test scoring sentences with metrics."""
        score, quote_type, has_metrics = extractor._score_sentence(
            "Traffic increased by 50% after the update."
        )

        assert has_metrics is True
        assert quote_type == "metric"
        assert score > 0.3

    def test_score_with_dollar_amount(self, extractor):
        """Test scoring sentences with dollar amounts."""
        score, quote_type, has_metrics = extractor._score_sentence(
            "Made $5,000 from affiliate revenue last month."
        )

        assert has_metrics is True
        assert score > 0.3

    def test_score_insight_pattern(self, extractor):
        """Test scoring sentences with insight patterns."""
        score, quote_type, has_metrics = extractor._score_sentence(
            "The key is to focus on user intent first and keywords second."
        )

        assert score > 0.2
        assert quote_type in ["insight", "metric"]

    def test_score_advice_pattern(self, extractor):
        """Test scoring sentences with advice patterns."""
        score, quote_type, has_metrics = extractor._score_sentence(
            "You should always check your competitors before writing content."
        )

        assert score > 0.2

    def test_score_success_pattern(self, extractor):
        """Test scoring sentences with success patterns."""
        score, quote_type, has_metrics = extractor._score_sentence(
            "Finally reached first page rankings after months of work."
        )

        assert score > 0.1

    def test_score_pain_pattern(self, extractor):
        """Test scoring sentences with pain patterns."""
        score, quote_type, has_metrics = extractor._score_sentence(
            "Frustrated with Google's algorithm changes destroying my traffic."
        )

        assert score > 0.1

    def test_score_capped_at_one(self, extractor):
        """Test that score is capped at 1.0."""
        # Create a sentence with many high-scoring patterns
        score, _, _ = extractor._score_sentence(
            "The key is that traffic increased by 50% and grew 3x with SEO keywords."
        )

        assert score <= 1.0


class TestQuoteExtractorExtract:
    """Tests for main extract method."""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance."""
        return QuoteExtractor(min_score=0.1)

    def test_extract_basic(self, extractor):
        """Test basic extraction."""
        text = """
        This is a short intro. The key insight here is that focusing on user intent
        leads to better rankings and more traffic. Traffic increased by 50% after
        implementing this strategy. Just do it.
        """

        quotes = extractor.extract(text, max_quotes=3)

        assert len(quotes) > 0
        assert all(isinstance(q, Quote) for q in quotes)
        assert all(q.score >= extractor.min_score for q in quotes)

    def test_extract_sorted_by_score(self, extractor):
        """Test that quotes are sorted by score descending."""
        text = """
        Regular sentence here without much value.
        Traffic grew by 200% after the update which was amazing.
        The key strategy was targeting long-tail keywords consistently.
        """

        quotes = extractor.extract(text, max_quotes=5)

        if len(quotes) >= 2:
            for i in range(len(quotes) - 1):
                assert quotes[i].score >= quotes[i + 1].score

    def test_extract_respects_max_quotes(self, extractor):
        """Test that max_quotes is respected."""
        text = """
        First good insight about SEO strategies and keyword research.
        Traffic increased by 25% after implementing these changes.
        The key is to focus on quality content over quantity always.
        Revenue grew by $5,000 from affiliate marketing last month.
        Pro tip: always check your competitors before writing content.
        """

        quotes = extractor.extract(text, max_quotes=2)

        assert len(quotes) <= 2

    def test_extract_filters_by_type(self, extractor):
        """Test filtering by quote type."""
        text = """
        Traffic increased by 50% which was a great metric.
        The key insight is that user intent matters most.
        I was frustrated with the constant algorithm changes.
        """

        metric_quotes = extractor.extract(text, max_quotes=5, quote_types=["metric"])

        for quote in metric_quotes:
            assert quote.quote_type == "metric"

    def test_extract_empty_text(self, extractor):
        """Test extraction from empty text."""
        quotes = extractor.extract("", max_quotes=5)
        assert quotes == []

    def test_extract_no_good_quotes(self, extractor):
        """Test when no quotes meet criteria."""
        text = "Short. Also short. Nope. No."
        quotes = extractor.extract(text, max_quotes=5)
        assert quotes == []


class TestQuoteExtractorSpecializedMethods:
    """Tests for specialized extraction methods."""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance."""
        return QuoteExtractor(min_score=0.1)

    def test_extract_metrics_quotes(self, extractor):
        """Test extracting only metrics quotes."""
        text = """
        Traffic increased by 50% after the changes were implemented.
        The key insight is that quality content matters most.
        Revenue grew to $10,000 monthly from affiliate programs.
        """

        quotes = extractor.extract_metrics_quotes(text)

        for quote in quotes:
            assert quote.quote_type == "metric"

    def test_extract_insights(self, extractor):
        """Test extracting insight quotes."""
        text = """
        The key is to focus on user intent over pure keyword optimization.
        My advice would be to always check competitors first.
        Traffic numbers are looking good this quarter overall.
        """

        quotes = extractor.extract_insights(text)

        for quote in quotes:
            assert quote.quote_type in ["insight", "advice"]

    def test_extract_pain_quotes(self, extractor):
        """Test extracting pain point quotes."""
        text = """
        I'm frustrated with Google's constant algorithm updates.
        Struggling to rank for any keywords in this competitive niche.
        The strategy is working great for our team overall.
        """

        quotes = extractor.extract_pain_quotes(text)

        for quote in quotes:
            assert quote.quote_type == "pain"

    def test_extract_success_quotes(self, extractor):
        """Test extracting success story quotes."""
        text = """
        Finally hit first page rankings after six months of work.
        The breakthrough came when we switched our strategy completely.
        Nothing special happening here in this regular text.
        """

        quotes = extractor.extract_success_quotes(text)

        for quote in quotes:
            assert quote.quote_type == "success"


class TestGetBestQuote:
    """Tests for get_best_quote method."""

    def test_get_best_quote_returns_top(self):
        """Test that get_best_quote returns the highest scoring quote."""
        extractor = QuoteExtractor(min_score=0.1)

        text = """
        Regular text here without much value or insight.
        Traffic increased by 200% after implementing SEO best practices.
        Another regular sentence without special patterns.
        """

        best = extractor.get_best_quote(text)

        if best:
            all_quotes = extractor.extract(text, max_quotes=10)
            assert best.score == max(q.score for q in all_quotes)

    def test_get_best_quote_empty_text(self):
        """Test get_best_quote with empty text."""
        extractor = QuoteExtractor()
        result = extractor.get_best_quote("")
        assert result is None

    def test_get_best_quote_no_good_quotes(self):
        """Test get_best_quote when no good quotes exist."""
        extractor = QuoteExtractor(min_score=0.9)  # Very high threshold
        result = extractor.get_best_quote("Short. Bad. Text.")
        assert result is None


class TestModuleFunctions:
    """Tests for module-level functions."""

    def test_get_extractor_returns_instance(self):
        """Test that get_extractor returns QuoteExtractor."""
        import signalsift.processing.quotes as quotes_module

        # Reset the module-level instance
        quotes_module._default_extractor = None

        extractor = get_extractor()
        assert isinstance(extractor, QuoteExtractor)

    def test_get_extractor_caches_instance(self):
        """Test that get_extractor caches the instance."""
        import signalsift.processing.quotes as quotes_module

        # Reset the module-level instance
        quotes_module._default_extractor = None

        extractor1 = get_extractor()
        extractor2 = get_extractor()

        assert extractor1 is extractor2

    def test_extract_quotes_function(self):
        """Test the extract_quotes convenience function."""
        text = """
        The key insight is that focusing on user intent leads to better results.
        Traffic increased by 50% after implementing this SEO strategy.
        """

        quotes = extract_quotes(text, max_quotes=2)

        assert isinstance(quotes, list)
        assert all(isinstance(q, Quote) for q in quotes)

    def test_get_best_quote_function(self):
        """Test the get_best_quote convenience function."""
        text = "Traffic grew by 100% which was an amazing metric to see."

        quote = get_best_quote(text)

        # May or may not return a quote depending on scoring
        assert quote is None or isinstance(quote, Quote)

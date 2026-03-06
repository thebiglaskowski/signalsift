"""Quote extraction for SignalSift.

This module extracts insightful, quotable sentences from content
for use in reports and summaries.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from signalsift.processing.sentiment import SentimentCategory, analyze_sentiment
from signalsift.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Quote:
    """An extracted quote from content."""

    text: str
    score: float  # Quality/relevance score 0-1
    has_metrics: bool
    sentiment: SentimentCategory
    quote_type: str  # "insight", "metric", "pain", "success", "advice"
    source_position: int  # Position in original text


# Patterns that indicate quotable content
METRIC_PATTERNS = [
    r"\d+%",  # Percentages
    r"\$[\d,]+(?:\.\d{2})?(?:k|K)?",  # Dollar amounts
    r"\d+(?:k|K|m|M)\b",  # Thousands/millions
    r"\d+\s*(?:x|X)\b",  # Multipliers (3x, 10x)
    r"\d+\s*(?:visitors|views|clicks|sessions|users)",  # Traffic metrics
    r"(?:increased|grew|improved|dropped|lost)\s+(?:by\s+)?\d+",  # Change metrics
    r"(?:first|1st|top\s+\d|#1)",  # Ranking achievements
]

INSIGHT_PATTERNS = [
    r"\b(?:the\s+(?:key|secret|trick|strategy)\s+(?:is|was))",
    r"\b(?:what\s+(?:worked|helped|made\s+the\s+difference))",
    r"\b(?:I\s+(?:learned|discovered|realized|found\s+out))",
    r"\b(?:the\s+(?:biggest|main|most\s+important)\s+(?:factor|thing|lesson))",
    r"\b(?:pro\s*tip|tip:|advice:)",
    r"\b(?:here'?s?\s+(?:what|how|why))",
]

ADVICE_PATTERNS = [
    r"\b(?:you\s+should|I\s+(?:recommend|suggest)|make\s+sure\s+(?:to|you))",
    r"\b(?:don'?t\s+(?:forget|skip|ignore|underestimate))",
    r"\b(?:always|never)\s+\w+",
    r"\b(?:the\s+best\s+(?:way|approach|method|strategy))",
    r"\b(?:start\s+(?:by|with)|focus\s+on)",
]

SUCCESS_PATTERNS = [
    r"\b(?:finally|breakthrough|game\s*changer)",
    r"\b(?:hit|reached|achieved)\s+(?:\$?\d|first|#1|top)",
    r"\b(?:doubled|tripled|10x|5x)",
    r"\b(?:success(?:fully)?|working|profitable)",
]

PAIN_PATTERNS = [
    r"\b(?:frustrated|struggling|stuck|confused)",
    r"\b(?:doesn'?t\s+work|broken|useless)",
    r"\b(?:waste\s+of|regret|mistake)",
    r"\b(?:dropped|lost|crashed|tanked)",
]

# Sentence quality indicators
WEAK_STARTS = [
    "um",
    "uh",
    "like",
    "so",
    "well",
    "yeah",
    "ok",
    "okay",
    "anyway",
    "basically",
    "literally",
    "honestly",
]

STRONG_STARTERS = [
    "the key",
    "what worked",
    "i learned",
    "pro tip",
    "my advice",
    "the best",
    "here's what",
    "after",
]


class QuoteExtractor:
    """Extract quotable sentences from content."""

    def __init__(
        self,
        min_length: int = 40,
        max_length: int = 300,
        min_score: float = 0.3,
    ) -> None:
        """
        Initialize the quote extractor.

        Args:
            min_length: Minimum character length for quotes.
            max_length: Maximum character length for quotes.
            min_score: Minimum score to include a quote.
        """
        self.min_length = min_length
        self.max_length = max_length
        self.min_score = min_score

    def extract(
        self,
        text: str,
        max_quotes: int = 5,
        quote_types: list[str] | None = None,
    ) -> list[Quote]:
        """
        Extract top quotes from text.

        Args:
            text: The text to extract quotes from.
            max_quotes: Maximum number of quotes to return.
            quote_types: Filter by quote types (insight, metric, pain, success, advice).

        Returns:
            List of Quote objects sorted by score.
        """
        sentences = self._split_sentences(text)
        quotes: list[Quote] = []

        for _, sentence in enumerate(sentences):
            # Skip if too short or too long
            if len(sentence) < self.min_length or len(sentence) > self.max_length:
                continue

            # Skip weak sentences
            if self._is_weak_sentence(sentence):
                continue

            # Score and classify the sentence
            score, quote_type, has_metrics = self._score_sentence(sentence)

            if score < self.min_score:
                continue

            # Apply type filter
            if quote_types and quote_type not in quote_types:
                continue

            # Get sentiment
            sentiment_result = analyze_sentiment(sentence)

            quotes.append(
                Quote(
                    text=sentence.strip(),
                    score=score,
                    has_metrics=has_metrics,
                    sentiment=sentiment_result.category,
                    quote_type=quote_type,
                    source_position=text.find(sentence),
                )
            )

        # Sort by score and return top N
        quotes.sort(key=lambda q: q.score, reverse=True)
        return quotes[:max_quotes]

    def extract_metrics_quotes(self, text: str, max_quotes: int = 3) -> list[Quote]:
        """Extract quotes that contain specific metrics/numbers."""
        return self.extract(text, max_quotes=max_quotes, quote_types=["metric"])

    def extract_insights(self, text: str, max_quotes: int = 3) -> list[Quote]:
        """Extract insightful/advice quotes."""
        return self.extract(
            text,
            max_quotes=max_quotes,
            quote_types=["insight", "advice"],
        )

    def extract_pain_quotes(self, text: str, max_quotes: int = 3) -> list[Quote]:
        """Extract pain point quotes."""
        return self.extract(text, max_quotes=max_quotes, quote_types=["pain"])

    def extract_success_quotes(self, text: str, max_quotes: int = 3) -> list[Quote]:
        """Extract success story quotes."""
        return self.extract(text, max_quotes=max_quotes, quote_types=["success"])

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        # Handle common abbreviations
        text = re.sub(r"(\b(?:Mr|Mrs|Ms|Dr|vs|etc|e\.g|i\.e))\.", r"\1<PERIOD>", text)

        # Split on sentence boundaries
        sentences = re.split(r"(?<=[.!?])\s+", text)

        # Restore abbreviation periods
        sentences = [s.replace("<PERIOD>", ".") for s in sentences]

        # Clean up
        sentences = [s.strip() for s in sentences if s.strip()]

        return sentences

    def _is_weak_sentence(self, sentence: str) -> bool:
        """Check if sentence starts with weak words or is low quality."""
        sentence_lower = sentence.lower().strip()

        # Check for weak starts
        for weak in WEAK_STARTS:
            if sentence_lower.startswith(weak + " ") or sentence_lower.startswith(weak + ","):
                return True

        # Check for questions (usually not quotable)
        if sentence.strip().endswith("?") and not any(
            re.search(p, sentence_lower) for p in INSIGHT_PATTERNS
        ):
            return True

        # Check for very short word count
        word_count = len(sentence.split())
        if word_count < 5:
            return True

        # Check for excessive punctuation (often indicates low quality)
        punctuation_ratio = sum(1 for c in sentence if c in "!?...") / len(sentence)
        return punctuation_ratio > 0.1

    def _score_sentence(self, sentence: str) -> tuple[float, str, bool]:
        """
        Score a sentence for quotability.

        Returns:
            Tuple of (score, quote_type, has_metrics).
        """
        sentence_lower = sentence.lower()
        score = 0.0
        quote_type = "insight"
        has_metrics = False

        # Check for metrics (highest value)
        metrics_found = sum(1 for p in METRIC_PATTERNS if re.search(p, sentence_lower))
        if metrics_found > 0:
            score += 0.3 + (0.1 * min(metrics_found, 3))
            has_metrics = True
            quote_type = "metric"

        # Check for insight patterns
        insights_found = sum(1 for p in INSIGHT_PATTERNS if re.search(p, sentence_lower))
        if insights_found > 0:
            score += 0.25 + (0.05 * min(insights_found, 2))
            if quote_type != "metric":
                quote_type = "insight"

        # Check for advice patterns
        advice_found = sum(1 for p in ADVICE_PATTERNS if re.search(p, sentence_lower))
        if advice_found > 0:
            score += 0.2 + (0.05 * min(advice_found, 2))
            if quote_type not in ["metric", "insight"]:
                quote_type = "advice"

        # Check for success patterns
        success_found = sum(1 for p in SUCCESS_PATTERNS if re.search(p, sentence_lower))
        if success_found > 0:
            score += 0.2
            if quote_type not in ["metric", "insight", "advice"]:
                quote_type = "success"

        # Check for pain patterns
        pain_found = sum(1 for p in PAIN_PATTERNS if re.search(p, sentence_lower))
        if pain_found > 0:
            score += 0.15
            if quote_type not in ["metric", "insight", "advice", "success"]:
                quote_type = "pain"

        # Bonus for strong starters
        for starter in STRONG_STARTERS:
            if sentence_lower.startswith(starter):
                score += 0.1
                break

        # Length bonus (prefer medium-length sentences)
        optimal_length = 150
        length_diff = abs(len(sentence) - optimal_length)
        length_score = max(0, 1 - (length_diff / optimal_length)) * 0.1
        score += length_score

        # Specificity bonus (contains specific terms)
        specific_terms = [
            "seo",
            "traffic",
            "rankings",
            "keywords",
            "backlinks",
            "content",
            "affiliate",
            "revenue",
            "google",
            "algorithm",
        ]
        specificity = sum(1 for t in specific_terms if t in sentence_lower)
        score += min(specificity * 0.03, 0.15)

        return min(score, 1.0), quote_type, has_metrics

    def get_best_quote(self, text: str) -> Quote | None:
        """Get the single best quote from text."""
        quotes = self.extract(text, max_quotes=1)
        return quotes[0] if quotes else None


# Module-level instance
_default_extractor: QuoteExtractor | None = None


def get_extractor() -> QuoteExtractor:
    """Get the default quote extractor instance."""
    global _default_extractor
    if _default_extractor is None:
        _default_extractor = QuoteExtractor()
    return _default_extractor


def extract_quotes(text: str, max_quotes: int = 5) -> list[Quote]:
    """Convenience function to extract quotes from text."""
    return get_extractor().extract(text, max_quotes=max_quotes)


def get_best_quote(text: str) -> Quote | None:
    """Get the single best quote from text."""
    return get_extractor().get_best_quote(text)

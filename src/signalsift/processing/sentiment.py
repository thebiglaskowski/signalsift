"""Sentiment analysis for SignalSift.

This module provides sentiment analysis for content, including
pain point severity detection and urgency classification.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from signalsift.utils.logging import get_logger

logger = get_logger(__name__)


class UrgencyLevel(Enum):
    """Urgency level for pain points."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SentimentCategory(Enum):
    """Sentiment category."""

    VERY_NEGATIVE = "very_negative"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    POSITIVE = "positive"
    VERY_POSITIVE = "very_positive"


@dataclass
class SentimentResult:
    """Result of sentiment analysis."""

    polarity: float  # -1.0 to 1.0
    subjectivity: float  # 0.0 to 1.0
    category: SentimentCategory
    urgency: UrgencyLevel
    pain_severity: int  # 1-5 scale
    confidence: float  # 0.0 to 1.0

    @property
    def is_pain_point(self) -> bool:
        """Check if this indicates a pain point."""
        return self.polarity < -0.1 or self.pain_severity >= 3

    @property
    def is_success_story(self) -> bool:
        """Check if this indicates a success story."""
        return self.polarity > 0.2 and self.subjectivity > 0.3


# Urgency indicators
URGENCY_CRITICAL_PATTERNS = [
    r"\b(emergency|urgent|asap|immediately|critical|crisis|desperate)\b",
    r"\b(can'?t\s+figure\s+out|completely\s+lost|total\s+mess)\b",
    r"\b(business\s+is\s+(dying|dead)|losing\s+everything)\b",
    r"\b(help\s*!+|please\s+help|someone\s+help)\b",
]

URGENCY_HIGH_PATTERNS = [
    r"\b(frustrated|struggling|stuck|blocked|confused)\b",
    r"\b(need\s+help|looking\s+for\s+help|any\s+advice)\b",
    r"\b(dropped|tanked|crashed|plummeted)\b",
    r"\b(lost\s+\d+%|down\s+\d+%)\b",
    r"\b(deadline|time\s+sensitive|running\s+out)\b",
]

URGENCY_MEDIUM_PATTERNS = [
    r"\b(wondering|curious|thinking\s+about)\b",
    r"\b(trying\s+to|want\s+to|planning\s+to)\b",
    r"\b(issue|problem|challenge)\b",
    r"\b(slow|inconsistent|unreliable)\b",
]

# Pain severity indicators (higher = more severe)
PAIN_SEVERITY_5_PATTERNS = [
    r"\b(deindexed|penalized|blacklisted|banned)\b",
    r"\b(site\s+is\s+dead|zero\s+traffic|completely\s+tanked)\b",
    r"\b(lost\s+everything|business\s+failed|shutting\s+down)\b",
    r"\b(scammed|ripped\s+off|fraud)\b",
]

PAIN_SEVERITY_4_PATTERNS = [
    r"\b(traffic\s+dropped|rankings\s+dropped|lost\s+rankings)\b",
    r"\b(massive\s+(drop|decline|loss))\b",
    r"\b(doesn'?t\s+work|broken|unusable)\b",
    r"\b(waste\s+of\s+(money|time)|regret)\b",
]

PAIN_SEVERITY_3_PATTERNS = [
    r"\b(frustrated|annoyed|disappointed)\b",
    r"\b(not\s+working|struggling|difficult)\b",
    r"\b(slow|buggy|unreliable)\b",
    r"\b(overpriced|expensive|not\s+worth)\b",
]

PAIN_SEVERITY_2_PATTERNS = [
    r"\b(confusing|unclear|complicated)\b",
    r"\b(minor\s+(issue|problem)|small\s+bug)\b",
    r"\b(could\s+be\s+better|room\s+for\s+improvement)\b",
    r"\b(wish\s+it\s+had|missing\s+feature)\b",
]

# Success indicators for polarity boost
SUCCESS_PATTERNS = [
    (r"\b(increased|grew|improved|boosted)\s+by\s+\d+", 0.3),
    (r"\b(hit|reached|achieved)\s+(first\s+page|#1|top\s+\d)", 0.4),
    (r"\b(case\s+study|success\s+story|what\s+worked)\b", 0.2),
    (r"\b\d+k?\+?\s*(visitors|views|clicks|sessions)\s*(/|per)\s*(month|day)\b", 0.2),
    (r"\b(doubled|tripled|10x|5x)\s+(traffic|revenue|income)\b", 0.4),
    (r"\b(finally|breakthrough|game\s*changer)\b", 0.2),
    (r"\b(love|amazing|incredible|fantastic|excellent)\b", 0.15),
]


class SentimentAnalyzer:
    """Analyze sentiment and urgency of content."""

    def __init__(self) -> None:
        """Initialize the sentiment analyzer."""
        self._textblob_available = False
        self._load_textblob()

    def _load_textblob(self) -> None:
        """Load TextBlob for sentiment analysis."""
        try:
            from textblob import TextBlob

            self._TextBlob = TextBlob
            self._textblob_available = True
            logger.debug("TextBlob loaded for sentiment analysis")
        except ImportError:
            logger.warning(
                "TextBlob not installed - using pattern-based sentiment. "
                "Install with: pip install textblob"
            )
            self._textblob_available = False

    @property
    def is_available(self) -> bool:
        """Check if full sentiment analysis is available."""
        return self._textblob_available

    def analyze(self, text: str) -> SentimentResult:
        """
        Analyze sentiment of text.

        Args:
            text: The text to analyze.

        Returns:
            SentimentResult with polarity, subjectivity, and classifications.
        """
        text_lower = text.lower()

        # Get base sentiment from TextBlob if available
        if self._textblob_available:
            blob = self._TextBlob(text)
            polarity = blob.sentiment.polarity
            subjectivity = blob.sentiment.subjectivity
            confidence = 0.7  # Base confidence for TextBlob
        else:
            # Fallback to pattern-based
            polarity, subjectivity = self._pattern_based_sentiment(text_lower)
            confidence = 0.4  # Lower confidence for pattern-based

        # Adjust polarity based on success patterns
        for pattern, boost in SUCCESS_PATTERNS:
            if re.search(pattern, text_lower):
                polarity = min(1.0, polarity + boost)
                confidence = min(1.0, confidence + 0.1)

        # Detect urgency
        urgency = self._detect_urgency(text_lower)

        # Detect pain severity
        pain_severity = self._detect_pain_severity(text_lower)

        # Adjust polarity for high pain severity
        if pain_severity >= 4:
            polarity = min(polarity, -0.3)
        elif pain_severity >= 3:
            polarity = min(polarity, 0.0)

        # Categorize sentiment
        category = self._categorize_sentiment(polarity)

        return SentimentResult(
            polarity=round(polarity, 3),
            subjectivity=round(subjectivity, 3),
            category=category,
            urgency=urgency,
            pain_severity=pain_severity,
            confidence=round(confidence, 3),
        )

    def _pattern_based_sentiment(self, text: str) -> tuple[float, float]:
        """Calculate sentiment using pattern matching (fallback)."""
        positive_words = [
            "good",
            "great",
            "excellent",
            "amazing",
            "love",
            "best",
            "helpful",
            "useful",
            "recommend",
            "success",
            "improved",
            "increased",
            "working",
            "easy",
            "simple",
            "effective",
        ]
        negative_words = [
            "bad",
            "terrible",
            "worst",
            "hate",
            "awful",
            "useless",
            "broken",
            "frustrated",
            "struggling",
            "failed",
            "dropped",
            "lost",
            "difficult",
            "expensive",
            "slow",
            "buggy",
        ]

        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        total = positive_count + negative_count

        if total == 0:
            return 0.0, 0.3

        polarity = (positive_count - negative_count) / max(total, 1)
        polarity = max(-1.0, min(1.0, polarity))

        # Subjectivity based on emotional word density
        word_count = len(text.split())
        subjectivity = min(1.0, total / max(word_count, 1) * 10)

        return polarity, subjectivity

    def _detect_urgency(self, text: str) -> UrgencyLevel:
        """Detect urgency level from text."""
        for pattern in URGENCY_CRITICAL_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return UrgencyLevel.CRITICAL

        for pattern in URGENCY_HIGH_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return UrgencyLevel.HIGH

        for pattern in URGENCY_MEDIUM_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return UrgencyLevel.MEDIUM

        return UrgencyLevel.LOW

    def _detect_pain_severity(self, text: str) -> int:
        """Detect pain point severity (1-5 scale)."""
        for pattern in PAIN_SEVERITY_5_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return 5

        for pattern in PAIN_SEVERITY_4_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return 4

        for pattern in PAIN_SEVERITY_3_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return 3

        for pattern in PAIN_SEVERITY_2_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return 2

        return 1

    def _categorize_sentiment(self, polarity: float) -> SentimentCategory:
        """Categorize sentiment based on polarity."""
        if polarity <= -0.5:
            return SentimentCategory.VERY_NEGATIVE
        elif polarity <= -0.1:
            return SentimentCategory.NEGATIVE
        elif polarity < 0.1:
            return SentimentCategory.NEUTRAL
        elif polarity < 0.5:
            return SentimentCategory.POSITIVE
        else:
            return SentimentCategory.VERY_POSITIVE

    def analyze_for_pain_point(self, text: str) -> dict:
        """
        Analyze text specifically for pain point detection.

        Returns a dict with pain point indicators.
        """
        result = self.analyze(text)
        text_lower = text.lower()

        # Additional pain point signals
        signals = {
            "has_question_marks": "?" in text,
            "asking_for_help": bool(
                re.search(r"\b(help|advice|tips|suggestions|recommend)\b", text_lower)
            ),
            "expressing_frustration": bool(
                re.search(r"\b(frustrated|annoyed|confused|stuck)\b", text_lower)
            ),
            "reporting_problem": bool(
                re.search(r"\b(issue|problem|bug|error|broken)\b", text_lower)
            ),
            "traffic_loss": bool(
                re.search(r"\b(dropped|lost|decreased|declined)\s+(traffic|rankings)", text_lower)
            ),
        }

        return {
            "is_pain_point": result.is_pain_point,
            "severity": result.pain_severity,
            "urgency": result.urgency.value,
            "polarity": result.polarity,
            "signals": signals,
            "signal_count": sum(signals.values()),
        }


# Module-level instance
_default_analyzer: SentimentAnalyzer | None = None


def get_analyzer() -> SentimentAnalyzer:
    """Get the default sentiment analyzer instance."""
    global _default_analyzer
    if _default_analyzer is None:
        _default_analyzer = SentimentAnalyzer()
    return _default_analyzer


def analyze_sentiment(text: str) -> SentimentResult:
    """Convenience function to analyze sentiment."""
    return get_analyzer().analyze(text)


def get_pain_severity(text: str) -> int:
    """Get pain point severity (1-5) for text."""
    return get_analyzer().analyze(text).pain_severity


def get_urgency(text: str) -> UrgencyLevel:
    """Get urgency level for text."""
    return get_analyzer().analyze(text).urgency

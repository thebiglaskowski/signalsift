"""Keyword matching utilities for SignalSift.

This module provides keyword matching with semantic expansion support.
When spaCy is installed with word vectors, it automatically expands
keywords to include semantically similar terms for better coverage.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from signalsift.database.models import Keyword
from signalsift.database.queries import get_all_keywords
from signalsift.utils.logging import get_logger

if TYPE_CHECKING:
    from signalsift.processing.semantic import SemanticExpander

logger = get_logger(__name__)


@dataclass
class KeywordMatch:
    """Represents a keyword match in content."""

    keyword: str
    category: str
    weight: float
    count: int  # Number of times this keyword appears
    is_semantic: bool = False  # True if matched via semantic expansion
    original_keyword: str | None = None  # Parent keyword if semantic match


class KeywordMatcher:
    """
    Keyword matching with semantic expansion support.

    Uses exact matching by default, with optional semantic expansion
    via spaCy word vectors when available. Semantic matching finds
    terms that are conceptually similar to the base keywords.

    Example:
        "affiliate" might also match "referral", "partner program", etc.
    """

    def __init__(
        self,
        enable_semantic: bool = True,
        cache_dir: Path | None = None,
    ) -> None:
        """
        Initialize the keyword matcher.

        Args:
            enable_semantic: Whether to enable semantic expansion.
            cache_dir: Directory for caching semantic expansions.
        """
        self._keywords: list[Keyword] | None = None
        self._patterns: dict[str, re.Pattern[str]] = {}
        self._semantic_patterns: dict[str, tuple[re.Pattern[str], str, float]] = {}
        self._enable_semantic = enable_semantic
        self._cache_dir = cache_dir
        self._semantic_available = False
        self._expander: SemanticExpander | None = None

        # Initialize semantic expansion
        if enable_semantic:
            self._init_semantic()

    def _init_semantic(self) -> None:
        """Initialize semantic expansion if available."""
        try:
            from signalsift.processing.semantic import (
                SemanticExpander,
            )

            self._expander = SemanticExpander(cache_dir=self._cache_dir)
            self._semantic_available = self._expander.is_available

            if self._semantic_available:
                logger.info(
                    "Semantic keyword expansion enabled " "(spaCy model loaded successfully)"
                )
            else:
                logger.info(
                    "Semantic expansion unavailable - using exact matching only. "
                    "To enable semantic matching, run: "
                    "python -m spacy download en_core_web_md"
                )

        except ImportError as e:
            logger.debug(f"Semantic module import failed: {e}")
            self._semantic_available = False

    @property
    def semantic_enabled(self) -> bool:
        """Check if semantic expansion is active."""
        return self._enable_semantic and self._semantic_available

    @property
    def keywords(self) -> list[Keyword]:
        """Get cached keywords, loading from DB if needed."""
        if self._keywords is None:
            self._keywords = get_all_keywords(enabled_only=True)
            self._build_patterns()
        return self._keywords

    def _build_patterns(self) -> None:
        """Build regex patterns for exact and semantic matching."""
        # Clear existing patterns
        self._patterns.clear()
        self._semantic_patterns.clear()

        # Build exact match patterns
        if self._keywords is None:
            return
        for kw in self._keywords:
            pattern = re.compile(
                r"\b" + re.escape(kw.keyword.lower()) + r"\b",
                re.IGNORECASE,
            )
            self._patterns[kw.keyword] = pattern

        # Build semantic expansion patterns if available
        if self.semantic_enabled and self._expander:
            logger.info("Building semantic expansion patterns...")
            expansion_count = 0

            for kw in self._keywords:
                expansions = self._expander.expand_keyword(
                    keyword=kw.keyword,
                    category=kw.category,
                    base_weight=kw.weight,
                )

                for exp in expansions:
                    # Create pattern for expanded term
                    pattern = re.compile(
                        r"\b" + re.escape(exp.expanded_term.lower()) + r"\b",
                        re.IGNORECASE,
                    )

                    # Store with reference to original keyword
                    pattern_key = f"{kw.keyword}:{exp.expanded_term}"
                    self._semantic_patterns[pattern_key] = (
                        pattern,
                        kw.keyword,  # original keyword
                        exp.weight,  # derived weight
                    )
                    expansion_count += 1

            if expansion_count > 0:
                logger.info(
                    f"Generated {expansion_count} semantic expansions "
                    f"for {len(self._keywords)} keywords"
                )

    def refresh(self) -> None:
        """Refresh the keyword cache from the database."""
        self._keywords = None
        self._patterns.clear()
        self._semantic_patterns.clear()

    def find_matches(self, text: str) -> list[KeywordMatch]:
        """
        Find all keyword matches in the given text.

        Performs exact matching first, then semantic matching
        if enabled. Semantic matches are flagged accordingly.

        Args:
            text: The text to search in.

        Returns:
            List of KeywordMatch objects for all matches found.
        """
        text_lower = text.lower()
        matches: list[KeywordMatch] = []
        matched_terms: set[str] = set()  # Track to avoid duplicates

        # === Exact matching ===
        for keyword in self.keywords:
            pattern = self._patterns.get(keyword.keyword)
            if pattern:
                found = pattern.findall(text_lower)
                if found:
                    matches.append(
                        KeywordMatch(
                            keyword=keyword.keyword,
                            category=keyword.category,
                            weight=keyword.weight,
                            count=len(found),
                            is_semantic=False,
                            original_keyword=None,
                        )
                    )
                    matched_terms.add(keyword.keyword.lower())

        # === Semantic matching ===
        if self.semantic_enabled:
            for pattern_key, (pattern, original_kw, weight) in self._semantic_patterns.items():
                # Extract expanded term from key
                expanded_term = pattern_key.split(":", 1)[1]

                # Skip if already matched exactly
                if expanded_term.lower() in matched_terms:
                    continue

                found = pattern.findall(text_lower)
                if found:
                    # Find the original keyword to get category
                    original_keyword = next(
                        (k for k in self.keywords if k.keyword == original_kw),
                        None,
                    )

                    if original_keyword:
                        matches.append(
                            KeywordMatch(
                                keyword=expanded_term,
                                category=original_keyword.category,
                                weight=weight,
                                count=len(found),
                                is_semantic=True,
                                original_keyword=original_kw,
                            )
                        )
                        matched_terms.add(expanded_term.lower())

        return matches

    def calculate_keyword_score(self, matches: list[KeywordMatch]) -> float:
        """
        Calculate a score based on keyword matches.

        Semantic matches contribute to the score but with their
        reduced weight (80% of parent by default).

        Args:
            matches: List of KeywordMatch objects.

        Returns:
            Weighted score based on matches (capped at 35 points).
        """
        score = 0.0
        for match in matches:
            # Weight * 5 points per occurrence, capped per keyword
            keyword_contribution = min(match.count, 3) * match.weight * 5
            score += keyword_contribution

        # Cap total keyword score at 35
        return min(score, 35.0)

    def get_matched_keywords(self, matches: list[KeywordMatch]) -> list[str]:
        """Get list of matched keyword strings."""
        return [m.keyword for m in matches]

    def get_matches_by_category(self, matches: list[KeywordMatch]) -> dict[str, list[KeywordMatch]]:
        """Group matches by category."""
        by_category: dict[str, list[KeywordMatch]] = {}
        for match in matches:
            if match.category not in by_category:
                by_category[match.category] = []
            by_category[match.category].append(match)
        return by_category

    def get_semantic_matches(self, matches: list[KeywordMatch]) -> list[KeywordMatch]:
        """Filter to only semantic matches."""
        return [m for m in matches if m.is_semantic]

    def get_exact_matches(self, matches: list[KeywordMatch]) -> list[KeywordMatch]:
        """Filter to only exact matches."""
        return [m for m in matches if not m.is_semantic]

    def get_match_stats(self, matches: list[KeywordMatch]) -> dict[str, int]:
        """Get statistics about matches."""
        exact = len([m for m in matches if not m.is_semantic])
        semantic = len([m for m in matches if m.is_semantic])
        return {
            "total": len(matches),
            "exact": exact,
            "semantic": semantic,
            "categories": len({m.category for m in matches}),
        }


# Module-level matcher instance for convenience
_default_matcher: KeywordMatcher | None = None


def get_matcher(
    enable_semantic: bool = True,
    cache_dir: Path | None = None,
) -> KeywordMatcher:
    """
    Get the default keyword matcher instance.

    Args:
        enable_semantic: Whether to enable semantic expansion.
        cache_dir: Directory for caching expansions.

    Returns:
        KeywordMatcher instance.
    """
    global _default_matcher
    if _default_matcher is None:
        _default_matcher = KeywordMatcher(
            enable_semantic=enable_semantic,
            cache_dir=cache_dir,
        )
    return _default_matcher


def find_matching_keywords(text: str) -> list[KeywordMatch]:
    """
    Convenience function to find keyword matches.

    Uses the default matcher with semantic expansion enabled.

    Args:
        text: The text to search in.

    Returns:
        List of KeywordMatch objects.
    """
    return get_matcher().find_matches(text)


def is_semantic_matching_enabled() -> bool:
    """Check if semantic matching is currently active."""
    return get_matcher().semantic_enabled

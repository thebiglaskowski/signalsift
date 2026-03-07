"""Semantic keyword expansion using spaCy word vectors.

This module provides semantic similarity matching to expand the base keyword set
with semantically related terms, improving content matching coverage.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from signalsift.utils.logging import get_logger

if TYPE_CHECKING:
    import spacy
    from spacy.language import Language

    from signalsift.processing.vector_index import VocabVectorIndex

logger = get_logger(__name__)

# Default spaCy model - medium model includes word vectors
DEFAULT_MODEL = "en_core_web_md"

# Similarity thresholds by category type
# Some categories need stricter matching (tool names) vs looser (concepts)
CATEGORY_SIMILARITY_THRESHOLDS: dict[str, float] = {
    # Strict - proper nouns, tool names (should match closely)
    "tool_mentions": 0.85,
    # Standard - general concepts
    "success_signals": 0.75,
    "pain_points": 0.75,
    "techniques": 0.75,
    "keyword_research": 0.75,
    "monetization": 0.75,
    "ai_visibility": 0.75,
    "content_generation": 0.75,
    "image_generation": 0.75,
    "static_sites": 0.75,
    "competition": 0.75,
    "ecommerce": 0.75,
    "local_seo": 0.75,
}

DEFAULT_SIMILARITY_THRESHOLD = 0.75

# Weight reduction for expanded terms (80% of parent weight)
EXPANSION_WEIGHT_FACTOR = 0.8

# Maximum expansions per keyword to prevent explosion
MAX_EXPANSIONS_PER_KEYWORD = 5

# Cache file for pre-computed expansions
EXPANSION_CACHE_FILE = "semantic_expansions.json"


@dataclass
class ExpandedKeyword:
    """Represents a semantically expanded keyword."""

    original_keyword: str
    expanded_term: str
    similarity_score: float
    category: str
    weight: float  # Derived weight (parent weight * factor)


@dataclass
class SemanticExpander:
    """
    Expands keywords using spaCy word vectors for semantic similarity.

    This class provides the core functionality for finding semantically
    similar terms to expand the base keyword set. Uses FAISS for fast
    approximate nearest neighbor search when available.
    """

    model_name: str = DEFAULT_MODEL
    cache_dir: Path | None = None
    _nlp: Language | None = field(default=None, repr=False)
    _expansion_cache: dict[str, list[ExpandedKeyword]] = field(default_factory=dict, repr=False)
    _model_loaded: bool = field(default=False, repr=False)
    _vector_index: VocabVectorIndex | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Initialize the expander and attempt to load the model."""
        self._load_model()
        self._load_cache()
        self._init_vector_index()

    def _init_vector_index(self) -> None:
        """Initialize FAISS vector index if available."""
        from signalsift.processing.vector_index import VocabVectorIndex

        self._vector_index = VocabVectorIndex(cache_dir=self.cache_dir)

        if self._model_loaded and self._nlp is not None:
            if self._vector_index.is_available:
                self._vector_index.build_from_vocab(self._nlp.vocab)
            else:
                logger.info(
                    "FAISS not installed. Semantic search will use slower brute-force. "
                    "Install with: pip install faiss-cpu"
                )

    @property
    def is_available(self) -> bool:
        """Check if semantic expansion is available."""
        return self._model_loaded and self._nlp is not None

    def _load_model(self) -> None:
        """Load the spaCy model with word vectors."""
        try:
            import spacy

            try:
                self._nlp = spacy.load(self.model_name)
                self._model_loaded = True
                logger.info(f"Loaded spaCy model: {self.model_name}")
            except OSError:
                # Model not downloaded
                logger.warning(
                    f"spaCy model '{self.model_name}' not found. "
                    f"Semantic expansion disabled. To enable, run:\n"
                    f"  python -m spacy download {self.model_name}"
                )
                self._model_loaded = False

        except ImportError:
            logger.warning(
                "spaCy not installed. Semantic expansion disabled. "
                "To enable, run: pip install spacy"
            )
            self._model_loaded = False

    def _load_cache(self) -> None:
        """Load cached expansions from disk if available."""
        if self.cache_dir is None:
            return

        cache_path = self.cache_dir / EXPANSION_CACHE_FILE
        if cache_path.exists():
            try:
                with open(cache_path, encoding="utf-8") as f:
                    data = json.load(f)

                # Reconstruct ExpandedKeyword objects
                for key, expansions in data.items():
                    self._expansion_cache[key] = [ExpandedKeyword(**exp) for exp in expansions]

                logger.debug(f"Loaded {len(self._expansion_cache)} cached expansions")
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to load expansion cache: {e}")

    def _save_cache(self) -> None:
        """Save expansion cache to disk."""
        if self.cache_dir is None:
            return

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = self.cache_dir / EXPANSION_CACHE_FILE

        # Convert to serializable format
        data = {
            key: [
                {
                    "original_keyword": exp.original_keyword,
                    "expanded_term": exp.expanded_term,
                    "similarity_score": exp.similarity_score,
                    "category": exp.category,
                    "weight": exp.weight,
                }
                for exp in expansions
            ]
            for key, expansions in self._expansion_cache.items()
        }

        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        logger.debug(f"Saved {len(self._expansion_cache)} expansions to cache")

    def _get_cache_key(self, keyword: str, category: str) -> str:
        """Generate a cache key for a keyword."""
        return f"{category}:{keyword.lower()}"

    def expand_keyword(
        self,
        keyword: str,
        category: str,
        base_weight: float,
        threshold: float | None = None,
    ) -> list[ExpandedKeyword]:
        """
        Find semantically similar terms for a keyword.

        Args:
            keyword: The keyword to expand.
            category: The keyword category (affects threshold).
            base_weight: The original keyword weight.
            threshold: Custom similarity threshold (uses category default if None).

        Returns:
            List of ExpandedKeyword objects with similar terms.
        """
        if not self.is_available:
            return []
        assert self._nlp is not None

        # Check cache first
        cache_key = self._get_cache_key(keyword, category)
        if cache_key in self._expansion_cache:
            return self._expansion_cache[cache_key]

        # Determine threshold
        if threshold is None:
            threshold = CATEGORY_SIMILARITY_THRESHOLDS.get(category, DEFAULT_SIMILARITY_THRESHOLD)

        expansions: list[ExpandedKeyword] = []

        try:
            # Process the keyword
            doc = self._nlp(keyword.lower())

            # Skip if no vector (out of vocabulary)
            if not doc.has_vector or doc.vector_norm == 0:
                logger.debug(f"No vector for keyword: {keyword}")
                self._expansion_cache[cache_key] = []
                return []

            # Find similar terms in vocabulary
            similar_terms = self._find_similar_in_vocab(doc, threshold, MAX_EXPANSIONS_PER_KEYWORD)

            # Create expanded keywords
            derived_weight = base_weight * EXPANSION_WEIGHT_FACTOR

            for term, similarity in similar_terms:
                # Skip if same as original
                if term.lower() == keyword.lower():
                    continue

                expansions.append(
                    ExpandedKeyword(
                        original_keyword=keyword,
                        expanded_term=term,
                        similarity_score=similarity,
                        category=category,
                        weight=derived_weight,
                    )
                )

            # Cache the result
            self._expansion_cache[cache_key] = expansions

            if expansions:
                logger.debug(f"Expanded '{keyword}' -> {[e.expanded_term for e in expansions]}")

        except Exception as e:
            logger.warning(f"Error expanding keyword '{keyword}': {e}")
            self._expansion_cache[cache_key] = []

        return expansions

    def _find_similar_in_vocab(
        self,
        doc: spacy.tokens.Doc,
        threshold: float,
        max_results: int,
    ) -> list[tuple[str, float]]:
        """
        Find similar words using FAISS index (fast) or fallback to brute force.

        Args:
            doc: The spaCy Doc object for the keyword.
            threshold: Minimum similarity score.
            max_results: Maximum number of results.

        Returns:
            List of (term, similarity_score) tuples.
        """
        # Try FAISS first (O(log n))
        if self._vector_index is not None and self._vector_index.is_built:
            return self._vector_index.search(
                np.asarray(doc.vector, dtype=np.float32),
                k=max_results,
                threshold=threshold,
            )

        # Fallback to brute force (O(n)) - only for small vocabs or no FAISS
        logger.debug("Using brute-force similarity search (consider installing faiss-cpu)")
        return self._brute_force_search(doc, threshold, max_results)

    def _brute_force_search(
        self,
        doc: spacy.tokens.Doc,
        threshold: float,
        max_results: int,
    ) -> list[tuple[str, float]]:
        """Original brute-force implementation for fallback."""
        similar: list[tuple[str, float]] = []
        assert self._nlp is not None

        try:
            vocab = self._nlp.vocab
            candidates: list[tuple[str, float]] = []

            # Iterate through vocab strings that have vectors
            for word in vocab.strings:
                lexeme = vocab[word]

                # Skip words without vectors or non-alpha
                if not lexeme.has_vector or not lexeme.is_alpha:
                    continue

                # Skip very short or very long words
                if len(word) < 3 or len(word) > 20:
                    continue

                # Calculate similarity
                similarity = doc.similarity(self._nlp(word))

                if similarity >= threshold:
                    candidates.append((word, similarity))

            # Sort by similarity and take top results
            candidates.sort(key=lambda x: x[1], reverse=True)
            similar = candidates[:max_results]

        except Exception as e:
            logger.warning(f"Error in similarity search: {e}")

        return similar

    def expand_all_keywords(
        self,
        keywords: list[tuple[str, str, float]],
    ) -> dict[str, list[ExpandedKeyword]]:
        """
        Expand a list of keywords.

        Args:
            keywords: List of (keyword, category, weight) tuples.

        Returns:
            Dict mapping original keywords to their expansions.
        """
        all_expansions: dict[str, list[ExpandedKeyword]] = {}

        for keyword, category, weight in keywords:
            expansions = self.expand_keyword(keyword, category, weight)
            if expansions:
                all_expansions[keyword] = expansions

        # Save cache after batch expansion
        self._save_cache()

        return all_expansions

    def clear_cache(self) -> None:
        """Clear the expansion cache."""
        self._expansion_cache.clear()

        if self.cache_dir:
            cache_path = self.cache_dir / EXPANSION_CACHE_FILE
            if cache_path.exists():
                cache_path.unlink()

        logger.info("Cleared semantic expansion cache")


# Module-level instance for convenience
_default_expander: SemanticExpander | None = None


def get_expander(cache_dir: Path | None = None) -> SemanticExpander:
    """Get the default semantic expander instance."""
    global _default_expander

    if _default_expander is None:
        _default_expander = SemanticExpander(cache_dir=cache_dir)

    return _default_expander


def is_semantic_expansion_available() -> bool:
    """Check if semantic expansion is available."""
    return get_expander().is_available


def expand_keyword(
    keyword: str,
    category: str,
    base_weight: float,
) -> list[ExpandedKeyword]:
    """
    Convenience function to expand a single keyword.

    Args:
        keyword: The keyword to expand.
        category: The keyword category.
        base_weight: The original keyword weight.

    Returns:
        List of ExpandedKeyword objects.
    """
    return get_expander().expand_keyword(keyword, category, base_weight)

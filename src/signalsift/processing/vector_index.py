"""Vector index for fast approximate nearest neighbor search.

This module provides FAISS-based indexing for semantic similarity search,
replacing the O(n) brute-force vocabulary scan with O(log n) ANN search.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from signalsift.utils.logging import get_logger

if TYPE_CHECKING:
    import faiss
    from spacy.vocab import Vocab

logger = get_logger(__name__)

INDEX_CACHE_FILE = "faiss_vocab_index.json"
FAISS_INDEX_FILE = "faiss_vocab_index.faiss"


class VocabVectorIndex:
    """
    FAISS-based vector index for fast similarity search.

    Replaces O(n) vocab iteration with O(log n) approximate search.
    """

    def __init__(
        self,
        cache_dir: Path | None = None,
        nlist: int = 100,  # Number of clusters for IVF
    ) -> None:
        """
        Initialize the vector index.

        Args:
            cache_dir: Directory for caching the index.
            nlist: Number of clusters for IVF index (for large vocabularies).
        """
        self.cache_dir = cache_dir
        self.nlist = nlist
        self._index: faiss.Index | None = None
        self._words: list[str] = []
        self._word_to_idx: dict[str, int] = {}
        self._dimension: int = 0
        self._is_built = False

    @property
    def is_available(self) -> bool:
        """Check if FAISS is available."""
        try:
            import faiss  # noqa: F401

            return True
        except ImportError:
            return False

    @property
    def is_built(self) -> bool:
        """Check if the index has been built."""
        return self._is_built

    def build_from_vocab(self, vocab: Vocab) -> bool:
        """
        Build the FAISS index from spaCy vocabulary.

        Args:
            vocab: spaCy vocabulary with word vectors.

        Returns:
            True if index was built successfully.
        """
        if not self.is_available:
            logger.warning("FAISS not available. Install with: pip install faiss-cpu")
            return False

        import faiss

        # Try to load cached index
        if self._load_cache():
            logger.info("Loaded cached FAISS index")
            return True

        logger.info("Building FAISS index from vocabulary...")

        # Collect words with vectors
        words: list[str] = []
        vectors: list[np.ndarray] = []

        for word in vocab.strings:
            lexeme = vocab[word]
            if not lexeme.has_vector or not lexeme.is_alpha:
                continue
            if len(word) < 3 or len(word) > 20:
                continue

            words.append(word)
            vectors.append(np.asarray(lexeme.vector, dtype=np.float32))

        if not vectors:
            logger.warning("No vectors found in vocabulary")
            return False

        # Convert to numpy array
        vectors_array = np.array(vectors, dtype=np.float32)
        self._dimension = vectors_array.shape[1]

        logger.info(f"Building index with {len(words)} words, {self._dimension} dimensions")

        # Normalize vectors for cosine similarity
        faiss.normalize_L2(vectors_array)

        # Create IVF index for large vocabularies
        if len(words) > 10000:
            # IVF index with inner product (on normalized vectors = cosine)
            quantizer = faiss.IndexFlatIP(self._dimension)
            self._index = faiss.IndexIVFFlat(
                quantizer,
                self._dimension,
                min(self.nlist, len(words) // 10),
                faiss.METRIC_INNER_PRODUCT,
            )
            self._index.train(vectors_array)
            self._index.add(vectors_array)
            self._index.nprobe = 10  # Search 10 clusters
        else:
            # Flat index for smaller vocabularies
            self._index = faiss.IndexFlatIP(self._dimension)
            self._index.add(vectors_array)

        self._words = words
        self._word_to_idx = {word: idx for idx, word in enumerate(words)}
        self._is_built = True

        # Cache the index
        self._save_cache()

        logger.info(f"FAISS index built with {len(words)} words")
        return True

    def search(
        self,
        query_vector: np.ndarray,
        k: int = 10,
        threshold: float = 0.75,
    ) -> list[tuple[str, float]]:
        """
        Search for similar words.

        Args:
            query_vector: Query vector (will be normalized).
            k: Maximum number of results.
            threshold: Minimum similarity threshold.

        Returns:
            List of (word, similarity) tuples.
        """
        if not self._is_built or self._index is None:
            return []

        import faiss

        # Normalize query vector
        query = query_vector.astype(np.float32).reshape(1, -1)
        faiss.normalize_L2(query)

        # Search (request extra results to account for filtering)
        distances, indices = self._index.search(query, k * 2)

        results: list[tuple[str, float]] = []
        for dist, idx in zip(distances[0], indices[0], strict=False):
            if idx < 0:  # FAISS returns -1 for empty slots
                continue
            if dist < threshold:
                continue

            word = self._words[idx]
            results.append((word, float(dist)))

            if len(results) >= k:
                break

        return results

    def _cache_path(self) -> Path | None:
        """Get the cache file path."""
        if self.cache_dir is None:
            return None
        return self.cache_dir / INDEX_CACHE_FILE

    def _faiss_path(self) -> Path | None:
        """Get the FAISS index file path."""
        if self.cache_dir is None:
            return None
        return self.cache_dir / FAISS_INDEX_FILE

    def _save_cache(self) -> None:
        """Save index to cache."""
        cache_path = self._cache_path()
        faiss_path = self._faiss_path()

        if cache_path is None or faiss_path is None or self._index is None:
            return

        import faiss

        cache_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "words": self._words,
            "dimension": self._dimension,
        }

        # Save FAISS index separately
        faiss.write_index(self._index, str(faiss_path))

        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        logger.debug(f"Saved FAISS index cache to {cache_path}")

    def _load_cache(self) -> bool:
        """Load index from cache."""
        cache_path = self._cache_path()
        faiss_path = self._faiss_path()

        if cache_path is None or not cache_path.exists():
            return False
        if faiss_path is None or not faiss_path.exists():
            return False

        import faiss

        try:
            with open(cache_path, encoding="utf-8") as f:
                data = json.load(f)

            self._words = data["words"]
            self._dimension = data["dimension"]
            self._word_to_idx = {word: idx for idx, word in enumerate(self._words)}
            self._index = faiss.read_index(str(faiss_path))
            self._is_built = True

            return True

        except Exception as e:
            logger.warning(f"Failed to load FAISS cache: {e}")
            return False

    def clear_cache(self) -> None:
        """Clear cached index."""
        cache_path = self._cache_path()
        faiss_path = self._faiss_path()

        if cache_path and cache_path.exists():
            cache_path.unlink()

        if faiss_path and faiss_path.exists():
            faiss_path.unlink()

        self._index = None
        self._words = []
        self._word_to_idx = {}
        self._is_built = False

        logger.info("Cleared FAISS index cache")

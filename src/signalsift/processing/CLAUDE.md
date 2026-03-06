# Processing Pipeline

> Content enrichment pipeline: scoring, keyword matching, sentiment, trends, classification, NLP, and LLM analysis.

@rules/performance.md

## Patterns

- Each processor is a standalone module — no shared mutable state between them
- Use `@lru_cache` for expensive operations that repeat across a scan (e.g., `get_matcher()` in `keywords.py`)
- Named constants for all numeric thresholds — never inline magic numbers (see `scoring.py` for the pattern)
- NLP and LLM modules are optional — guard with `try/import` and degrade gracefully if the extra is not installed
- `KeywordMatcher` in `keywords.py` is the shared matching primitive used across scoring and classification

## Module Responsibilities

```
processing/
  scoring.py        # Relevance score (0-100) for each content type — uses named constants
  keywords.py       # KeywordMatcher class + get_matcher() cached factory
  classification.py # Category assignment based on keywords and content
  sentiment.py      # TextBlob-based sentiment analysis
  trends.py         # Detect trending topics across a time window
  entities.py       # Named entity extraction (optional: spaCy)
  semantic.py       # Semantic similarity matching (optional: FAISS)
  vector_index.py   # FAISS vector index management
  llm_analyzer.py   # LLM-powered analysis (optional: OpenAI/Anthropic)
  competitive.py    # Competitive intelligence extraction
  quotes.py         # Notable quote extraction from content
```

## Scoring Constants Pattern

Group related constants with section comments:

```python
# =============================================================================
# Reddit Scoring Constants
# =============================================================================
REDDIT_UPVOTE_DIVISOR = 2.5
REDDIT_UPVOTE_MAX_POINTS = 20
```

This makes tuning transparent — reviewers can see the intent, not just numbers.

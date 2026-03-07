"""Shared test fixtures for SignalSift."""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from signalsift.database.models import RedditThread, YouTubeVideo
from signalsift.sources.base import ContentItem


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Create a temporary database path."""
    return tmp_path / "test_signalsift.db"


@pytest.fixture
def temp_db(temp_db_path: Path) -> Generator[Path, None, None]:
    """Create a temporary test database with schema initialized."""
    from signalsift.database.schema import get_schema_sql

    # Create database with schema
    conn = sqlite3.connect(temp_db_path)
    conn.executescript(get_schema_sql())
    conn.close()

    # Patch get_db_path to return our temp path
    with patch("signalsift.database.connection.get_db_path", return_value=temp_db_path):
        yield temp_db_path


@pytest.fixture
def sample_reddit_thread() -> RedditThread:
    """Create a sample Reddit thread for testing."""
    return RedditThread(
        id="test123",
        subreddit="SEO",
        title="How I increased organic traffic by 300%",
        author="test_user",
        selftext="Here's my detailed case study with metrics and strategies...",
        url="/r/SEO/comments/test123/how_i_increased_organic_traffic/",
        score=150,
        num_comments=45,
        created_utc=1704067200,  # 2024-01-01 00:00:00 UTC
        flair="Case Study",
        captured_at=1704067200,
        relevance_score=75.0,
        matched_keywords=["organic traffic", "case study"],
        category="success_signals",
    )


@pytest.fixture
def sample_youtube_video() -> YouTubeVideo:
    """Create a sample YouTube video for testing."""
    return YouTubeVideo(
        id="dQw4w9WgXcQ",
        channel_id="UC_test_channel",
        channel_name="SEO Tutorial Channel",
        title="Complete SEO Guide for 2024",
        description="Learn everything about SEO in this comprehensive guide.",
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        duration_seconds=1800,  # 30 minutes
        view_count=50000,
        like_count=2000,
        published_at=1704067200,
        transcript="This is a test transcript about SEO strategies...",
        transcript_available=True,
        captured_at=1704067200,
        relevance_score=65.0,
        matched_keywords=["SEO", "guide"],
        category="techniques",
    )


@pytest.fixture
def sample_content_item() -> ContentItem:
    """Create a sample ContentItem for testing."""
    return ContentItem(
        id="test456",
        source_type="reddit",
        source_id="bigseo",
        title="Test title with SEO keywords",
        content="Test content about SEO strategies and keyword research",
        url="https://reddit.com/r/bigseo/comments/test456",
        created_at=datetime.now(),
        metadata={
            "score": 100,
            "num_comments": 20,
            "author": "test_author",
            "flair": "Discussion",
        },
    )


@pytest.fixture
def sample_hackernews_content_item() -> ContentItem:
    """Create a sample HackerNews ContentItem for testing."""
    return ContentItem(
        id="hn_12345678",
        source_type="hackernews",
        source_id="hackernews",
        title="Show HN: My new SEO tool",
        content="I built a tool that helps with keyword research...",
        url="https://news.ycombinator.com/item?id=12345678",
        created_at=datetime.now(),
        metadata={
            "author": "hn_user",
            "points": 150,
            "num_comments": 45,
            "story_type": "show_hn",
            "external_url": "https://example.com/seo-tool",
        },
    )


@pytest.fixture
def mock_reddit_session() -> Generator[MagicMock, None, None]:
    """Mock requests session for Reddit RSS."""
    with patch("requests.Session") as mock_session_class:
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        yield mock_session


@pytest.fixture
def mock_youtube_api() -> Generator[MagicMock, None, None]:
    """Mock YouTube API client."""
    with patch("googleapiclient.discovery.build") as mock_build:
        mock_youtube = MagicMock()
        mock_build.return_value = mock_youtube
        yield mock_youtube


@pytest.fixture
def mock_spacy_model() -> Generator[MagicMock, None, None]:
    """Mock spaCy model for semantic tests."""
    with patch("spacy.load") as mock_load:
        mock_nlp = MagicMock()
        mock_doc = MagicMock()
        mock_doc.has_vector = True
        mock_doc.vector_norm = 1.0
        mock_doc.vector = [0.1] * 300  # Fake vector
        mock_doc.similarity.return_value = 0.85
        mock_nlp.return_value = mock_doc
        mock_nlp.vocab = MagicMock()
        mock_load.return_value = mock_nlp
        yield mock_nlp

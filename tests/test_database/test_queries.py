"""Tests for database query functions."""

from signalsift.database.models import Keyword, RedditThread, Source, YouTubeVideo


class TestRedditQueries:
    """Tests for Reddit database operations."""

    def test_insert_and_retrieve_thread(self, temp_db, sample_reddit_thread: RedditThread) -> None:
        """Test basic insert and retrieval."""
        from signalsift.database.queries import get_reddit_threads, insert_reddit_thread

        insert_reddit_thread(sample_reddit_thread)

        threads = get_reddit_threads(subreddits=["SEO"])
        assert len(threads) == 1
        assert threads[0].id == "test123"
        assert threads[0].title == sample_reddit_thread.title

    def test_thread_exists(self, temp_db, sample_reddit_thread: RedditThread) -> None:
        """Test existence check."""
        from signalsift.database.queries import insert_reddit_thread, thread_exists

        assert not thread_exists("test123")
        insert_reddit_thread(sample_reddit_thread)
        assert thread_exists("test123")

    def test_filter_by_min_score(self, temp_db, sample_reddit_thread: RedditThread) -> None:
        """Test filtering by relevance score."""
        from signalsift.database.queries import get_reddit_threads, insert_reddit_thread

        sample_reddit_thread.relevance_score = 75.0
        insert_reddit_thread(sample_reddit_thread)

        high_threshold = get_reddit_threads(min_score=90.0)
        assert len(high_threshold) == 0

        low_threshold = get_reddit_threads(min_score=50.0)
        assert len(low_threshold) == 1

    def test_filter_by_processed(self, temp_db, sample_reddit_thread: RedditThread) -> None:
        """Test filtering by processed status."""
        from signalsift.database.queries import get_reddit_threads, insert_reddit_thread

        sample_reddit_thread.processed = False
        insert_reddit_thread(sample_reddit_thread)

        unprocessed = get_reddit_threads(processed=False)
        assert len(unprocessed) == 1

        processed = get_reddit_threads(processed=True)
        assert len(processed) == 0

    def test_limit(self, temp_db) -> None:
        """Test limit parameter."""
        from signalsift.database.queries import get_reddit_threads, insert_reddit_thread

        for i in range(5):
            thread = RedditThread(
                id=f"thread_{i}",
                subreddit="SEO",
                title=f"Thread {i}",
                url=f"/r/SEO/comments/thread_{i}",
                created_utc=1704067200 + i,
                captured_at=1704067200,
                matched_keywords=[],
            )
            insert_reddit_thread(thread)

        threads = get_reddit_threads(limit=3)
        assert len(threads) == 3


class TestYouTubeQueries:
    """Tests for YouTube database operations."""

    def test_insert_and_retrieve_video(self, temp_db, sample_youtube_video: YouTubeVideo) -> None:
        """Test basic insert and retrieval."""
        from signalsift.database.queries import get_youtube_videos, insert_youtube_video

        insert_youtube_video(sample_youtube_video)

        videos = get_youtube_videos(channel_ids=["UC_test_channel"])
        assert len(videos) == 1
        assert videos[0].id == "dQw4w9WgXcQ"

    def test_video_exists(self, temp_db, sample_youtube_video: YouTubeVideo) -> None:
        """Test existence check."""
        from signalsift.database.queries import insert_youtube_video, video_exists

        assert not video_exists("dQw4w9WgXcQ")
        insert_youtube_video(sample_youtube_video)
        assert video_exists("dQw4w9WgXcQ")


class TestSourceQueries:
    """Tests for source management."""

    def test_add_and_get_sources(self, temp_db) -> None:
        """Test adding and retrieving sources."""
        from signalsift.database.queries import add_source, get_sources_by_type

        source = Source(
            source_type="reddit",
            source_id="SEO",
            display_name="r/SEO",
            tier=1,
            enabled=True,
        )
        add_source(source)

        sources = get_sources_by_type("reddit")
        assert len(sources) >= 1
        seo_source = next((s for s in sources if s.source_id == "SEO"), None)
        assert seo_source is not None
        assert seo_source.tier == 1

    def test_toggle_source(self, temp_db) -> None:
        """Test enabling/disabling sources."""
        from signalsift.database.queries import (
            add_source,
            get_sources_by_type,
            toggle_source,
        )

        source = Source(source_type="reddit", source_id="test_sub", enabled=True)
        add_source(source)

        toggle_source("reddit", "test_sub", enabled=False)

        # Should not appear in enabled-only query
        sources = get_sources_by_type("reddit", enabled_only=True)
        assert not any(s.source_id == "test_sub" for s in sources)

        # Should appear when including disabled
        sources = get_sources_by_type("reddit", enabled_only=False)
        assert any(s.source_id == "test_sub" for s in sources)


class TestKeywordQueries:
    """Tests for keyword management."""

    def test_add_and_get_keywords(self, temp_db) -> None:
        """Test adding and retrieving keywords."""
        from signalsift.database.queries import add_keyword, get_keywords_by_category

        kw = Keyword(keyword="case study", category="success_signals", weight=1.5)
        add_keyword(kw)

        keywords = get_keywords_by_category("success_signals")
        assert any(k.keyword == "case study" for k in keywords)

    def test_remove_keyword(self, temp_db) -> None:
        """Test removing keywords."""
        from signalsift.database.queries import (
            add_keyword,
            get_all_keywords,
            remove_keyword,
        )

        kw = Keyword(keyword="test_keyword", category="tools")
        add_keyword(kw)

        assert remove_keyword("test_keyword") is True
        assert remove_keyword("test_keyword") is False  # Already removed

        keywords = get_all_keywords()
        assert not any(k.keyword == "test_keyword" for k in keywords)


class TestCacheOperations:
    """Tests for cache management."""

    def test_get_cache_stats(self, temp_db, sample_reddit_thread: RedditThread) -> None:
        """Test cache statistics."""
        from signalsift.database.queries import get_cache_stats, insert_reddit_thread

        insert_reddit_thread(sample_reddit_thread)

        stats = get_cache_stats()
        assert stats["reddit_total"] >= 1
        assert "youtube_total" in stats
        assert "reddit_sources" in stats

    def test_prune_old_content(self, temp_db) -> None:
        """Test pruning old processed content."""
        from signalsift.database.queries import (
            get_reddit_threads,
            insert_reddit_thread,
            prune_old_content,
        )

        # Create old processed thread
        old_thread = RedditThread(
            id="old_thread",
            subreddit="SEO",
            title="Old Thread",
            url="/r/SEO/comments/old",
            created_utc=1609459200,  # 2021-01-01
            captured_at=1609459200,
            matched_keywords=[],
            processed=True,
        )
        insert_reddit_thread(old_thread)

        # Create recent thread
        recent_thread = RedditThread(
            id="recent_thread",
            subreddit="SEO",
            title="Recent Thread",
            url="/r/SEO/comments/recent",
            created_utc=1704067200,
            captured_at=1704067200,
            matched_keywords=[],
            processed=False,
        )
        insert_reddit_thread(recent_thread)

        reddit_deleted, youtube_deleted = prune_old_content(older_than_days=30)

        # Old processed thread should be deleted
        threads = get_reddit_threads()
        assert len(threads) == 1
        assert threads[0].id == "recent_thread"

"""Tests for HackerNews model and queries."""

from signalsift.database.models import HackerNewsItem


class TestHackerNewsItem:
    """Tests for HackerNewsItem model."""

    def test_creation_with_required_fields(self) -> None:
        """Test creating an item with required fields."""
        item = HackerNewsItem(
            id="hn_12345678",
            title="Show HN: My new tool",
            url="https://news.ycombinator.com/item?id=12345678",
            created_utc=1704067200,
        )
        assert item.id == "hn_12345678"
        assert item.points == 0  # Default
        assert item.story_type == "story"  # Default

    def test_parse_keywords_from_json_string(self) -> None:
        """Test that matched_keywords parses JSON strings."""
        item = HackerNewsItem(
            id="hn_12345678",
            title="Test",
            url="https://news.ycombinator.com/item?id=12345678",
            created_utc=1704067200,
            matched_keywords='["seo", "tool"]',
        )
        assert item.matched_keywords == ["seo", "tool"]

    def test_parse_keywords_from_list(self) -> None:
        """Test that matched_keywords accepts lists directly."""
        item = HackerNewsItem(
            id="hn_12345678",
            title="Test",
            url="https://news.ycombinator.com/item?id=12345678",
            created_utc=1704067200,
            matched_keywords=["seo", "tool"],
        )
        assert item.matched_keywords == ["seo", "tool"]

    def test_to_db_dict(self) -> None:
        """Test conversion to database dictionary."""
        item = HackerNewsItem(
            id="hn_12345678",
            title="Show HN: SEO Tool",
            author="test_user",
            url="https://news.ycombinator.com/item?id=12345678",
            external_url="https://example.com/seo-tool",
            points=150,
            num_comments=45,
            created_utc=1704067200,
            story_type="show_hn",
            relevance_score=75.0,
            matched_keywords=["seo", "tool"],
            category="tool_mentions",
        )

        db_dict = item.to_db_dict()

        assert db_dict["id"] == "hn_12345678"
        assert db_dict["title"] == "Show HN: SEO Tool"
        assert db_dict["points"] == 150
        assert db_dict["story_type"] == "show_hn"
        assert db_dict["processed"] == 0  # Boolean -> int
        assert isinstance(db_dict["matched_keywords"], str)  # JSON string

    def test_created_datetime_property(self) -> None:
        """Test created_datetime property."""
        item = HackerNewsItem(
            id="hn_12345678",
            title="Test",
            url="https://news.ycombinator.com/item?id=12345678",
            created_utc=1704067200,
        )
        dt = item.created_datetime
        # Verify it returns a datetime matching the timestamp
        assert dt.timestamp() == 1704067200

    def test_hn_url_property(self) -> None:
        """Test hn_url property extracts correct URL."""
        item = HackerNewsItem(
            id="hn_12345678",
            title="Test",
            url="https://news.ycombinator.com/item?id=12345678",
            created_utc=1704067200,
        )
        assert item.hn_url == "https://news.ycombinator.com/item?id=12345678"


class TestHackerNewsQueries:
    """Tests for HackerNews database operations."""

    def test_insert_and_retrieve_item(self, temp_db) -> None:
        """Test basic insert and retrieval."""
        from signalsift.database.queries import (
            get_hackernews_items,
            insert_hackernews_item,
        )

        item = HackerNewsItem(
            id="hn_12345678",
            title="Show HN: My SEO Tool",
            author="test_user",
            url="https://news.ycombinator.com/item?id=12345678",
            points=100,
            num_comments=30,
            created_utc=1704067200,
            story_type="show_hn",
            relevance_score=65.0,
            matched_keywords=["seo", "tool"],
            category="tool_mentions",
        )
        insert_hackernews_item(item)

        items = get_hackernews_items()
        assert len(items) == 1
        assert items[0].id == "hn_12345678"
        assert items[0].title == "Show HN: My SEO Tool"
        assert items[0].points == 100

    def test_hackernews_exists(self, temp_db) -> None:
        """Test existence check."""
        from signalsift.database.queries import hackernews_exists, insert_hackernews_item

        assert not hackernews_exists("hn_12345678")

        item = HackerNewsItem(
            id="hn_12345678",
            title="Test",
            url="https://news.ycombinator.com/item?id=12345678",
            created_utc=1704067200,
        )
        insert_hackernews_item(item)

        assert hackernews_exists("hn_12345678")

    def test_filter_by_story_type(self, temp_db) -> None:
        """Test filtering by story type."""
        from signalsift.database.queries import (
            get_hackernews_items,
            insert_hackernews_item,
        )

        # Insert different story types
        for story_type in ["story", "ask_hn", "show_hn"]:
            item = HackerNewsItem(
                id=f"hn_{story_type}",
                title=f"Test {story_type}",
                url=f"https://news.ycombinator.com/item?id={story_type}",
                created_utc=1704067200,
                story_type=story_type,
            )
            insert_hackernews_item(item)

        show_items = get_hackernews_items(story_type="show_hn")
        assert len(show_items) == 1
        assert show_items[0].story_type == "show_hn"

        ask_items = get_hackernews_items(story_type="ask_hn")
        assert len(ask_items) == 1
        assert ask_items[0].story_type == "ask_hn"

    def test_insert_dict_backwards_compatible(self, temp_db) -> None:
        """Test that dict insertion still works for backwards compatibility."""
        from signalsift.database.queries import (
            get_hackernews_items,
            insert_hackernews_item,
        )

        # Insert as dict (old format)
        data = {
            "id": "hn_legacy",
            "title": "Legacy format test",
            "url": "https://news.ycombinator.com/item?id=legacy",
            "points": 50,
            "num_comments": 10,
            "created_utc": 1704067200,
            "story_type": "story",
            "captured_at": 1704067200,
            "matched_keywords": ["test"],
        }
        insert_hackernews_item(data)

        items = get_hackernews_items()
        assert len(items) == 1
        assert items[0].id == "hn_legacy"

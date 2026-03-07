"""Hacker News data source for SignalSift.

This module provides an adapter for fetching relevant discussions
from Hacker News using the Algolia Search API.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import requests

from signalsift.sources.base import BaseSource, ContentItem
from signalsift.utils.logging import get_logger

logger = get_logger(__name__)

# Hacker News Algolia API endpoints
HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"
HN_SEARCH_BY_DATE_URL = "https://hn.algolia.com/api/v1/search_by_date"
HN_ITEM_URL = "https://hn.algolia.com/api/v1/items/{item_id}"

# Default search queries for SEO-related content
DEFAULT_SEARCH_QUERIES = [
    # Core SEO
    "SEO",
    "search engine optimization",
    "google algorithm",
    "organic traffic",
    "SERP",
    # AI/LLM related
    "AI content",
    "ChatGPT SEO",
    "LLM search",
    "AI search engine",
    "generative search",
    "perplexity",
    # Content & Marketing
    "content marketing",
    "content strategy",
    "keyword research",
    "backlinks",
    "link building",
    # Technical
    "core web vitals",
    "page speed",
    "structured data",
    "schema markup",
    "site speed",
    # Tools
    "Ahrefs",
    "Semrush",
    "Moz",
    # Business/Monetization
    "affiliate marketing",
    "passive income website",
    "niche site",
    "display ads",
    "AdSense",
]


@dataclass
class HackerNewsItem:
    """Represents a Hacker News story or comment."""

    id: str
    title: str
    url: str | None
    author: str
    points: int
    num_comments: int
    created_at: datetime
    story_text: str | None  # For Ask HN / Show HN posts
    story_type: str  # "story", "ask_hn", "show_hn", "comment"


class HackerNewsSource(BaseSource):
    """
    Hacker News data source using Algolia Search API.

    Fetches SEO, AI, and tech marketing discussions from HN.
    """

    def __init__(
        self,
        search_queries: list[str] | None = None,
        min_points: int = 10,
        min_comments: int = 5,
        request_delay: float = 1.0,
    ) -> None:
        """
        Initialize the Hacker News source.

        Args:
            search_queries: List of search queries to use.
            min_points: Minimum points for a story to be included.
            min_comments: Minimum comments for a story to be included.
            request_delay: Delay between API requests in seconds.
        """
        self.search_queries = search_queries or DEFAULT_SEARCH_QUERIES
        self.min_points = min_points
        self.min_comments = min_comments
        self.request_delay = request_delay
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "SignalSift/1.0 (https://autoscript.studio)"})

    def get_source_type(self) -> str:
        """Return the source type identifier."""
        return "hackernews"

    def test_connection(self) -> bool:
        """Test connectivity to the Hacker News Algolia API."""
        try:
            response = self._session.get(
                HN_SEARCH_URL,
                params={"query": "test", "hitsPerPage": 1},
                timeout=10,
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Hacker News connection test failed: {e}")
            return False

    def fetch(
        self,
        since: datetime | None = None,
        limit: int | None = None,
    ) -> list[ContentItem]:
        """
        Fetch content from Hacker News.

        Args:
            since: Only fetch content newer than this datetime.
            limit: Maximum number of items to fetch per query.

        Returns:
            List of ContentItem objects.
        """
        if since is None:
            since = datetime.now() - timedelta(days=30)
        effective_limit = limit if limit is not None else 100

        all_items: dict[str, ContentItem] = {}  # Use dict to dedupe by ID

        for query in self.search_queries:
            try:
                items = self._search(query, since, effective_limit)
                for item in items:
                    if item.id not in all_items:
                        all_items[item.id] = item

                # Rate limiting
                time.sleep(self.request_delay)

            except Exception as e:
                logger.warning(f"Failed to fetch HN for query '{query}': {e}")
                continue

        logger.info(f"Fetched {len(all_items)} unique items from Hacker News")
        return list(all_items.values())

    def _search(
        self,
        query: str,
        since: datetime,
        limit: int,
    ) -> list[ContentItem]:
        """
        Search Hacker News for a query.

        Args:
            query: Search query.
            since: Only return items newer than this.
            limit: Maximum results.

        Returns:
            List of ContentItem objects.
        """
        items: list[ContentItem] = []
        since_timestamp = int(since.timestamp())

        try:
            # Use search_by_date for chronological results
            response = self._session.get(
                HN_SEARCH_BY_DATE_URL,
                params={
                    "query": query,
                    "tags": "story",  # Only stories, not comments
                    "numericFilters": f"created_at_i>{since_timestamp},points>={self.min_points}",
                    "hitsPerPage": min(limit, 100),
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            for hit in data.get("hits", []):
                # Filter by comment count
                num_comments = hit.get("num_comments", 0)
                if num_comments < self.min_comments:
                    continue

                item = self._hit_to_content_item(hit)
                if item:
                    items.append(item)

        except requests.RequestException as e:
            logger.warning(f"HN API request failed: {e}")

        return items

    def _hit_to_content_item(self, hit: dict[str, Any]) -> ContentItem | None:
        """Convert an Algolia hit to a ContentItem."""
        try:
            object_id = hit.get("objectID", "")
            title = hit.get("title", "")

            if not object_id or not title:
                return None

            # Determine story type
            story_type = "story"
            if title.lower().startswith("ask hn"):
                story_type = "ask_hn"
            elif title.lower().startswith("show hn"):
                story_type = "show_hn"

            # Get content (story text for self posts)
            story_text = hit.get("story_text") or ""

            # Parse timestamp
            created_at_i = hit.get("created_at_i", 0)
            created_at = datetime.fromtimestamp(created_at_i) if created_at_i else datetime.now()

            # Build URL
            external_url = hit.get("url")
            hn_url = f"https://news.ycombinator.com/item?id={object_id}"

            return ContentItem(
                id=f"hn_{object_id}",
                source_type="hackernews",
                source_id="hackernews",
                title=title,
                content=story_text,
                url=hn_url,
                created_at=created_at,
                metadata={
                    "author": hit.get("author", "unknown"),
                    "points": hit.get("points", 0),
                    "num_comments": hit.get("num_comments", 0),
                    "external_url": external_url,
                    "story_type": story_type,
                    "tags": hit.get("_tags", []),
                },
            )

        except Exception as e:
            logger.debug(f"Failed to parse HN hit: {e}")
            return None

    def fetch_item_with_comments(
        self,
        item_id: str,
        max_comments: int = 50,
    ) -> tuple[HackerNewsItem | None, list[str]]:
        """
        Fetch a single item with its top comments.

        Useful for getting more context on high-value discussions.

        Args:
            item_id: The Hacker News item ID.
            max_comments: Maximum number of comments to fetch.

        Returns:
            Tuple of (item, list of comment texts).
        """
        try:
            response = self._session.get(
                HN_ITEM_URL.format(item_id=item_id),
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            # Parse item
            item = HackerNewsItem(
                id=str(data.get("id", "")),
                title=data.get("title", ""),
                url=data.get("url"),
                author=data.get("author", "unknown"),
                points=data.get("points", 0),
                num_comments=data.get("num_comments", 0) or len(data.get("children", [])),
                created_at=datetime.fromtimestamp(data.get("created_at_i", 0)),
                story_text=data.get("text"),
                story_type=data.get("type", "story"),
            )

            # Extract top-level comment texts
            comments: list[str] = []
            for child in data.get("children", [])[:max_comments]:
                if child.get("text"):
                    comments.append(child["text"])

            return item, comments

        except Exception as e:
            logger.warning(f"Failed to fetch HN item {item_id}: {e}")
            return None, []

    def get_front_page(self, limit: int = 30) -> list[ContentItem]:
        """
        Get current front page stories.

        Args:
            limit: Maximum number of stories.

        Returns:
            List of ContentItem objects.
        """
        items: list[ContentItem] = []

        try:
            response = self._session.get(
                HN_SEARCH_URL,
                params={
                    "tags": "front_page",
                    "hitsPerPage": min(limit, 30),
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            for hit in data.get("hits", []):
                item = self._hit_to_content_item(hit)
                if item:
                    items.append(item)

        except requests.RequestException as e:
            logger.warning(f"Failed to fetch HN front page: {e}")

        return items

    def search_recent(
        self,
        query: str,
        days: int = 7,
        limit: int = 50,
    ) -> list[ContentItem]:
        """
        Search for recent discussions matching a query.

        Args:
            query: Search query.
            days: Number of days to look back.
            limit: Maximum results.

        Returns:
            List of ContentItem objects.
        """
        since = datetime.now() - timedelta(days=days)
        return self._search(query, since, limit)


# Module-level instance
_default_source: HackerNewsSource | None = None


def get_hackernews_source() -> HackerNewsSource:
    """Get the default Hacker News source instance."""
    global _default_source
    if _default_source is None:
        _default_source = HackerNewsSource()
    return _default_source


def fetch_hackernews(
    since: datetime | None = None,
    limit: int = 100,
) -> list[ContentItem]:
    """Convenience function to fetch Hacker News content."""
    return get_hackernews_source().fetch(since=since, limit=limit)

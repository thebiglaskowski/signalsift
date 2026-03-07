"""Reddit data source adapter using RSS feeds (no API key required)."""

import hashlib
import html
import re
import time
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Any

import feedparser
import requests

from signalsift.config import get_settings
from signalsift.database.models import RedditThread
from signalsift.database.queries import (
    get_sources_by_type,
    thread_exists,
    update_source_last_fetched,
)
from signalsift.sources.base import BaseSource, ContentItem
from signalsift.utils.logging import get_logger

logger = get_logger(__name__)

# Reddit RSS user agent
USER_AGENT = "SignalSift RSS/1.0 (RSS feed reader)"


class RedditRSSSource(BaseSource):
    """Reddit data source using public RSS feeds (no API key required)."""

    def __init__(self) -> None:
        """Initialize the Reddit RSS source."""
        self.settings = get_settings()
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": USER_AGENT})

    def get_source_type(self) -> str:
        """Return the source type identifier."""
        return "reddit"

    def test_connection(self) -> bool:
        """Test if Reddit RSS feeds are accessible."""
        try:
            url = "https://www.reddit.com/r/test/.rss"
            response = self._session.get(url, timeout=10)
            return bool(response.status_code == 200)
        except Exception as e:
            logger.error(f"Reddit RSS connection test failed: {e}")
            return False

    def fetch(
        self,
        since: datetime | None = None,
        limit: int | None = None,
    ) -> list[ContentItem]:
        """
        Fetch content from all enabled Reddit sources via RSS.

        Args:
            since: Only fetch content created after this datetime.
            limit: Maximum items per subreddit.

        Returns:
            List of ContentItem objects.
        """
        sources = get_sources_by_type("reddit", enabled_only=True)
        if not sources:
            logger.warning("No enabled Reddit sources found")
            return []

        all_items: list[ContentItem] = []
        limit = limit or self.settings.reddit.posts_per_subreddit

        for source in sources:
            try:
                items = self._fetch_subreddit(
                    subreddit_name=source.source_id,
                    tier=source.tier,
                    since=since,
                    limit=limit,
                )
                all_items.extend(items)
                update_source_last_fetched("reddit", source.source_id)

                # Polite delay between subreddits
                time.sleep(self.settings.reddit.request_delay_seconds)

            except Exception as e:
                logger.error(f"Error fetching r/{source.source_id} RSS: {e}")
                continue

        return all_items

    def fetch_subreddit(
        self,
        subreddit_name: str,
        since: datetime | None = None,
        limit: int | None = None,
    ) -> list[ContentItem]:
        """
        Fetch content from a specific subreddit via RSS.

        Args:
            subreddit_name: Name of the subreddit.
            since: Only fetch content created after this datetime.
            limit: Maximum items to fetch.

        Returns:
            List of ContentItem objects.
        """
        return self._fetch_subreddit(
            subreddit_name=subreddit_name,
            tier=2,  # Default tier
            since=since,
            limit=limit or self.settings.reddit.posts_per_subreddit,
        )

    def _fetch_subreddit(
        self,
        subreddit_name: str,
        tier: int,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[ContentItem]:
        """Internal method to fetch from a subreddit via RSS."""
        logger.info(f"Fetching from r/{subreddit_name} via RSS (tier {tier})")

        # Calculate time filter
        if since is None:
            since = datetime.now() - timedelta(days=self.settings.reddit.max_age_days)

        items: list[ContentItem] = []
        posts_seen: set[str] = set()

        # Fetch from multiple RSS endpoints for better coverage
        # Reddit RSS endpoints: hot, new, top, rising
        endpoints = ["hot", "new"]

        for endpoint in endpoints:
            try:
                url = f"https://www.reddit.com/r/{subreddit_name}/{endpoint}/.rss"
                response = self._session.get(url, timeout=30)

                if response.status_code == 404:
                    logger.warning(f"Subreddit r/{subreddit_name} not found or private")
                    break
                elif response.status_code == 429:
                    logger.warning("Reddit rate limit hit, waiting...")
                    time.sleep(5)
                    continue
                elif response.status_code != 200:
                    logger.warning(
                        f"Failed to fetch r/{subreddit_name}/{endpoint}: HTTP {response.status_code}"
                    )
                    continue

                feed = feedparser.parse(response.content)

                for entry in feed.entries:
                    post_id = self._extract_post_id(entry)
                    if post_id and post_id not in posts_seen:
                        posts_seen.add(post_id)
                        item = self._process_entry(entry, subreddit_name, tier, since)
                        if item:
                            items.append(item)

                        if len(items) >= limit:
                            break

                # Small delay between endpoints
                time.sleep(1)

            except Exception as e:
                logger.warning(f"Error fetching r/{subreddit_name}/{endpoint} RSS: {e}")
                continue

            if len(items) >= limit:
                break

        logger.info(f"Fetched {len(items)} posts from r/{subreddit_name} via RSS")
        return items

    def _extract_post_id(self, entry: Any) -> str | None:
        """Extract the Reddit post ID from an RSS entry."""
        # The ID is usually in the link: https://www.reddit.com/r/subreddit/comments/POST_ID/...
        link = entry.get("link", "")
        if "/comments/" in link:
            parts = link.split("/comments/")
            if len(parts) > 1:
                post_id = parts[1].split("/")[0]
                return str(post_id)
        return None

    def _process_entry(
        self,
        entry: Any,
        subreddit_name: str,
        tier: int,
        since: datetime,
    ) -> ContentItem | None:
        """Process a single RSS entry."""
        try:
            # Parse published date
            published = entry.get("published") or entry.get("updated")
            if published:
                try:
                    created_at = parsedate_to_datetime(published)
                    # Make timezone naive for comparison
                    if created_at.tzinfo is not None:
                        created_at = created_at.replace(tzinfo=None)
                except Exception:
                    created_at = datetime.now()
            else:
                created_at = datetime.now()

            # Check if post is too old
            if created_at < since:
                return None

            # Extract post ID
            post_id = self._extract_post_id(entry)
            if not post_id:
                return None

            # Check if already in cache
            if thread_exists(post_id):
                return None

            # Extract title
            title = entry.get("title", "")
            if not title:
                return None

            # RSS feeds include HTML content - extract text
            content = self._extract_content(entry)

            # Skip if no meaningful content
            if not content or content in ("[removed]", "[deleted]"):
                return None

            # Extract author
            author = None
            if "author_detail" in entry:
                author = entry.author_detail.get("name", "").replace("/u/", "")
            elif "author" in entry:
                author = str(entry.author).replace("/u/", "")

            # Build metadata
            # Note: RSS feeds don't include score/comments - set defaults
            metadata: dict[str, Any] = {
                "score": 0,  # Not available in RSS
                "num_comments": 0,  # Not available in RSS
                "flair": None,
                "author": author,
                "tier": tier,
                "upvote_ratio": 0,
                "source_method": "rss",  # Track that this came from RSS
            }

            return ContentItem(
                id=post_id,
                source_type="reddit",
                source_id=subreddit_name,
                title=title,
                content=content,
                url=entry.get("link", f"https://reddit.com/r/{subreddit_name}/comments/{post_id}"),
                created_at=created_at,
                metadata=metadata,
            )

        except Exception as e:
            logger.debug(f"Error processing RSS entry: {e}")
            return None

    def _extract_content(self, entry: Any) -> str:
        """Extract text content from RSS entry, stripping HTML."""
        # RSS entries have content in 'content' or 'summary'
        raw_content = ""
        if "content" in entry and entry.content:
            raw_content = entry.content[0].get("value", "")
        elif "summary" in entry:
            raw_content = entry.summary

        if not raw_content:
            return ""

        # Strip HTML tags using stdlib html.parser, then decode entities
        text = re.sub(r"<[^>]+>", " ", raw_content)
        text = html.unescape(text)
        # Clean up whitespace
        text = re.sub(r"\s+", " ", text).strip()

        # RSS often includes "[link]" or "[comments]" markers at the end
        text = re.sub(r"\[link\]\s*\[comments\]\s*$", "", text).strip()
        text = re.sub(r"\[link\]\s*$", "", text).strip()
        text = re.sub(r"\[comments\]\s*$", "", text).strip()

        return text

    def content_item_to_thread(self, item: ContentItem) -> RedditThread:
        """Convert a ContentItem to a RedditThread model."""
        # Calculate content hash
        content_hash = hashlib.sha256((item.title + item.content).encode()).hexdigest()

        return RedditThread(
            id=item.id,
            subreddit=item.source_id,
            title=item.title,
            author=item.metadata.get("author"),
            selftext=item.content,
            url=item.url,
            score=item.metadata.get("score", 0),
            num_comments=item.metadata.get("num_comments", 0),
            created_utc=int(item.created_at.timestamp()),
            flair=item.metadata.get("flair"),
            content_hash=content_hash,
        )

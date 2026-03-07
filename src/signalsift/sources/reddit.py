"""Reddit data source adapter using PRAW."""

import hashlib
import time
from datetime import datetime, timedelta
from typing import Any

import praw
from praw.models import Submission

from signalsift.config import get_settings
from signalsift.database.models import RedditThread
from signalsift.database.queries import (
    get_sources_by_type,
    thread_exists,
    update_source_last_fetched,
)
from signalsift.exceptions import RedditError
from signalsift.sources.base import BaseSource, ContentItem
from signalsift.utils.logging import get_logger

logger = get_logger(__name__)


class RedditSource(BaseSource):
    """Reddit data source using PRAW."""

    def __init__(self) -> None:
        """Initialize the Reddit source."""
        self.settings = get_settings()
        self._reddit: praw.Reddit | None = None

    @property
    def reddit(self) -> praw.Reddit:
        """Get or create the Reddit instance."""
        if self._reddit is None:
            if not self.settings.has_reddit_credentials():
                raise RedditError(
                    "Reddit credentials not configured. "
                    "Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET environment variables."
                )

            self._reddit = praw.Reddit(
                client_id=self.settings.reddit.client_id,
                client_secret=self.settings.reddit.client_secret,
                user_agent=self.settings.reddit.user_agent,
            )
        return self._reddit

    def get_source_type(self) -> str:
        """Return the source type identifier."""
        return "reddit"

    def test_connection(self) -> bool:
        """Test if the Reddit connection is working."""
        try:
            # Try to access a public subreddit
            subreddit = self.reddit.subreddit("test")
            _ = subreddit.display_name
            return True
        except Exception as e:
            logger.error(f"Reddit connection test failed: {e}")
            return False

    def fetch(
        self,
        since: datetime | None = None,
        limit: int | None = None,
    ) -> list[ContentItem]:
        """
        Fetch content from all enabled Reddit sources.

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
                logger.error(f"Error fetching r/{source.source_id}: {e}")
                continue

        return all_items

    def fetch_subreddit(
        self,
        subreddit_name: str,
        since: datetime | None = None,
        limit: int | None = None,
    ) -> list[ContentItem]:
        """
        Fetch content from a specific subreddit.

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
        """Internal method to fetch from a subreddit."""
        logger.info(f"Fetching from r/{subreddit_name} (tier {tier})")

        # Calculate time filter
        if since is None:
            since = datetime.now() - timedelta(days=self.settings.reddit.max_age_days)

        since_timestamp = int(since.timestamp())

        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            items: list[ContentItem] = []

            # Fetch from both hot and new for better coverage
            posts_seen: set[str] = set()

            for post in subreddit.hot(limit=limit):
                if post.id not in posts_seen:
                    posts_seen.add(post.id)
                    item = self._process_post(post, subreddit_name, tier, since_timestamp)
                    if item:
                        items.append(item)

            for post in subreddit.new(limit=limit):
                if post.id not in posts_seen:
                    posts_seen.add(post.id)
                    item = self._process_post(post, subreddit_name, tier, since_timestamp)
                    if item:
                        items.append(item)

            logger.info(f"Fetched {len(items)} new posts from r/{subreddit_name}")
            return items

        except Exception as e:
            logger.error(f"Error fetching r/{subreddit_name}: {e}")
            raise RedditError(f"Failed to fetch r/{subreddit_name}: {e}") from e

    def _process_post(
        self,
        post: Submission,
        subreddit_name: str,
        tier: int,
        since_timestamp: int,
    ) -> ContentItem | None:
        """Process a single Reddit post."""
        # Check if post is too old
        if post.created_utc < since_timestamp:
            return None

        # Check if post meets minimum requirements
        if post.score < self.settings.reddit.min_score:
            return None

        if post.num_comments < self.settings.reddit.min_comments:
            return None

        # Skip non-text posts
        if not post.is_self:
            return None

        # Skip removed/deleted content
        selftext = post.selftext or ""
        if selftext in ("[removed]", "[deleted]", ""):
            return None

        # Check if already in cache
        if thread_exists(post.id):
            return None

        # Build metadata
        metadata: dict[str, Any] = {
            "score": post.score,
            "num_comments": post.num_comments,
            "flair": post.link_flair_text,
            "author": str(post.author) if post.author else None,
            "tier": tier,
            "upvote_ratio": post.upvote_ratio,
        }

        return ContentItem(
            id=post.id,
            source_type="reddit",
            source_id=subreddit_name,
            title=post.title,
            content=selftext,
            url=f"https://reddit.com{post.permalink}",
            created_at=datetime.fromtimestamp(post.created_utc),
            metadata=metadata,
        )

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

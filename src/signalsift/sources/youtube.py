"""YouTube data source adapter."""

import hashlib
import re
import time
from datetime import datetime, timedelta
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

from signalsift.config import get_settings
from signalsift.database.models import YouTubeVideo
from signalsift.database.queries import (
    get_sources_by_type,
    update_source_last_fetched,
    video_exists,
)
from signalsift.exceptions import YouTubeError
from signalsift.sources.base import BaseSource, ContentItem
from signalsift.utils.logging import get_logger

logger = get_logger(__name__)


class YouTubeSource(BaseSource):
    """YouTube data source using YouTube Data API and transcript API."""

    def __init__(self) -> None:
        """Initialize the YouTube source."""
        self.settings = get_settings()
        self._youtube = None
        self._transcript_api = YouTubeTranscriptApi()

    @property
    def youtube(self) -> Any:
        """Get or create the YouTube API client."""
        if self._youtube is None:
            if not self.settings.has_youtube_credentials():
                raise YouTubeError(
                    "YouTube API key not configured. "
                    "Set YOUTUBE_API_KEY environment variable."
                )

            self._youtube = build(
                "youtube", "v3", developerKey=self.settings.youtube.api_key
            )
        return self._youtube

    def get_source_type(self) -> str:
        """Return the source type identifier."""
        return "youtube"

    def test_connection(self) -> bool:
        """Test if the YouTube connection is working."""
        try:
            # Try to search for a video
            request = self.youtube.search().list(
                part="snippet",
                q="test",
                type="video",
                maxResults=1,
            )
            request.execute()
            return True
        except Exception as e:
            logger.error(f"YouTube connection test failed: {e}")
            return False

    def fetch(
        self,
        since: datetime | None = None,
        limit: int | None = None,
    ) -> list[ContentItem]:
        """
        Fetch content from all enabled YouTube sources.

        Args:
            since: Only fetch content published after this datetime.
            limit: Maximum videos per channel.

        Returns:
            List of ContentItem objects.
        """
        sources = get_sources_by_type("youtube", enabled_only=True)
        if not sources:
            logger.warning("No enabled YouTube sources found")
            return []

        all_items: list[ContentItem] = []
        limit = limit or self.settings.youtube.videos_per_channel

        for source in sources:
            try:
                items = self._fetch_channel(
                    channel_id=source.source_id,
                    channel_name=source.display_name or source.source_id,
                    tier=source.tier,
                    since=since,
                    limit=limit,
                )
                all_items.extend(items)
                update_source_last_fetched("youtube", source.source_id)

                # Polite delay between channels
                time.sleep(1)

            except Exception as e:
                logger.error(f"Error fetching channel {source.source_id}: {e}")
                continue

        return all_items

    def fetch_channel(
        self,
        channel_id: str,
        channel_name: str | None = None,
        since: datetime | None = None,
        limit: int | None = None,
    ) -> list[ContentItem]:
        """
        Fetch content from a specific YouTube channel.

        Args:
            channel_id: YouTube channel ID.
            channel_name: Display name for the channel.
            since: Only fetch videos published after this datetime.
            limit: Maximum videos to fetch.

        Returns:
            List of ContentItem objects.
        """
        return self._fetch_channel(
            channel_id=channel_id,
            channel_name=channel_name or channel_id,
            tier=2,  # Default tier
            since=since,
            limit=limit or self.settings.youtube.videos_per_channel,
        )

    def _resolve_handle(self, handle: str) -> str | None:
        """Resolve a @handle to a channel ID via the YouTube API."""
        try:
            response = self.youtube.channels().list(
                part="id",
                forHandle=handle.lstrip("@"),
            ).execute()
            items = response.get("items", [])
            return items[0]["id"] if items else None
        except HttpError as e:
            logger.error(f"YouTube API error resolving handle {handle}: {e}")
            return None

    def _fetch_channel(
        self,
        channel_id: str,
        channel_name: str,
        tier: int,
        since: datetime | None = None,
        limit: int = 10,
    ) -> list[ContentItem]:
        """Internal method to fetch from a channel."""
        # Resolve @handle to a real channel ID if needed
        if channel_id.startswith("@"):
            resolved = self._resolve_handle(channel_id)
            if not resolved:
                logger.warning(f"Could not resolve YouTube handle: {channel_id}")
                return []
            logger.info(f"Resolved {channel_id} -> {resolved}")
            channel_id = resolved

        logger.info(f"Fetching from channel: {channel_name} ({channel_id})")

        # Calculate time filter
        if since is None:
            since = datetime.now() - timedelta(days=self.settings.youtube.max_age_days)

        try:
            # Get uploads playlist ID
            channels_response = self.youtube.channels().list(
                part="contentDetails",
                id=channel_id,
            ).execute()

            if not channels_response.get("items"):
                logger.warning(f"Channel not found: {channel_id}")
                return []

            uploads_playlist_id = (
                channels_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
            )

            # Get videos from uploads playlist
            videos_response = self.youtube.playlistItems().list(
                part="snippet,contentDetails",
                playlistId=uploads_playlist_id,
                maxResults=min(limit, 50),  # API max is 50
            ).execute()

            items: list[ContentItem] = []

            for video_item in videos_response.get("items", []):
                video_id = video_item["contentDetails"]["videoId"]

                # Skip if already in cache
                if video_exists(video_id):
                    continue

                # Get detailed video info
                video_details = self._get_video_details(video_id)
                if not video_details:
                    continue

                # Check if video meets criteria
                item = self._process_video(
                    video_id=video_id,
                    video_details=video_details,
                    channel_id=channel_id,
                    channel_name=channel_name,
                    tier=tier,
                    since=since,
                )

                if item:
                    items.append(item)

                # Brief delay between transcript fetches
                time.sleep(0.5)

            logger.info(f"Fetched {len(items)} new videos from {channel_name}")
            return items

        except HttpError as e:
            logger.error(f"YouTube API error for channel {channel_id}: {e}")
            raise YouTubeError(f"Failed to fetch channel {channel_id}: {e}") from e

    def _get_video_details(self, video_id: str) -> dict[str, Any] | None:
        """Get detailed information for a video."""
        try:
            response = self.youtube.videos().list(
                part="snippet,contentDetails,statistics",
                id=video_id,
            ).execute()

            if response.get("items"):
                return dict(response["items"][0])
            return None

        except HttpError as e:
            logger.error(f"Error getting video details for {video_id}: {e}")
            return None

    def _process_video(
        self,
        video_id: str,
        video_details: dict[str, Any],
        channel_id: str,
        channel_name: str,
        tier: int,
        since: datetime,
    ) -> ContentItem | None:
        """Process a single YouTube video."""
        snippet = video_details.get("snippet", {})
        content_details = video_details.get("contentDetails", {})
        statistics = video_details.get("statistics", {})

        # Parse published date
        published_at_str = snippet.get("publishedAt", "")
        try:
            published_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
            published_at = published_at.replace(tzinfo=None)  # Make naive for comparison
        except ValueError:
            logger.warning(f"Could not parse date for video {video_id}")
            return None

        # Check if video is too old
        if published_at < since:
            return None

        # Parse duration
        duration_str = content_details.get("duration", "PT0S")
        duration_seconds = self._parse_duration(duration_str)

        # Check duration requirements
        if duration_seconds < self.settings.youtube.min_duration_seconds:
            return None
        if duration_seconds > self.settings.youtube.max_duration_seconds:
            return None

        # Get transcript
        transcript = self._get_transcript(video_id)

        # Build metadata
        metadata: dict[str, Any] = {
            "channel_id": channel_id,
            "channel_name": channel_name,
            "duration_seconds": duration_seconds,
            "view_count": int(statistics.get("viewCount", 0)),
            "like_count": int(statistics.get("likeCount", 0)),
            "tier": tier,
            "transcript_available": transcript is not None,
            "description": snippet.get("description", ""),
        }

        return ContentItem(
            id=video_id,
            source_type="youtube",
            source_id=channel_id,
            title=snippet.get("title", ""),
            content=transcript or "",
            url=f"https://www.youtube.com/watch?v={video_id}",
            created_at=published_at,
            metadata=metadata,
        )

    def _get_transcript(self, video_id: str) -> str | None:
        """Get transcript for a video."""
        try:
            transcript_list = self._transcript_api.fetch(
                video_id,
                languages=[self.settings.youtube.transcript_language, "en"],
            )

            # Join all transcript snippets
            full_text = " ".join(snippet.text for snippet in transcript_list)

            # Clean up transcript
            full_text = self._clean_transcript(full_text)

            # Truncate if too long
            max_length = self.settings.youtube.transcript_max_length
            if len(full_text) > max_length:
                full_text = full_text[:max_length] + "..."

            return full_text

        except (TranscriptsDisabled, NoTranscriptFound):
            logger.debug(f"No transcript available for video {video_id}")
            return None
        except VideoUnavailable:
            logger.warning(f"Video unavailable: {video_id}")
            return None
        except Exception as e:
            logger.error(f"Error getting transcript for {video_id}: {e}")
            return None

    def _clean_transcript(self, text: str) -> str:
        """Clean up transcript text."""
        # Remove common artifacts
        artifacts = [
            "[Music]",
            "[Applause]",
            "[Laughter]",
            "[Silence]",
            "[Inaudible]",
        ]
        for artifact in artifacts:
            text = text.replace(artifact, "")

        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def _parse_duration(self, duration_str: str) -> int:
        """Parse ISO 8601 duration string to seconds."""
        # PT1H30M15S -> 5415 seconds
        pattern = r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?"
        match = re.match(pattern, duration_str)

        if not match:
            return 0

        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)

        return hours * 3600 + minutes * 60 + seconds

    def content_item_to_video(self, item: ContentItem) -> YouTubeVideo:
        """Convert a ContentItem to a YouTubeVideo model."""
        # Calculate content hash
        content_for_hash = item.title + (item.content or "")
        content_hash = hashlib.sha256(content_for_hash.encode()).hexdigest()

        return YouTubeVideo(
            id=item.id,
            channel_id=item.source_id,
            channel_name=item.metadata.get("channel_name"),
            title=item.title,
            description=item.metadata.get("description"),
            url=item.url,
            duration_seconds=item.metadata.get("duration_seconds"),
            view_count=item.metadata.get("view_count", 0),
            like_count=item.metadata.get("like_count", 0),
            published_at=int(item.created_at.timestamp()),
            transcript=item.content if item.content else None,
            transcript_available=item.metadata.get("transcript_available", False),
            content_hash=content_hash,
        )

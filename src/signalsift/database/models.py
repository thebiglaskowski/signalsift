"""Pydantic models for database records."""

import json
from datetime import datetime
from typing import Any, cast

from pydantic import BaseModel, Field, field_validator


class RedditThread(BaseModel):
    """Model for a Reddit thread."""

    id: str
    subreddit: str
    title: str
    author: str | None = None
    selftext: str | None = None
    url: str
    score: int = 0
    num_comments: int = 0
    created_utc: int
    flair: str | None = None
    captured_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    content_hash: str | None = None
    relevance_score: float = 0.0
    matched_keywords: list[str] = Field(default_factory=list)
    category: str | None = None
    processed: bool = False
    report_id: str | None = None

    @field_validator("matched_keywords", mode="before")
    @classmethod
    def parse_keywords(cls, v: Any) -> list[str]:
        """Parse keywords from JSON string if needed."""
        if isinstance(v, str):
            try:
                return cast(list[str], json.loads(v))
            except json.JSONDecodeError:
                return []
        return cast(list[str], v) if v else []

    def to_db_dict(self) -> dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            "id": self.id,
            "subreddit": self.subreddit,
            "title": self.title,
            "author": self.author,
            "selftext": self.selftext,
            "url": self.url,
            "score": self.score,
            "num_comments": self.num_comments,
            "created_utc": self.created_utc,
            "flair": self.flair,
            "captured_at": self.captured_at,
            "content_hash": self.content_hash,
            "relevance_score": self.relevance_score,
            "matched_keywords": json.dumps(self.matched_keywords),
            "category": self.category,
            "processed": 1 if self.processed else 0,
            "report_id": self.report_id,
        }

    @property
    def created_datetime(self) -> datetime:
        """Get created_utc as datetime."""
        return datetime.fromtimestamp(self.created_utc)

    @property
    def permalink(self) -> str:
        """Get Reddit permalink."""
        return f"https://reddit.com{self.url}" if not self.url.startswith("http") else self.url


class YouTubeVideo(BaseModel):
    """Model for a YouTube video."""

    id: str
    channel_id: str
    channel_name: str | None = None
    title: str
    description: str | None = None
    url: str
    duration_seconds: int | None = None
    view_count: int = 0
    like_count: int = 0
    published_at: int
    transcript: str | None = None
    transcript_available: bool = False
    captured_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    content_hash: str | None = None
    relevance_score: float = 0.0
    matched_keywords: list[str] = Field(default_factory=list)
    category: str | None = None
    processed: bool = False
    report_id: str | None = None

    @field_validator("matched_keywords", mode="before")
    @classmethod
    def parse_keywords(cls, v: Any) -> list[str]:
        """Parse keywords from JSON string if needed."""
        if isinstance(v, str):
            try:
                return cast(list[str], json.loads(v))
            except json.JSONDecodeError:
                return []
        return cast(list[str], v) if v else []

    def to_db_dict(self) -> dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            "id": self.id,
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "title": self.title,
            "description": self.description,
            "url": self.url,
            "duration_seconds": self.duration_seconds,
            "view_count": self.view_count,
            "like_count": self.like_count,
            "published_at": self.published_at,
            "transcript": self.transcript,
            "transcript_available": 1 if self.transcript_available else 0,
            "captured_at": self.captured_at,
            "content_hash": self.content_hash,
            "relevance_score": self.relevance_score,
            "matched_keywords": json.dumps(self.matched_keywords),
            "category": self.category,
            "processed": 1 if self.processed else 0,
            "report_id": self.report_id,
        }

    @property
    def published_datetime(self) -> datetime:
        """Get published_at as datetime."""
        return datetime.fromtimestamp(self.published_at)

    @property
    def duration_formatted(self) -> str:
        """Get duration as formatted string (e.g., '15:30')."""
        if not self.duration_seconds:
            return "N/A"
        minutes, seconds = divmod(self.duration_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"


class Report(BaseModel):
    """Model for a generated report."""

    id: str
    generated_at: int
    filepath: str
    reddit_count: int = 0
    youtube_count: int = 0
    date_range_start: int | None = None
    date_range_end: int | None = None
    config_snapshot: str | None = None

    @property
    def generated_datetime(self) -> datetime:
        """Get generated_at as datetime."""
        return datetime.fromtimestamp(self.generated_at)


class Keyword(BaseModel):
    """Model for a tracked keyword."""

    id: int | None = None
    keyword: str
    category: str
    weight: float = 1.0
    enabled: bool = True


class Source(BaseModel):
    """Model for a content source (subreddit or YouTube channel)."""

    id: int | None = None
    source_type: str  # "reddit" or "youtube"
    source_id: str  # subreddit name or channel ID
    display_name: str | None = None
    tier: int = 2
    enabled: bool = True
    last_fetched: int | None = None

    @property
    def last_fetched_datetime(self) -> datetime | None:
        """Get last_fetched as datetime."""
        return datetime.fromtimestamp(self.last_fetched) if self.last_fetched else None


class ProcessingLogEntry(BaseModel):
    """Model for a processing log entry."""

    id: int | None = None
    timestamp: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    action: str
    source_type: str | None = None
    source_id: str | None = None
    details: str | None = None


class HackerNewsItem(BaseModel):
    """Model for a Hacker News item."""

    id: str  # Format: "hn_<object_id>"
    title: str
    author: str | None = None
    story_text: str | None = None  # Content for Ask HN / Show HN posts
    url: str  # HN discussion URL
    external_url: str | None = None  # External link if any
    points: int = 0
    num_comments: int = 0
    created_utc: int
    story_type: str = "story"  # "story", "ask_hn", "show_hn"
    captured_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    content_hash: str | None = None
    relevance_score: float = 0.0
    matched_keywords: list[str] = Field(default_factory=list)
    category: str | None = None
    processed: bool = False
    report_id: str | None = None

    @field_validator("matched_keywords", mode="before")
    @classmethod
    def parse_keywords(cls, v: Any) -> list[str]:
        """Parse keywords from JSON string if needed."""
        if isinstance(v, str):
            try:
                return cast(list[str], json.loads(v))
            except json.JSONDecodeError:
                return []
        return cast(list[str], v) if v else []

    def to_db_dict(self) -> dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "story_text": self.story_text,
            "url": self.url,
            "external_url": self.external_url,
            "points": self.points,
            "num_comments": self.num_comments,
            "created_utc": self.created_utc,
            "story_type": self.story_type,
            "captured_at": self.captured_at,
            "content_hash": self.content_hash,
            "relevance_score": self.relevance_score,
            "matched_keywords": json.dumps(self.matched_keywords),
            "category": self.category,
            "processed": 1 if self.processed else 0,
            "report_id": self.report_id,
        }

    @property
    def created_datetime(self) -> datetime:
        """Get created_utc as datetime."""
        return datetime.fromtimestamp(self.created_utc)

    @property
    def hn_url(self) -> str:
        """Get HN discussion URL."""
        item_id = self.id.replace("hn_", "")
        return f"https://news.ycombinator.com/item?id={item_id}"

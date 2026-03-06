"""Relevance scoring algorithms for SignalSift."""

import hashlib
import re
from datetime import datetime
from functools import lru_cache

from signalsift.database.models import HackerNewsItem, RedditThread, Source, YouTubeVideo
from signalsift.database.queries import get_sources_by_type
from signalsift.processing.classification import classify_content
from signalsift.processing.keywords import (
    KeywordMatch,
    KeywordMatcher,
    get_matcher,
)
from signalsift.sources.base import ContentItem

# =============================================================================
# Scoring Constants
# =============================================================================

# Reddit scoring constants
REDDIT_UPVOTE_DIVISOR = 2.5  # Upvotes needed per point
REDDIT_UPVOTE_MAX_POINTS = 20
REDDIT_COMMENT_DIVISOR = 1.33  # Comments needed per point
REDDIT_COMMENT_MAX_POINTS = 15
REDDIT_VIRAL_THRESHOLD = 100  # Upvotes for viral bonus
REDDIT_VIRAL_BONUS = 5
REDDIT_DETAILED_POST_LENGTH = 500  # Characters for "detailed" bonus
REDDIT_DETAILED_POST_BONUS = 5
REDDIT_QUALITY_FLAIR_BONUS = 5
REDDIT_METRICS_BONUS = 5

# YouTube scoring constants
YOUTUBE_VIEW_DIVISOR = 666.67  # Views needed per point (~10k = 15 pts)
YOUTUBE_VIEW_MAX_POINTS = 15
YOUTUBE_LIKE_DIVISOR = 50  # Likes needed per point (~500 = 10 pts)
YOUTUBE_LIKE_MAX_POINTS = 10
YOUTUBE_HIGH_ENGAGEMENT_RATIO = 0.04  # 4% like ratio
YOUTUBE_HIGH_ENGAGEMENT_BONUS = 5
YOUTUBE_OPTIMAL_DURATION_MIN = 600  # 10 minutes
YOUTUBE_OPTIMAL_DURATION_MAX = 2400  # 40 minutes
YOUTUBE_ACCEPTABLE_DURATION_MIN = 300  # 5 minutes
YOUTUBE_ACCEPTABLE_DURATION_MAX = 3600  # 60 minutes
YOUTUBE_OPTIMAL_DURATION_BONUS = 10
YOUTUBE_ACCEPTABLE_DURATION_BONUS = 5
YOUTUBE_TRANSCRIPT_BONUS = 5
YOUTUBE_SUBSTANTIAL_TRANSCRIPT_LENGTH = 2000
YOUTUBE_SUBSTANTIAL_TRANSCRIPT_BONUS = 5

# Hacker News scoring constants
HN_POINTS_DIVISOR = 2  # Points needed per score point
HN_POINTS_MAX_POINTS = 25
HN_COMMENT_DIVISOR = 2  # Comments needed per score point
HN_COMMENT_MAX_POINTS = 15
HN_ASK_BONUS = 10
HN_SHOW_BONUS = 5
HN_HIGH_COMMENT_RATIO = 0.5  # Comments/points ratio
HN_HIGH_COMMENT_RATIO_BONUS = 5

# Source tier bonuses
TIER_1_REDDIT_BONUS = 10
TIER_2_REDDIT_BONUS = 5
TIER_1_YOUTUBE_BONUS = 15
TIER_2_YOUTUBE_BONUS = 8

# Velocity thresholds and bonuses
VELOCITY_VIRAL_THRESHOLD = 50
VELOCITY_VIRAL_BONUS = 15
VELOCITY_HOT_THRESHOLD = 20
VELOCITY_HOT_BONUS = 10
VELOCITY_RISING_THRESHOLD = 10
VELOCITY_RISING_BONUS = 7
VELOCITY_ACTIVE_THRESHOLD = 5
VELOCITY_ACTIVE_BONUS = 4
VELOCITY_MODERATE_THRESHOLD = 2
VELOCITY_MODERATE_BONUS = 2

# Keyword scoring
KEYWORD_MAX_MATCH_COUNT = 3
KEYWORD_MULTIPLIER = 5
KEYWORD_MAX_TOTAL = 35
YOUTUBE_KEYWORD_MAX_MATCH_COUNT = 5
YOUTUBE_KEYWORD_MULTIPLIER = 3

# Engagement velocity calculation
MIN_AGE_HOURS = 0.5  # Minimum age to avoid division issues
COMMENT_WEIGHT = 2  # Comments weighted 2x in engagement


def calculate_engagement_velocity(
    score: int,
    comments: int,
    created_timestamp: int,
    now: datetime | None = None,
) -> float:
    """
    Calculate engagement velocity (engagement per hour).

    Higher velocity = content is gaining traction quickly.

    Args:
        score: Upvotes/points.
        comments: Number of comments.
        created_timestamp: Unix timestamp of creation.
        now: Current time (defaults to now).

    Returns:
        Engagement per hour.
    """
    if now is None:
        now = datetime.now()

    age_hours = (now.timestamp() - created_timestamp) / 3600
    if age_hours < MIN_AGE_HOURS:
        age_hours = MIN_AGE_HOURS  # Minimum 30 minutes to avoid division issues

    total_engagement = score + (comments * COMMENT_WEIGHT)
    velocity = total_engagement / age_hours

    return round(velocity, 2)


def get_velocity_bonus(velocity: float) -> float:
    """
    Calculate score bonus based on engagement velocity.

    Args:
        velocity: Engagement per hour.

    Returns:
        Score bonus (0-15 points).
    """
    if velocity >= VELOCITY_VIRAL_THRESHOLD:
        return VELOCITY_VIRAL_BONUS  # Viral content
    elif velocity >= VELOCITY_HOT_THRESHOLD:
        return VELOCITY_HOT_BONUS  # Hot content
    elif velocity >= VELOCITY_RISING_THRESHOLD:
        return VELOCITY_RISING_BONUS  # Rising content
    elif velocity >= VELOCITY_ACTIVE_THRESHOLD:
        return VELOCITY_ACTIVE_BONUS  # Active content
    elif velocity >= VELOCITY_MODERATE_THRESHOLD:
        return VELOCITY_MODERATE_BONUS  # Moderate activity
    return 0  # Low activity


def contains_numbers(text: str) -> bool:
    """Check if text contains numeric values (potential metrics)."""
    # Look for patterns like percentages, dollar amounts, or standalone numbers
    patterns = [
        r"\d+%",  # Percentages
        r"\$\d+",  # Dollar amounts
        r"\d+k\b",  # Thousands (e.g., "100k")
        r"\d+\s*(views|visitors|users|clicks|sessions)",  # Traffic metrics
        r"increased\s+by\s+\d+",  # Increase mentions
        r"\d+\s*x\b",  # Multipliers (e.g., "3x")
    ]
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


@lru_cache(maxsize=8)
def _get_sources_for_type(source_type: str) -> tuple[Source, ...]:
    """Load all sources for a given type, cached to avoid N+1 queries during batch scoring."""
    return tuple(get_sources_by_type(source_type, enabled_only=False))


def get_source_tier(source_type: str, source_id: str) -> int:
    """Get the tier for a source. Returns 2 (medium) if not found."""
    for source in _get_sources_for_type(source_type):
        if source.source_id == source_id:
            return source.tier
    return 2  # Default to medium tier


def calculate_reddit_score(
    thread: RedditThread,
    keyword_matches: list[KeywordMatch],
    source_tier: int = 2,
) -> float:
    """
    Calculate relevance score for a Reddit thread (0-100 scale).

    Scoring breakdown:
    - Engagement signals: max 40 points
    - Keyword matches: max 35 points
    - Content quality: max 15 points
    - Source tier bonus: max 10 points

    Args:
        thread: The Reddit thread to score.
        keyword_matches: List of keyword matches found in content.
        source_tier: Source tier (1=high, 2=medium, 3=low).

    Returns:
        Relevance score from 0-100.
    """
    score = 0.0

    # === Engagement signals (max 40 points) ===
    score += min(thread.score / REDDIT_UPVOTE_DIVISOR, REDDIT_UPVOTE_MAX_POINTS)
    score += min(thread.num_comments / REDDIT_COMMENT_DIVISOR, REDDIT_COMMENT_MAX_POINTS)

    # Bonus for viral posts
    if thread.score > REDDIT_VIRAL_THRESHOLD:
        score += REDDIT_VIRAL_BONUS

    # === Keyword matches (max 35 points) ===
    keyword_score = 0.0
    for match in keyword_matches:
        keyword_score += (
            min(match.count, KEYWORD_MAX_MATCH_COUNT) * match.weight * KEYWORD_MULTIPLIER
        )
    score += min(keyword_score, KEYWORD_MAX_TOTAL)

    # === Content quality signals (max 15 points) ===
    text = (thread.title or "") + " " + (thread.selftext or "")

    # Has metrics/numbers
    if contains_numbers(text):
        score += REDDIT_METRICS_BONUS

    # Detailed post
    if len(thread.selftext or "") > REDDIT_DETAILED_POST_LENGTH:
        score += REDDIT_DETAILED_POST_BONUS

    # Quality flair
    quality_flairs = ["case study", "success", "strategy", "results", "guide", "tutorial"]
    if thread.flair and any(f in thread.flair.lower() for f in quality_flairs):
        score += REDDIT_QUALITY_FLAIR_BONUS

    # === Source tier bonus (max 10 points) ===
    if source_tier == 1:
        score += TIER_1_REDDIT_BONUS
    elif source_tier == 2:
        score += TIER_2_REDDIT_BONUS
    # Tier 3 gets no bonus

    # === Engagement velocity bonus (max 15 points) ===
    velocity = calculate_engagement_velocity(
        thread.score,
        thread.num_comments,
        thread.created_utc,
    )
    score += get_velocity_bonus(velocity)

    return min(score, 100)


def calculate_youtube_score(
    video: YouTubeVideo,
    keyword_matches: list[KeywordMatch],
    source_tier: int = 1,
) -> float:
    """
    Calculate relevance score for a YouTube video (0-100 scale).

    Scoring breakdown:
    - Engagement signals: max 30 points
    - Keyword matches: max 35 points
    - Content quality: max 20 points
    - Source tier bonus: max 15 points

    Args:
        video: The YouTube video to score.
        keyword_matches: List of keyword matches found in content.
        source_tier: Source tier (1=high, 2=medium, 3=low).

    Returns:
        Relevance score from 0-100.
    """
    score = 0.0

    # === Engagement signals (max 30 points) ===
    score += min(video.view_count / YOUTUBE_VIEW_DIVISOR, YOUTUBE_VIEW_MAX_POINTS)
    score += min(video.like_count / YOUTUBE_LIKE_DIVISOR, YOUTUBE_LIKE_MAX_POINTS)

    # High engagement ratio bonus
    if video.view_count > 0:
        like_ratio = video.like_count / video.view_count
        if like_ratio > YOUTUBE_HIGH_ENGAGEMENT_RATIO:
            score += YOUTUBE_HIGH_ENGAGEMENT_BONUS

    # === Keyword matches (max 35 points) ===
    keyword_score = 0.0
    for match in keyword_matches:
        keyword_score += (
            min(match.count, YOUTUBE_KEYWORD_MAX_MATCH_COUNT)
            * match.weight
            * YOUTUBE_KEYWORD_MULTIPLIER
        )
    score += min(keyword_score, KEYWORD_MAX_TOTAL)

    # === Content quality signals (max 20 points) ===
    # Sweet spot duration: 10-40 minutes
    duration = video.duration_seconds or 0
    if YOUTUBE_OPTIMAL_DURATION_MIN <= duration <= YOUTUBE_OPTIMAL_DURATION_MAX:
        score += YOUTUBE_OPTIMAL_DURATION_BONUS
    elif (
        YOUTUBE_ACCEPTABLE_DURATION_MIN <= duration < YOUTUBE_OPTIMAL_DURATION_MIN
        or YOUTUBE_OPTIMAL_DURATION_MAX < duration <= YOUTUBE_ACCEPTABLE_DURATION_MAX
    ):
        score += YOUTUBE_ACCEPTABLE_DURATION_BONUS

    # Transcript available
    if video.transcript_available:
        score += YOUTUBE_TRANSCRIPT_BONUS

    # Substantial transcript content
    if video.transcript and len(video.transcript) > YOUTUBE_SUBSTANTIAL_TRANSCRIPT_LENGTH:
        score += YOUTUBE_SUBSTANTIAL_TRANSCRIPT_BONUS

    # === Source tier bonus (max 15 points) ===
    if source_tier == 1:
        score += TIER_1_YOUTUBE_BONUS
    elif source_tier == 2:
        score += TIER_2_YOUTUBE_BONUS
    # Tier 3 gets no bonus

    return min(score, 100)


def process_reddit_thread(
    item: ContentItem,
    matcher: KeywordMatcher | None = None,
) -> RedditThread:
    """
    Process a Reddit content item: score it, classify it, and convert to model.

    Args:
        item: ContentItem from the Reddit source.
        matcher: Optional KeywordMatcher instance. Uses default if not provided.

    Returns:
        Fully processed RedditThread model.
    """
    if matcher is None:
        matcher = get_matcher()

    # Find keyword matches
    full_text = item.title + " " + item.content
    matches = matcher.find_matches(full_text)

    # Get source tier
    source_tier = get_source_tier("reddit", item.source_id)

    # Create thread model
    content_hash = hashlib.sha256(full_text.encode()).hexdigest()

    thread = RedditThread(
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
        captured_at=int(datetime.now().timestamp()),
        content_hash=content_hash,
        matched_keywords=matcher.get_matched_keywords(matches),
    )

    # Calculate relevance score
    thread.relevance_score = calculate_reddit_score(thread, matches, source_tier)

    # Classify content
    thread.category = classify_content(full_text, matches)

    return thread


def process_youtube_video(
    item: ContentItem,
    matcher: KeywordMatcher | None = None,
) -> YouTubeVideo:
    """
    Process a YouTube content item: score it, classify it, and convert to model.

    Args:
        item: ContentItem from the YouTube source.
        matcher: Optional KeywordMatcher instance. Uses default if not provided.

    Returns:
        Fully processed YouTubeVideo model.
    """
    if matcher is None:
        matcher = get_matcher()

    # Find keyword matches in title and transcript
    full_text = item.title + " " + (item.content or "")
    matches = matcher.find_matches(full_text)

    # Get source tier
    source_tier = get_source_tier("youtube", item.source_id)

    # Create video model
    content_hash = hashlib.sha256(full_text.encode()).hexdigest()

    video = YouTubeVideo(
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
        captured_at=int(datetime.now().timestamp()),
        content_hash=content_hash,
        matched_keywords=matcher.get_matched_keywords(matches),
    )

    # Calculate relevance score
    video.relevance_score = calculate_youtube_score(video, matches, source_tier)

    # Classify content
    video.category = classify_content(full_text, matches)

    return video


def calculate_hackernews_score(
    points: int,
    num_comments: int,
    created_utc: int,
    keyword_matches: list[KeywordMatch],
    story_type: str = "story",
) -> float:
    """
    Calculate relevance score for a Hacker News item (0-100 scale).

    Scoring breakdown:
    - Engagement signals: max 40 points
    - Keyword matches: max 35 points
    - Content signals: max 15 points
    - Velocity bonus: max 10 points

    Args:
        points: HN points (upvotes).
        num_comments: Number of comments.
        created_utc: Unix timestamp of creation.
        keyword_matches: List of keyword matches found.
        story_type: "story", "ask_hn", or "show_hn".

    Returns:
        Relevance score from 0-100.
    """
    score = 0.0

    # === Engagement signals (max 40 points) ===
    # HN points are harder to get than Reddit upvotes
    score += min(points / HN_POINTS_DIVISOR, HN_POINTS_MAX_POINTS)
    score += min(num_comments / HN_COMMENT_DIVISOR, HN_COMMENT_MAX_POINTS)

    # === Keyword matches (max 35 points) ===
    keyword_score = 0.0
    for match in keyword_matches:
        keyword_score += (
            min(match.count, KEYWORD_MAX_MATCH_COUNT) * match.weight * KEYWORD_MULTIPLIER
        )
    score += min(keyword_score, KEYWORD_MAX_TOTAL)

    # === Content type bonus (max 15 points) ===
    # Ask HN often has valuable discussions
    if story_type == "ask_hn":
        score += HN_ASK_BONUS
    elif story_type == "show_hn":
        score += HN_SHOW_BONUS

    # High comment ratio indicates discussion-worthy content
    if points > 0 and num_comments / points > HN_HIGH_COMMENT_RATIO:
        score += HN_HIGH_COMMENT_RATIO_BONUS

    # === Velocity bonus (max 10 points) ===
    velocity = calculate_engagement_velocity(points, num_comments, created_utc)
    score += min(get_velocity_bonus(velocity), 10)

    return min(score, 100)


def process_hackernews_item(
    item: ContentItem,
    matcher: KeywordMatcher | None = None,
) -> HackerNewsItem:
    """
    Process a Hacker News content item: score it, classify it, and convert to model.

    Args:
        item: ContentItem from the HackerNews source.
        matcher: Optional KeywordMatcher instance. Uses default if not provided.

    Returns:
        Fully processed HackerNewsItem model.
    """
    if matcher is None:
        matcher = get_matcher()

    # Find keyword matches
    full_text = item.title + " " + (item.content or "")
    matches = matcher.find_matches(full_text)

    content_hash = hashlib.sha256(full_text.encode()).hexdigest()

    # Calculate score
    relevance_score = calculate_hackernews_score(
        points=item.metadata.get("points", 0),
        num_comments=item.metadata.get("num_comments", 0),
        created_utc=int(item.created_at.timestamp()),
        keyword_matches=matches,
        story_type=item.metadata.get("story_type", "story"),
    )

    # Classify content
    category = classify_content(full_text, matches)

    return HackerNewsItem(
        id=item.id,
        title=item.title,
        author=item.metadata.get("author"),
        story_text=item.content,
        url=item.url,
        external_url=item.metadata.get("external_url"),
        points=item.metadata.get("points", 0),
        num_comments=item.metadata.get("num_comments", 0),
        created_utc=int(item.created_at.timestamp()),
        story_type=item.metadata.get("story_type", "story"),
        captured_at=int(datetime.now().timestamp()),
        content_hash=content_hash,
        relevance_score=relevance_score,
        matched_keywords=matcher.get_matched_keywords(matches),
        category=category,
    )

"""Tests for scoring algorithms."""

import time

from signalsift.database.models import RedditThread, YouTubeVideo
from signalsift.processing.keywords import KeywordMatch
from signalsift.processing.scoring import (
    calculate_engagement_velocity,
    calculate_hackernews_score,
    calculate_reddit_score,
    calculate_youtube_score,
    contains_numbers,
    get_velocity_bonus,
)


class TestEngagementVelocity:
    """Tests for engagement velocity calculations."""

    def test_high_velocity_content(self) -> None:
        """Test scoring for rapidly-engaging content."""
        # 200 engagement in 1 hour = 200 velocity
        velocity = calculate_engagement_velocity(
            score=100,
            comments=50,
            created_timestamp=int(time.time()) - 3600,  # 1 hour ago
        )
        assert velocity >= 50  # Viral threshold

    def test_low_velocity_content(self) -> None:
        """Test scoring for slowly-engaging content."""
        # 20 engagement in 24 hours = ~0.8 velocity
        velocity = calculate_engagement_velocity(
            score=10,
            comments=5,
            created_timestamp=int(time.time()) - 86400,  # 24 hours ago
        )
        assert velocity < 5

    def test_minimum_age_prevents_division_issues(self) -> None:
        """Ensure very new content uses minimum age."""
        velocity = calculate_engagement_velocity(
            score=10,
            comments=5,
            created_timestamp=int(time.time()),  # Just now
        )
        assert velocity > 0
        assert velocity < 1000  # Should be reasonable

    def test_comments_weighted_more(self) -> None:
        """Test that comments are weighted 2x."""
        # 10 upvotes + 10 comments*2 = 30 total engagement
        velocity = calculate_engagement_velocity(
            score=10,
            comments=10,
            created_timestamp=int(time.time()) - 3600,
        )
        # 30 / 1 hour = 30 velocity
        assert velocity >= 25


class TestVelocityBonus:
    """Tests for velocity bonus calculation."""

    def test_viral_content(self) -> None:
        """Test bonus for viral content (50+ velocity)."""
        assert get_velocity_bonus(100) == 15
        assert get_velocity_bonus(50) == 15

    def test_hot_content(self) -> None:
        """Test bonus for hot content (20-50 velocity)."""
        assert get_velocity_bonus(30) == 10
        assert get_velocity_bonus(20) == 10

    def test_rising_content(self) -> None:
        """Test bonus for rising content (10-20 velocity)."""
        assert get_velocity_bonus(15) == 7
        assert get_velocity_bonus(10) == 7

    def test_low_activity(self) -> None:
        """Test no bonus for low activity."""
        assert get_velocity_bonus(1) == 0
        assert get_velocity_bonus(0) == 0


class TestContainsNumbers:
    """Tests for numeric content detection."""

    def test_percentage(self) -> None:
        """Test detection of percentages."""
        assert contains_numbers("Traffic increased by 50%")
        assert contains_numbers("300% growth")

    def test_dollar_amounts(self) -> None:
        """Test detection of dollar amounts."""
        assert contains_numbers("Made $1000 from ads")
        assert contains_numbers("Revenue hit $50k")

    def test_traffic_metrics(self) -> None:
        """Test detection of traffic metrics."""
        assert contains_numbers("Got 10000 visitors last month")
        assert contains_numbers("50k views on the video")

    def test_multipliers(self) -> None:
        """Test detection of multipliers."""
        assert contains_numbers("Results improved 3x")
        assert contains_numbers("10x growth")

    def test_no_numbers(self) -> None:
        """Test text without metrics."""
        assert not contains_numbers("This is just regular text")
        assert not contains_numbers("SEO strategies for beginners")


class TestRedditScoring:
    """Tests for Reddit thread scoring."""

    def test_high_engagement_thread(self, sample_reddit_thread: RedditThread) -> None:
        """High engagement should yield decent score."""
        matches = [KeywordMatch("organic traffic", "success_signals", 1.5, 2, False)]
        score = calculate_reddit_score(sample_reddit_thread, matches, source_tier=1)
        assert score >= 40  # High quality content

    def test_low_engagement_thread(self) -> None:
        """Low engagement should yield lower score."""
        thread = RedditThread(
            id="low_eng",
            subreddit="SEO",
            title="Test",
            url="/r/SEO/comments/low_eng",
            created_utc=int(time.time()) - 86400,
            captured_at=int(time.time()),
            score=2,
            num_comments=0,
            matched_keywords=[],
        )
        matches: list[KeywordMatch] = []
        score = calculate_reddit_score(thread, matches, source_tier=3)
        assert score < 30

    def test_score_capped_at_100(self, sample_reddit_thread: RedditThread) -> None:
        """Score should never exceed 100."""
        sample_reddit_thread.score = 10000
        sample_reddit_thread.num_comments = 1000
        sample_reddit_thread.selftext = "x" * 1000  # Long content

        matches = [KeywordMatch(f"kw{i}", "success_signals", 1.5, 5, False) for i in range(20)]
        score = calculate_reddit_score(sample_reddit_thread, matches, source_tier=1)
        assert score <= 100

    def test_tier_bonus(self, sample_reddit_thread: RedditThread) -> None:
        """Test source tier affects score."""
        matches: list[KeywordMatch] = []

        score_tier1 = calculate_reddit_score(sample_reddit_thread, matches, source_tier=1)
        score_tier2 = calculate_reddit_score(sample_reddit_thread, matches, source_tier=2)
        score_tier3 = calculate_reddit_score(sample_reddit_thread, matches, source_tier=3)

        assert score_tier1 > score_tier2 > score_tier3

    def test_quality_flair_bonus(self) -> None:
        """Test quality flair adds bonus."""
        thread_with_flair = RedditThread(
            id="flair_test",
            subreddit="SEO",
            title="Test",
            url="/r/SEO/comments/flair_test",
            created_utc=int(time.time()),
            captured_at=int(time.time()),
            matched_keywords=[],
            flair="Case Study",
        )

        thread_no_flair = RedditThread(
            id="no_flair",
            subreddit="SEO",
            title="Test",
            url="/r/SEO/comments/no_flair",
            created_utc=int(time.time()),
            captured_at=int(time.time()),
            matched_keywords=[],
            flair=None,
        )

        score_with = calculate_reddit_score(thread_with_flair, [], source_tier=2)
        score_without = calculate_reddit_score(thread_no_flair, [], source_tier=2)

        assert score_with > score_without


class TestYouTubeScoring:
    """Tests for YouTube video scoring."""

    def test_high_engagement_video(self, sample_youtube_video: YouTubeVideo) -> None:
        """High engagement should yield decent score."""
        matches = [KeywordMatch("SEO", "techniques", 1.0, 3, False)]
        score = calculate_youtube_score(sample_youtube_video, matches, source_tier=1)
        assert score >= 40

    def test_transcript_bonus(self) -> None:
        """Test transcript availability affects score."""
        video_with_transcript = YouTubeVideo(
            id="trans",
            channel_id="UC_test",
            title="Test",
            url="https://youtube.com/watch?v=trans",
            published_at=int(time.time()),
            captured_at=int(time.time()),
            matched_keywords=[],
            transcript="Long transcript content " * 200,
            transcript_available=True,
        )

        video_no_transcript = YouTubeVideo(
            id="no_trans",
            channel_id="UC_test",
            title="Test",
            url="https://youtube.com/watch?v=no_trans",
            published_at=int(time.time()),
            captured_at=int(time.time()),
            matched_keywords=[],
            transcript_available=False,
        )

        score_with = calculate_youtube_score(video_with_transcript, [], source_tier=2)
        score_without = calculate_youtube_score(video_no_transcript, [], source_tier=2)

        assert score_with > score_without


class TestHackerNewsScoring:
    """Tests for Hacker News scoring."""

    def test_high_engagement_story(self) -> None:
        """High engagement should yield high score."""
        matches = [KeywordMatch("SEO tool", "tool_mentions", 1.3, 2, False)]
        score = calculate_hackernews_score(
            points=100,
            num_comments=50,
            created_utc=int(time.time()) - 3600,
            keyword_matches=matches,
            story_type="story",
        )
        assert score >= 50

    def test_ask_hn_bonus(self) -> None:
        """Test Ask HN stories get bonus."""
        matches: list[KeywordMatch] = []

        score_ask = calculate_hackernews_score(
            points=20,
            num_comments=10,
            created_utc=int(time.time()) - 3600,
            keyword_matches=matches,
            story_type="ask_hn",
        )

        score_regular = calculate_hackernews_score(
            points=20,
            num_comments=10,
            created_utc=int(time.time()) - 3600,
            keyword_matches=matches,
            story_type="story",
        )

        assert score_ask > score_regular

    def test_score_capped_at_100(self) -> None:
        """Score should never exceed 100."""
        matches = [KeywordMatch(f"kw{i}", "success_signals", 1.5, 5, False) for i in range(20)]
        score = calculate_hackernews_score(
            points=1000,
            num_comments=500,
            created_utc=int(time.time()),
            keyword_matches=matches,
            story_type="ask_hn",
        )
        assert score <= 100

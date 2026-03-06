"""Tests for trend detection module."""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from signalsift.processing.trends import (
    Trend,
    TrendDetector,
    TrendReport,
    analyze_trends,
    get_declining_topics,
    get_detector,
    get_emerging_topics,
)


class TestTrendDataclass:
    """Tests for Trend dataclass."""

    def test_trend_creation(self):
        """Test creating a Trend instance."""
        trend = Trend(
            topic="seo",
            category="marketing",
            current_count=100,
            previous_count=50,
            change_percent=100.0,
            velocity=14.3,
            direction="rising",
            avg_engagement=500.0,
            sample_titles=["SEO tips", "SEO guide"],
        )

        assert trend.topic == "seo"
        assert trend.current_count == 100
        assert trend.change_percent == 100.0
        assert trend.direction == "rising"
        assert len(trend.sample_titles) == 2

    def test_trend_directions(self):
        """Test different trend directions."""
        for direction in ["rising", "falling", "stable", "new", "gone"]:
            trend = Trend(
                topic="test",
                category="test",
                current_count=10,
                previous_count=10,
                change_percent=0,
                velocity=1.0,
                direction=direction,
                avg_engagement=100,
                sample_titles=[],
            )
            assert trend.direction == direction


class TestTrendReportDataclass:
    """Tests for TrendReport dataclass."""

    def test_trend_report_creation(self):
        """Test creating a TrendReport instance."""
        now = datetime.now()
        report = TrendReport(
            period_start=now - timedelta(days=7),
            period_end=now,
            comparison_start=now - timedelta(days=14),
            comparison_end=now - timedelta(days=7),
            emerging=[],
            declining=[],
            new_topics=[],
            gone_topics=[],
            stable_hot=[],
        )

        assert report.period_end == now
        assert isinstance(report.emerging, list)
        assert isinstance(report.declining, list)


class TestTrendDetectorInit:
    """Tests for TrendDetector initialization."""

    def test_init_creates_instance(self, tmp_path):
        """Test that initialization creates an instance."""
        db_path = tmp_path / "test.db"
        detector = TrendDetector(db_path=db_path)

        assert detector.db_path == db_path
        assert detector.rising_threshold == 1.5
        assert detector.falling_threshold == 0.5

    def test_init_custom_thresholds(self, tmp_path):
        """Test initialization with custom thresholds."""
        db_path = tmp_path / "test.db"
        detector = TrendDetector(
            db_path=db_path,
            rising_threshold=2.0,
            falling_threshold=0.3,
        )

        assert detector.rising_threshold == 2.0
        assert detector.falling_threshold == 0.3

    def test_init_creates_table(self, tmp_path):
        """Test that initialization creates the table."""
        db_path = tmp_path / "test.db"
        TrendDetector(db_path=db_path)

        # Check table exists
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='keyword_trends'"
            )
            assert cursor.fetchone() is not None

    def test_ensure_table_handles_error(self):
        """Test that _ensure_table handles errors gracefully."""
        detector = TrendDetector.__new__(TrendDetector)
        detector.db_path = Path("/nonexistent/path/db.db")

        # Should not raise
        detector._ensure_table()


class TestGetPeriodData:
    """Tests for _get_period_data method."""

    @pytest.fixture
    def detector(self, tmp_path):
        """Create TrendDetector with temp database."""
        db_path = tmp_path / "test.db"
        return TrendDetector(db_path=db_path)

    def test_get_period_data_empty(self, detector):
        """Test getting data from empty database."""
        now = datetime.now()
        data = detector._get_period_data(
            start=now - timedelta(days=7),
            end=now,
        )
        assert data == {}

    def test_get_period_data_with_data(self, detector):
        """Test getting data with records in database."""
        import json

        now = datetime.now()
        start = now - timedelta(days=7)

        # Insert test data
        with sqlite3.connect(detector.db_path) as conn:
            conn.execute(
                """
                INSERT INTO keyword_trends
                (keyword, category, period_start, period_end, mention_count,
                 avg_engagement, sample_titles, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "seo",
                    "marketing",
                    start.isoformat(),
                    now.isoformat(),
                    10,
                    500.0,
                    json.dumps(["Title 1", "Title 2"]),
                    now.isoformat(),
                ),
            )
            conn.commit()

        data = detector._get_period_data(start=start, end=now)

        assert "seo" in data
        assert data["seo"]["count"] == 10
        assert data["seo"]["category"] == "marketing"


class TestAnalyze:
    """Tests for analyze method."""

    @pytest.fixture
    def detector(self, tmp_path):
        """Create TrendDetector with temp database."""
        db_path = tmp_path / "test.db"
        return TrendDetector(db_path=db_path)

    def test_analyze_empty_database(self, detector):
        """Test analyzing empty database."""
        report = detector.analyze()

        assert isinstance(report, TrendReport)
        assert report.emerging == []
        assert report.declining == []

    def test_analyze_identifies_rising(self, detector):
        """Test that analyze identifies rising trends using mocked period data."""
        with patch.object(detector, "_get_period_data") as mock_get_data:
            # Mock current period with high counts
            current_data = {
                "seo": {
                    "category": "marketing",
                    "count": 15,
                    "engagement": 200.0,
                    "titles": ["New Title"],
                },
            }
            # Mock comparison period with low counts
            comparison_data = {
                "seo": {
                    "category": "marketing",
                    "count": 5,
                    "engagement": 100.0,
                    "titles": ["Old Title"],
                },
            }

            # First call is current, second is comparison
            mock_get_data.side_effect = [current_data, comparison_data]

            report = detector.analyze(min_mentions=2)

            # Should identify "seo" as rising (15/5 = 3x increase > 1.5 threshold)
            rising_topics = [t.topic for t in report.emerging]
            assert "seo" in rising_topics

    def test_analyze_identifies_falling(self, detector):
        """Test that analyze identifies falling trends using mocked period data."""
        with patch.object(detector, "_get_period_data") as mock_get_data:
            # Mock current period with low counts
            current_data = {
                "keyword_stuffing": {
                    "category": "techniques",
                    "count": 5,
                    "engagement": 50.0,
                    "titles": ["Declining"],
                },
            }
            # Mock comparison period with high counts
            comparison_data = {
                "keyword_stuffing": {
                    "category": "techniques",
                    "count": 20,
                    "engagement": 100.0,
                    "titles": ["Old practice"],
                },
            }

            mock_get_data.side_effect = [current_data, comparison_data]

            report = detector.analyze(min_mentions=2)

            # Should identify as falling (5/20 = 0.25 < 0.5 threshold)
            falling_topics = [t.topic for t in report.declining]
            assert "keyword_stuffing" in falling_topics

    def test_analyze_identifies_new_topics(self, detector):
        """Test that analyze identifies new topics using mocked period data."""
        with patch.object(detector, "_get_period_data") as mock_get_data:
            # Mock current period with data
            current_data = {
                "ai_seo": {
                    "category": "ai",
                    "count": 10,
                    "engagement": 300.0,
                    "titles": ["AI SEO is new"],
                },
            }
            # Mock comparison period with no data
            comparison_data = {}

            mock_get_data.side_effect = [current_data, comparison_data]

            report = detector.analyze(min_mentions=2)

            new_topics = [t.topic for t in report.new_topics]
            assert "ai_seo" in new_topics


class TestGetEmergingTopics:
    """Tests for get_emerging_topics method."""

    @pytest.fixture
    def detector(self, tmp_path):
        """Create TrendDetector with temp database."""
        db_path = tmp_path / "test.db"
        return TrendDetector(db_path=db_path)

    def test_get_emerging_topics_empty(self, detector):
        """Test getting emerging topics from empty database."""
        topics = detector.get_emerging_topics()
        assert topics == []

    def test_get_emerging_topics_filters_by_change(self, detector):
        """Test that emerging topics are filtered by min_change."""
        with patch.object(detector, "analyze") as mock_analyze:
            mock_analyze.return_value = TrendReport(
                period_start=datetime.now() - timedelta(days=7),
                period_end=datetime.now(),
                comparison_start=datetime.now() - timedelta(days=14),
                comparison_end=datetime.now() - timedelta(days=7),
                emerging=[
                    Trend("topic1", "cat", 100, 50, 100.0, 10, "rising", 500, []),
                    Trend("topic2", "cat", 60, 50, 20.0, 8, "rising", 400, []),
                ],
                declining=[],
                new_topics=[],
                gone_topics=[],
                stable_hot=[],
            )

            topics = detector.get_emerging_topics(days=7, min_change=50.0)

            # Only topic1 has >= 50% change
            assert len(topics) == 1
            assert topics[0].topic == "topic1"


class TestGetDecliningTopics:
    """Tests for get_declining_topics method."""

    @pytest.fixture
    def detector(self, tmp_path):
        """Create TrendDetector with temp database."""
        db_path = tmp_path / "test.db"
        return TrendDetector(db_path=db_path)

    def test_get_declining_topics_empty(self, detector):
        """Test getting declining topics from empty database."""
        topics = detector.get_declining_topics()
        assert topics == []

    def test_get_declining_topics_filters_by_change(self, detector):
        """Test that declining topics are filtered by max_change."""
        with patch.object(detector, "analyze") as mock_analyze:
            mock_analyze.return_value = TrendReport(
                period_start=datetime.now() - timedelta(days=7),
                period_end=datetime.now(),
                comparison_start=datetime.now() - timedelta(days=14),
                comparison_end=datetime.now() - timedelta(days=7),
                emerging=[],
                declining=[
                    Trend("topic1", "cat", 10, 100, -90.0, 1, "falling", 50, []),
                    Trend("topic2", "cat", 80, 100, -20.0, 10, "falling", 400, []),
                ],
                new_topics=[],
                gone_topics=[],
                stable_hot=[],
            )

            topics = detector.get_declining_topics(days=7, max_change=-30.0)

            # Only topic1 has <= -30% change
            assert len(topics) == 1
            assert topics[0].topic == "topic1"


class TestCalculateVelocity:
    """Tests for calculate_velocity method."""

    @pytest.fixture
    def detector(self, tmp_path):
        """Create TrendDetector with temp database."""
        db_path = tmp_path / "test.db"
        return TrendDetector(db_path=db_path)

    def test_calculate_velocity_no_data(self, detector):
        """Test velocity calculation with no data."""
        velocity = detector.calculate_velocity("unknown_keyword")
        assert velocity == 0.0

    def test_calculate_velocity_with_data(self, detector):
        """Test velocity calculation with data using mocked period data."""
        with patch.object(detector, "_get_period_data") as mock_get_data:
            mock_get_data.return_value = {
                "seo": {"category": "marketing", "count": 70, "engagement": 100.0, "titles": []},
            }

            velocity = detector.calculate_velocity("seo", days=7)

            assert velocity == 10.0


class TestModuleFunctions:
    """Tests for module-level functions."""

    def test_get_detector_returns_instance(self):
        """Test that get_detector returns a TrendDetector."""
        import signalsift.processing.trends as trends_module

        # Reset module-level instance
        trends_module._default_detector = None

        with patch.object(TrendDetector, "_ensure_table"):
            detector = get_detector()
            assert isinstance(detector, TrendDetector)

    def test_get_detector_caches_instance(self):
        """Test that get_detector caches the instance."""
        import signalsift.processing.trends as trends_module

        # Reset module-level instance
        trends_module._default_detector = None

        with patch.object(TrendDetector, "_ensure_table"):
            detector1 = get_detector()
            detector2 = get_detector()

            assert detector1 is detector2

    def test_analyze_trends_function(self):
        """Test analyze_trends convenience function."""
        mock_report = TrendReport(
            period_start=datetime.now() - timedelta(days=7),
            period_end=datetime.now(),
            comparison_start=datetime.now() - timedelta(days=14),
            comparison_end=datetime.now() - timedelta(days=7),
            emerging=[],
            declining=[],
            new_topics=[],
            gone_topics=[],
            stable_hot=[],
        )

        with (
            patch.object(TrendDetector, "analyze", return_value=mock_report),
            patch.object(TrendDetector, "_ensure_table"),
        ):
            import signalsift.processing.trends as trends_module

            trends_module._default_detector = None

            report = analyze_trends()

            assert isinstance(report, TrendReport)

    def test_get_emerging_topics_function(self):
        """Test get_emerging_topics convenience function."""
        with (
            patch.object(TrendDetector, "get_emerging_topics", return_value=[]),
            patch.object(TrendDetector, "_ensure_table"),
        ):
            import signalsift.processing.trends as trends_module

            trends_module._default_detector = None

            topics = get_emerging_topics(days=7)

            assert topics == []

    def test_get_declining_topics_function(self):
        """Test get_declining_topics convenience function."""
        with (
            patch.object(TrendDetector, "get_declining_topics", return_value=[]),
            patch.object(TrendDetector, "_ensure_table"),
        ):
            import signalsift.processing.trends as trends_module

            trends_module._default_detector = None

            topics = get_declining_topics(days=7)

            assert topics == []

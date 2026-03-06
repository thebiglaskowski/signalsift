"""Tests for the status command."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from signalsift.cli.main import cli


class TestStatusCommand:
    """Tests for the status command."""

    @pytest.fixture
    def mock_settings(self) -> MagicMock:
        """Create mock settings object."""
        settings = MagicMock()
        settings.database.path = Path("/tmp/test_signalsift.db")
        settings.has_reddit_credentials.return_value = True
        settings.has_youtube_credentials.return_value = True
        return settings

    @pytest.fixture
    def mock_cache_stats(self) -> dict:
        """Create mock cache statistics."""
        return {
            "reddit_total": 150,
            "reddit_unprocessed": 25,
            "reddit_last_scan": datetime(2024, 1, 15, 10, 30),
            "youtube_total": 50,
            "youtube_unprocessed": 10,
            "youtube_last_scan": datetime(2024, 1, 15, 11, 0),
            "reddit_sources": 10,
            "reddit_sources_enabled": 8,
            "youtube_sources": 5,
            "youtube_sources_enabled": 4,
            "reports_total": 3,
            "last_report_date": datetime(2024, 1, 14),
            "last_report_path": "reports/2024-01-14-signalsift.md",
        }

    @pytest.fixture
    def mock_latest_report(self) -> MagicMock:
        """Create mock latest report object."""
        report = MagicMock()
        report.created_at = datetime(2024, 1, 14, 9, 0)
        report.output_path = "reports/2024-01-14-signalsift.md"
        return report

    def test_status_displays_database_info(
        self, mock_settings: MagicMock, mock_cache_stats: dict, mock_latest_report: MagicMock
    ) -> None:
        """Test that status displays database information."""
        runner = CliRunner()

        with (
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.cli.main.setup_logging"),
            patch("signalsift.config.get_settings", return_value=mock_settings),
            patch("signalsift.cli.status.get_cache_stats", return_value=mock_cache_stats),
            patch("signalsift.cli.status.get_latest_report", return_value=mock_latest_report),
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat") as mock_stat,
        ):
            mock_stat.return_value.st_size = 1024 * 1024  # 1 MB
            result = runner.invoke(cli, ["status"])

            assert result.exit_code == 0
            assert "SignalSift Status" in result.output
            assert "Database:" in result.output
            assert "test_signalsift.db" in result.output

    def test_status_displays_reddit_stats(
        self, mock_settings: MagicMock, mock_cache_stats: dict, mock_latest_report: MagicMock
    ) -> None:
        """Test that status displays Reddit statistics."""
        runner = CliRunner()

        with (
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.cli.main.setup_logging"),
            patch("signalsift.config.get_settings", return_value=mock_settings),
            patch("signalsift.cli.status.get_cache_stats", return_value=mock_cache_stats),
            patch("signalsift.cli.status.get_latest_report", return_value=mock_latest_report),
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat") as mock_stat,
        ):
            mock_stat.return_value.st_size = 1024
            result = runner.invoke(cli, ["status"])

            assert result.exit_code == 0
            assert "Reddit Threads" in result.output
            assert "150" in result.output  # reddit_total
            assert "25" in result.output  # reddit_unprocessed

    def test_status_displays_youtube_stats(
        self, mock_settings: MagicMock, mock_cache_stats: dict, mock_latest_report: MagicMock
    ) -> None:
        """Test that status displays YouTube statistics."""
        runner = CliRunner()

        with (
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.cli.main.setup_logging"),
            patch("signalsift.config.get_settings", return_value=mock_settings),
            patch("signalsift.cli.status.get_cache_stats", return_value=mock_cache_stats),
            patch("signalsift.cli.status.get_latest_report", return_value=mock_latest_report),
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat") as mock_stat,
        ):
            mock_stat.return_value.st_size = 1024
            result = runner.invoke(cli, ["status"])

            assert result.exit_code == 0
            assert "YouTube Videos" in result.output
            assert "50" in result.output  # youtube_total
            assert "10" in result.output  # youtube_unprocessed

    def test_status_displays_sources_configured(
        self, mock_settings: MagicMock, mock_cache_stats: dict, mock_latest_report: MagicMock
    ) -> None:
        """Test that status displays source configuration."""
        runner = CliRunner()

        with (
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.cli.main.setup_logging"),
            patch("signalsift.config.get_settings", return_value=mock_settings),
            patch("signalsift.cli.status.get_cache_stats", return_value=mock_cache_stats),
            patch("signalsift.cli.status.get_latest_report", return_value=mock_latest_report),
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat") as mock_stat,
        ):
            mock_stat.return_value.st_size = 1024
            result = runner.invoke(cli, ["status"])

            assert result.exit_code == 0
            assert "Sources Configured" in result.output
            assert "Reddit" in result.output
            assert "YouTube" in result.output
            # Check enabled vs total sources
            assert "8" in result.output  # reddit_sources_enabled
            assert "4" in result.output  # youtube_sources_enabled

    def test_status_displays_report_info(
        self, mock_settings: MagicMock, mock_cache_stats: dict, mock_latest_report: MagicMock
    ) -> None:
        """Test that status displays report information."""
        runner = CliRunner()

        with (
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.cli.main.setup_logging"),
            patch("signalsift.config.get_settings", return_value=mock_settings),
            patch("signalsift.cli.status.get_cache_stats", return_value=mock_cache_stats),
            patch("signalsift.cli.status.get_latest_report", return_value=mock_latest_report),
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat") as mock_stat,
        ):
            mock_stat.return_value.st_size = 1024
            result = runner.invoke(cli, ["status"])

            assert result.exit_code == 0
            assert "Reports Generated:" in result.output
            assert "3" in result.output  # reports_total
            assert "Last Report:" in result.output
            assert "2024-01-14" in result.output

    def test_status_no_reports_generated(
        self, mock_settings: MagicMock, mock_cache_stats: dict
    ) -> None:
        """Test status display when no reports have been generated."""
        runner = CliRunner()
        mock_cache_stats["reports_total"] = 0

        with (
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.cli.main.setup_logging"),
            patch("signalsift.config.get_settings", return_value=mock_settings),
            patch("signalsift.cli.status.get_cache_stats", return_value=mock_cache_stats),
            patch("signalsift.cli.status.get_latest_report", return_value=None),
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat") as mock_stat,
        ):
            mock_stat.return_value.st_size = 1024
            result = runner.invoke(cli, ["status"])

            assert result.exit_code == 0
            assert "No reports generated yet" in result.output

    def test_status_displays_reddit_credentials_status(
        self, mock_settings: MagicMock, mock_cache_stats: dict, mock_latest_report: MagicMock
    ) -> None:
        """Test that status displays Reddit credentials status."""
        runner = CliRunner()

        # Test with credentials configured
        with (
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.cli.main.setup_logging"),
            patch("signalsift.config.get_settings", return_value=mock_settings),
            patch("signalsift.cli.status.get_cache_stats", return_value=mock_cache_stats),
            patch("signalsift.cli.status.get_latest_report", return_value=mock_latest_report),
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat") as mock_stat,
        ):
            mock_stat.return_value.st_size = 1024
            result = runner.invoke(cli, ["status"])

            assert result.exit_code == 0
            assert "API Credentials:" in result.output
            assert "Reddit credentials configured" in result.output

    def test_status_displays_reddit_credentials_not_configured(
        self, mock_settings: MagicMock, mock_cache_stats: dict, mock_latest_report: MagicMock
    ) -> None:
        """Test status when Reddit credentials are not configured."""
        runner = CliRunner()
        mock_settings.has_reddit_credentials.return_value = False

        with (
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.cli.main.setup_logging"),
            patch("signalsift.config.get_settings", return_value=mock_settings),
            patch("signalsift.cli.status.get_cache_stats", return_value=mock_cache_stats),
            patch("signalsift.cli.status.get_latest_report", return_value=mock_latest_report),
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat") as mock_stat,
        ):
            mock_stat.return_value.st_size = 1024
            result = runner.invoke(cli, ["status"])

            assert result.exit_code == 0
            assert "Reddit credentials not configured" in result.output

    def test_status_displays_youtube_credentials_status(
        self, mock_settings: MagicMock, mock_cache_stats: dict, mock_latest_report: MagicMock
    ) -> None:
        """Test that status displays YouTube credentials status."""
        runner = CliRunner()

        with (
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.cli.main.setup_logging"),
            patch("signalsift.config.get_settings", return_value=mock_settings),
            patch("signalsift.cli.status.get_cache_stats", return_value=mock_cache_stats),
            patch("signalsift.cli.status.get_latest_report", return_value=mock_latest_report),
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat") as mock_stat,
        ):
            mock_stat.return_value.st_size = 1024
            result = runner.invoke(cli, ["status"])

            assert result.exit_code == 0
            assert "YouTube API key configured" in result.output

    def test_status_displays_youtube_credentials_not_configured(
        self, mock_settings: MagicMock, mock_cache_stats: dict, mock_latest_report: MagicMock
    ) -> None:
        """Test status when YouTube credentials are not configured."""
        runner = CliRunner()
        mock_settings.has_youtube_credentials.return_value = False

        with (
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.cli.main.setup_logging"),
            patch("signalsift.config.get_settings", return_value=mock_settings),
            patch("signalsift.cli.status.get_cache_stats", return_value=mock_cache_stats),
            patch("signalsift.cli.status.get_latest_report", return_value=mock_latest_report),
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat") as mock_stat,
        ):
            mock_stat.return_value.st_size = 1024
            result = runner.invoke(cli, ["status"])

            assert result.exit_code == 0
            assert "YouTube API key not configured" in result.output

    def test_status_with_never_scanned(
        self, mock_settings: MagicMock, mock_cache_stats: dict, mock_latest_report: MagicMock
    ) -> None:
        """Test status when sources have never been scanned."""
        runner = CliRunner()
        mock_cache_stats["reddit_last_scan"] = None
        mock_cache_stats["youtube_last_scan"] = None

        with (
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.cli.main.setup_logging"),
            patch("signalsift.config.get_settings", return_value=mock_settings),
            patch("signalsift.cli.status.get_cache_stats", return_value=mock_cache_stats),
            patch("signalsift.cli.status.get_latest_report", return_value=mock_latest_report),
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat") as mock_stat,
        ):
            mock_stat.return_value.st_size = 1024
            result = runner.invoke(cli, ["status"])

            assert result.exit_code == 0
            assert "Never" in result.output

    def test_status_with_verbose_flag(
        self, mock_settings: MagicMock, mock_cache_stats: dict, mock_latest_report: MagicMock
    ) -> None:
        """Test that verbose flag is handled by status command."""
        runner = CliRunner()

        with (
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.cli.main.setup_logging"),
            patch("signalsift.config.get_settings", return_value=mock_settings),
            patch("signalsift.cli.status.get_cache_stats", return_value=mock_cache_stats),
            patch("signalsift.cli.status.get_latest_report", return_value=mock_latest_report),
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat") as mock_stat,
        ):
            mock_stat.return_value.st_size = 1024
            result = runner.invoke(cli, ["--verbose", "status"])

            # Should still work successfully
            assert result.exit_code == 0
            assert "SignalSift Status" in result.output

    def test_status_database_size_formatting(
        self, mock_settings: MagicMock, mock_cache_stats: dict, mock_latest_report: MagicMock
    ) -> None:
        """Test that database size is properly formatted."""
        runner = CliRunner()

        with (
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.cli.main.setup_logging"),
            patch("signalsift.config.get_settings", return_value=mock_settings),
            patch("signalsift.cli.status.get_cache_stats", return_value=mock_cache_stats),
            patch("signalsift.cli.status.get_latest_report", return_value=mock_latest_report),
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat") as mock_stat,
        ):
            mock_stat.return_value.st_size = 1024 * 1024 * 5  # 5 MB
            result = runner.invoke(cli, ["status"])

            assert result.exit_code == 0
            assert "Size:" in result.output

    def test_status_database_not_exists(
        self, mock_settings: MagicMock, mock_cache_stats: dict, mock_latest_report: MagicMock
    ) -> None:
        """Test status when database file doesn't exist yet."""
        runner = CliRunner()

        with (
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.cli.main.setup_logging"),
            patch("signalsift.config.get_settings", return_value=mock_settings),
            patch("signalsift.cli.status.get_cache_stats", return_value=mock_cache_stats),
            patch("signalsift.cli.status.get_latest_report", return_value=mock_latest_report),
            patch.object(Path, "exists", return_value=False),
        ):
            result = runner.invoke(cli, ["status"])

            # Should still display status, just with 0 size
            assert result.exit_code == 0
            assert "SignalSift Status" in result.output

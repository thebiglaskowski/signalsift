"""Tests for main CLI entry point and basic commands."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from signalsift import __version__
from signalsift.cli.main import cli


class TestCLIInitialization:
    """Tests for CLI initialization and basic functionality."""

    def test_cli_version(self) -> None:
        """Test that --version shows the correct version."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert __version__ in result.output
        assert "signalsift" in result.output.lower()

    def test_cli_help(self) -> None:
        """Test that --help shows usage information."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "SignalSift" in result.output
        assert "Personal community intelligence tool" in result.output
        assert "Commands:" in result.output
        # Check that main commands are listed
        assert "scan" in result.output
        assert "report" in result.output
        assert "status" in result.output
        assert "sources" in result.output

    def test_cli_verbose_flag(self) -> None:
        """Test that verbose flag is properly handled."""
        runner = CliRunner()
        mock_stats = {
            "reddit_total": 0,
            "reddit_unprocessed": 0,
            "reddit_last_scan": None,
            "youtube_total": 0,
            "youtube_unprocessed": 0,
            "youtube_last_scan": None,
            "reddit_sources": 0,
            "reddit_sources_enabled": 0,
            "youtube_sources": 0,
            "youtube_sources_enabled": 0,
            "reports_total": 0,
        }
        with (
            patch("signalsift.cli.main.setup_logging") as mock_logging,
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.cli.status.get_cache_stats", return_value=mock_stats),
            patch("signalsift.cli.status.get_latest_report", return_value=None),
            patch("signalsift.config.get_settings") as mock_settings,
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat") as mock_stat,
        ):
            mock_settings.return_value.database.path = Path("/tmp/test.db")
            mock_settings.return_value.has_reddit_credentials.return_value = False
            mock_settings.return_value.has_youtube_credentials.return_value = False
            mock_stat.return_value.st_size = 1024
            runner.invoke(cli, ["--verbose", "status"])

            # Check logging was configured with DEBUG
            mock_logging.assert_called_once()
            call_args = mock_logging.call_args
            assert call_args[1]["level"] == "DEBUG"

    def test_cli_no_verbose_flag(self) -> None:
        """Test that logging defaults to INFO without verbose flag."""
        runner = CliRunner()
        mock_stats = {
            "reddit_total": 0,
            "reddit_unprocessed": 0,
            "reddit_last_scan": None,
            "youtube_total": 0,
            "youtube_unprocessed": 0,
            "youtube_last_scan": None,
            "reddit_sources": 0,
            "reddit_sources_enabled": 0,
            "youtube_sources": 0,
            "youtube_sources_enabled": 0,
            "reports_total": 0,
        }
        with (
            patch("signalsift.cli.main.setup_logging") as mock_logging,
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.cli.status.get_cache_stats", return_value=mock_stats),
            patch("signalsift.cli.status.get_latest_report", return_value=None),
            patch("signalsift.config.get_settings") as mock_settings,
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat") as mock_stat,
        ):
            mock_settings.return_value.database.path = Path("/tmp/test.db")
            mock_settings.return_value.has_reddit_credentials.return_value = False
            mock_settings.return_value.has_youtube_credentials.return_value = False
            mock_stat.return_value.st_size = 1024
            runner.invoke(cli, ["status"])

            # Check logging was configured with INFO
            mock_logging.assert_called_once()
            call_args = mock_logging.call_args
            assert call_args[1]["level"] == "INFO"


class TestDatabaseInitialization:
    """Tests for database initialization during CLI startup."""

    def test_database_auto_init_when_missing(self) -> None:
        """Test that database is automatically initialized if it doesn't exist."""
        runner = CliRunner()
        mock_stats = {
            "reddit_total": 0,
            "reddit_unprocessed": 0,
            "reddit_last_scan": None,
            "youtube_total": 0,
            "youtube_unprocessed": 0,
            "youtube_last_scan": None,
            "reddit_sources": 0,
            "reddit_sources_enabled": 0,
            "youtube_sources": 0,
            "youtube_sources_enabled": 0,
            "reports_total": 0,
        }
        # Need to invoke a real command (not --help) to trigger the CLI callback
        with (
            patch("signalsift.cli.main.database_exists", return_value=False),
            patch("signalsift.cli.main.initialize_database") as mock_init,
            patch("signalsift.cli.main.setup_logging"),
            patch("signalsift.cli.status.get_cache_stats", return_value=mock_stats),
            patch("signalsift.cli.status.get_latest_report", return_value=None),
            patch("signalsift.config.get_settings") as mock_settings,
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat") as mock_stat,
        ):
            mock_settings.return_value.database.path = Path("/tmp/test.db")
            mock_settings.return_value.has_reddit_credentials.return_value = False
            mock_settings.return_value.has_youtube_credentials.return_value = False
            mock_stat.return_value.st_size = 1024
            result = runner.invoke(cli, ["status"])

            # Database should be initialized
            mock_init.assert_called_once_with(populate_defaults=True)
            assert "Database initialized" in result.output

    def test_database_not_reinit_when_exists(self) -> None:
        """Test that database is not reinitialized if it already exists."""
        runner = CliRunner()
        mock_stats = {
            "reddit_total": 0,
            "reddit_unprocessed": 0,
            "reddit_last_scan": None,
            "youtube_total": 0,
            "youtube_unprocessed": 0,
            "youtube_last_scan": None,
            "reddit_sources": 0,
            "reddit_sources_enabled": 0,
            "youtube_sources": 0,
            "youtube_sources_enabled": 0,
            "reports_total": 0,
        }
        with (
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.cli.main.initialize_database") as mock_init,
            patch("signalsift.cli.main.setup_logging"),
            patch("signalsift.cli.status.get_cache_stats", return_value=mock_stats),
            patch("signalsift.cli.status.get_latest_report", return_value=None),
            patch("signalsift.config.get_settings") as mock_settings,
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat") as mock_stat,
        ):
            mock_settings.return_value.database.path = Path("/tmp/test.db")
            mock_settings.return_value.has_reddit_credentials.return_value = False
            mock_settings.return_value.has_youtube_credentials.return_value = False
            mock_stat.return_value.st_size = 1024
            result = runner.invoke(cli, ["status"])

            # Database should NOT be initialized
            mock_init.assert_not_called()
            assert "Database initialized" not in result.output


class TestInitCommand:
    """Tests for the init command."""

    def test_init_new_database(self) -> None:
        """Test initializing a new database."""
        runner = CliRunner()
        with (
            patch("signalsift.cli.main.database_exists", return_value=False),
            patch("signalsift.cli.main.initialize_database") as mock_init,
            patch("signalsift.cli.main.setup_logging"),
        ):
            result = runner.invoke(cli, ["init"])

            assert result.exit_code == 0
            # Called in both main CLI and init command
            assert mock_init.call_count >= 1
            assert "Database initialized" in result.output
            assert "default sources and keywords" in result.output

    def test_init_reset_existing_database_confirmed(self) -> None:
        """Test resetting an existing database with confirmation."""
        runner = CliRunner()
        with (
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.database.connection.reset_database") as mock_reset,
            patch("signalsift.cli.main.setup_logging"),
        ):
            # Simulate user confirming the reset
            result = runner.invoke(cli, ["init"], input="y\n")

            assert result.exit_code == 0
            mock_reset.assert_called_once()
            assert "reset" in result.output.lower()

    def test_init_reset_existing_database_cancelled(self) -> None:
        """Test cancelling database reset."""
        runner = CliRunner()
        with (
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.database.connection.reset_database") as mock_reset,
            patch("signalsift.cli.main.setup_logging"),
        ):
            # Simulate user cancelling the reset
            result = runner.invoke(cli, ["init"], input="n\n")

            assert result.exit_code == 0
            mock_reset.assert_not_called()
            assert "Cancelled" in result.output


class TestMigrateCommand:
    """Tests for the migrate command."""

    def test_migrate_check_flag(self) -> None:
        """Test migration status check."""
        runner = CliRunner()
        mock_status = {
            "current_version": 3,
            "latest_version": 5,
            "applied": 3,
            "pending": 2,
        }

        with (
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.cli.main.setup_logging"),
            patch("signalsift.database.migrations.migration_status", return_value=mock_status),
            patch("signalsift.database.migrations.get_pending_migrations", return_value=[]),
        ):
            result = runner.invoke(cli, ["migrate", "--check"])

            assert result.exit_code == 0
            assert "3" in result.output  # Current version
            assert "5" in result.output  # Latest version

    def test_migrate_check_shows_pending_migrations(self) -> None:
        """Test that pending migrations are displayed in check mode."""
        runner = CliRunner()
        mock_status = {
            "current_version": 1,
            "latest_version": 3,
            "applied": 1,
            "pending": 2,
        }

        mock_migration_1 = MagicMock()
        mock_migration_1.version = 2
        mock_migration_1.name = "add_hackernews_support"

        mock_migration_2 = MagicMock()
        mock_migration_2.version = 3
        mock_migration_2.name = "add_competitive_tracking"

        with (
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.cli.main.setup_logging"),
            patch("signalsift.database.migrations.migration_status", return_value=mock_status),
            patch(
                "signalsift.database.migrations.get_pending_migrations",
                return_value=[mock_migration_1, mock_migration_2],
            ),
        ):
            result = runner.invoke(cli, ["migrate", "--check"])

            assert result.exit_code == 0
            assert "Pending migrations:" in result.output
            assert "add_hackernews_support" in result.output
            assert "add_competitive_tracking" in result.output

    def test_migrate_run_migrations(self) -> None:
        """Test running pending migrations."""
        runner = CliRunner()
        with (
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.cli.main.setup_logging"),
            patch("signalsift.database.migrations.migrate", return_value=2) as mock_migrate,
        ):
            result = runner.invoke(cli, ["migrate"])

            assert result.exit_code == 0
            mock_migrate.assert_called_once_with(target_version=None)
            assert "2" in result.output  # 2 migrations applied

    def test_migrate_no_pending_migrations(self) -> None:
        """Test migrate when database is already up to date."""
        runner = CliRunner()
        with (
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.cli.main.setup_logging"),
            patch("signalsift.database.migrations.migrate", return_value=0),
        ):
            result = runner.invoke(cli, ["migrate"])

            assert result.exit_code == 0
            assert "up to date" in result.output.lower()

    def test_migrate_to_specific_version(self) -> None:
        """Test migrating to a specific version."""
        runner = CliRunner()
        with (
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.cli.main.setup_logging"),
            patch("signalsift.database.migrations.migrate", return_value=1) as mock_migrate,
        ):
            result = runner.invoke(cli, ["migrate", "--version", "5"])

            assert result.exit_code == 0
            mock_migrate.assert_called_once_with(target_version=5)


class TestCommandRegistration:
    """Tests for command group registration."""

    def test_all_commands_registered(self) -> None:
        """Test that all expected commands are registered with the CLI."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        # Check all main commands are present
        expected_commands = [
            "scan",
            "report",
            "status",
            "sources",
            "keywords",
            "cache",
            "init",
            "migrate",
        ]

        for cmd in expected_commands:
            assert cmd in result.output, f"Command '{cmd}' not found in CLI help"

    def test_command_groups_have_subcommands(self) -> None:
        """Test that command groups show their subcommands."""
        runner = CliRunner()

        # Test sources subcommands
        with (
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.cli.main.setup_logging"),
        ):
            result = runner.invoke(cli, ["sources", "--help"])
            assert result.exit_code == 0
            assert "list" in result.output
            assert "add" in result.output


class TestCLIErrorHandling:
    """Tests for CLI error handling."""

    def test_invalid_command(self) -> None:
        """Test handling of invalid commands."""
        runner = CliRunner()
        result = runner.invoke(cli, ["invalid-command"])

        assert result.exit_code != 0
        assert "Error" in result.output or "No such command" in result.output

    def test_missing_required_argument(self) -> None:
        """Test handling of missing required arguments."""
        runner = CliRunner()
        with (
            patch("signalsift.cli.main.database_exists", return_value=True),
            patch("signalsift.cli.main.setup_logging"),
        ):
            # sources add requires two arguments
            result = runner.invoke(cli, ["sources", "add"])

            assert result.exit_code != 0

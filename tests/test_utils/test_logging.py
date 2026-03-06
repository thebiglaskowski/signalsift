"""Tests for logging utility module."""

import contextlib
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import signalsift.utils.logging as logging_module
from signalsift.utils.logging import get_logger, set_log_level, setup_logging


class TestSetupLogging:
    """Tests for setup_logging function."""

    @pytest.fixture(autouse=True)
    def reset_logging_state(self):
        """Reset module state before each test."""
        logging_module._initialized = False
        logging_module._loggers.clear()
        # Remove any existing handlers from signalsift logger
        root = logging.getLogger("signalsift")
        root.handlers = []
        yield
        # Cleanup after
        logging_module._initialized = False
        logging_module._loggers.clear()
        root.handlers = []

    def test_setup_logging_initializes(self, tmp_path):
        """Test that setup_logging initializes logging."""
        log_file = tmp_path / "test.log"
        setup_logging(log_file=log_file)

        assert logging_module._initialized is True

    def test_setup_logging_creates_handlers(self, tmp_path):
        """Test that setup_logging creates handlers."""
        log_file = tmp_path / "test.log"
        setup_logging(log_file=log_file)

        root_logger = logging.getLogger("signalsift")
        # Should have console and file handlers
        assert len(root_logger.handlers) >= 2

    def test_setup_logging_skips_if_initialized(self, tmp_path):
        """Test that setup_logging doesn't reinitialize."""
        log_file = tmp_path / "test.log"
        setup_logging(log_file=log_file)

        # Get handler count after first setup
        root_logger = logging.getLogger("signalsift")
        handler_count = len(root_logger.handlers)

        # Try to setup again
        setup_logging(log_file=log_file)

        # Should not add more handlers
        assert len(root_logger.handlers) == handler_count

    def test_setup_logging_creates_default_directory(self):
        """Test that setup_logging creates log directory when no file specified."""
        with patch("signalsift.utils.logging.LOGS_DIR") as mock_dir:
            mock_dir.mkdir = MagicMock()
            mock_dir.__truediv__ = MagicMock(return_value=Path("/fake/signalsift.log"))

            # Reset state to allow initialization
            logging_module._initialized = False

            # This will try to use default directory
            with contextlib.suppress(Exception):
                setup_logging()  # We just want to test the mkdir call

            mock_dir.mkdir.assert_called_once()

    def test_setup_logging_with_custom_log_file(self, tmp_path):
        """Test setup_logging with custom log file path."""
        subdir = tmp_path / "subdir"
        log_file = subdir / "custom.log"

        setup_logging(log_file=log_file)

        # Directory should be created
        assert subdir.exists()

    def test_setup_logging_sets_level(self, tmp_path):
        """Test that setup_logging sets the correct level."""
        log_file = tmp_path / "test.log"
        setup_logging(level="DEBUG", log_file=log_file)

        root_logger = logging.getLogger("signalsift")
        assert root_logger.level == logging.DEBUG


class TestGetLogger:
    """Tests for get_logger function."""

    @pytest.fixture(autouse=True)
    def reset_logging_state(self):
        """Reset module state before each test."""
        logging_module._initialized = False
        logging_module._loggers.clear()
        yield
        logging_module._initialized = False
        logging_module._loggers.clear()

    def test_get_logger_returns_logger(self, tmp_path):
        """Test that get_logger returns a logger instance."""
        # Initialize logging first
        log_file = tmp_path / "test.log"
        setup_logging(log_file=log_file)

        logger = get_logger("test")
        assert isinstance(logger, logging.Logger)

    def test_get_logger_caches_logger(self, tmp_path):
        """Test that get_logger caches loggers."""
        log_file = tmp_path / "test.log"
        setup_logging(log_file=log_file)

        logger1 = get_logger("test")
        logger2 = get_logger("test")

        assert logger1 is logger2

    def test_get_logger_initializes_if_needed(self):
        """Test that get_logger initializes logging if not done."""
        # Reset state
        logging_module._initialized = False

        with patch("signalsift.utils.logging.setup_logging") as mock_setup:
            get_logger("test")
            # setup_logging should have been called
            mock_setup.assert_called_once()

    def test_get_logger_prefixes_name(self, tmp_path):
        """Test that logger names are prefixed correctly."""
        log_file = tmp_path / "test.log"
        setup_logging(log_file=log_file)

        logger = get_logger("mymodule")
        assert logger.name == "signalsift.mymodule"

    def test_get_logger_doesnt_double_prefix(self, tmp_path):
        """Test that already prefixed names aren't double prefixed."""
        log_file = tmp_path / "test.log"
        setup_logging(log_file=log_file)

        logger = get_logger("signalsift.existing")
        assert logger.name == "signalsift.existing"


class TestSetLogLevel:
    """Tests for set_log_level function."""

    @pytest.fixture(autouse=True)
    def reset_logging_state(self, tmp_path):
        """Reset module state and setup logging."""
        logging_module._initialized = False
        logging_module._loggers.clear()
        root = logging.getLogger("signalsift")
        root.handlers = []

        log_file = tmp_path / "test.log"
        setup_logging(log_file=log_file)
        yield
        logging_module._initialized = False
        logging_module._loggers.clear()
        root.handlers = []

    def test_set_log_level_changes_root_level(self):
        """Test that set_log_level changes the root logger level."""
        set_log_level("DEBUG")
        root_logger = logging.getLogger("signalsift")
        assert root_logger.level == logging.DEBUG

        set_log_level("ERROR")
        assert root_logger.level == logging.ERROR

    def test_set_log_level_changes_file_handler(self):
        """Test that set_log_level changes file handler level."""
        set_log_level("DEBUG")

        root_logger = logging.getLogger("signalsift")
        file_handlers = [h for h in root_logger.handlers if isinstance(h, logging.FileHandler)]

        for handler in file_handlers:
            assert handler.level == logging.DEBUG

    def test_set_log_level_case_insensitive(self):
        """Test that log level is case insensitive."""
        set_log_level("debug")
        root_logger = logging.getLogger("signalsift")
        assert root_logger.level == logging.DEBUG

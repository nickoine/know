# Built-in
from __future__ import annotations
from unittest.mock import MagicMock, patch
from typing import TYPE_CHECKING

# External
from django.test import SimpleTestCase
from django.db import models

# Internal
from cmn import DBManager, BaseModel

if TYPE_CHECKING:
    from typing import Optional


class ModelTest(BaseModel):
    """
    Concrete test model for unit testing.

    This model is used exclusively for testing purposes and is not managed
    by Django's migration system (managed = False).
    """

    name = models.CharField(max_length=255)

    class Meta:
        managed = False
        app_label = "test"


class TestClassBase(SimpleTestCase):
    """
    Base test class for unit tests that don't require database access.

    This class provides a consistent testing environment by:
    - Mocking external dependencies and services
    - Setting up common test fixtures and utilities
    - Providing helper assertion methods for logging verification
    - Using proper cleanup mechanisms with addCleanup()

    Inherits from SimpleTestCase since these are true unit tests that
    don't need database connections or transactions.
    """

    def setUp(self) -> None:
        """
        Set up test environment with mocked dependencies.

        Create mocks for:
        - External services and database operations
        - Django transaction management
        - Logging infrastructure
        - Cache mechanisms
        """
        super().setUp()

        # Initialize test fixtures and mocks
        self._setup_service_mocks()
        self._setup_model_mocks()
        self._setup_database_mocks()
        self._setup_logging_mocks()
        self._setup_cache_mocks()

    def _setup_service_mocks(self) -> None:
        """Set up mocks for external services."""
        self.mock_service = MagicMock()

    def _setup_model_mocks(self) -> None:
        """Set up mocks for database models and instances."""
        # Create real model instances for testing
        self.real_mock_model = ModelTest(name="ModelTest")
        self.real_test_model_as_class = ModelTest

        # Create mock model with spec for strict interface compliance
        self.mock_model = MagicMock(spec=ModelTest)

    def _setup_database_mocks(self) -> None:
        """Set up mocks for database manager and transactions."""
        # Real manager instance with mocked model
        self.real_mock_manager = DBManager()
        self.real_mock_manager.model = MagicMock()

        # Mock manager with spec for interface compliance
        self.mock_manager = MagicMock(spec=DBManager)

        # Mock Django transaction management
        self.mock_commit = self._start_patch_with_cleanup("django.db.transaction.commit")
        self.mock_rollback = self._start_patch_with_cleanup("django.db.transaction.rollback")

    def _setup_logging_mocks(self) -> None:
        """Set up mocks for logging infrastructure."""
        self.mock_logger = self._start_patch_with_cleanup("cmn.base_model.logger")

        # Create convenient references to specific log level methods
        self.mock_info_logger = self.mock_logger.info
        self.mock_error_logger = self.mock_logger.error
        self.mock_exception_logger = self.mock_logger.exception

    def _setup_cache_mocks(self) -> None:
        """Set up mocks for Django cache framework."""
        self.mock_cache = self._start_patch_with_cleanup("django.core.cache.cache")

    def _start_patch_with_cleanup(self, target: str) -> MagicMock:
        """
        Start a patch and register it for automatic cleanup.

        Args:
            target: The import path to patch

        Returns:
            The mock object created by the patch
        """
        patcher = patch(target)
        mock_obj = patcher.start()
        self.addCleanup(patcher.stop)
        return mock_obj

    # Logging assertion helpers
    def assert_logs_error(self, expected_message: str, call_count: Optional[int] = None) -> None:
        """
        Assert that a specific error message was logged.

        Args:
            expected_message: The expected error message
            call_count: Expected number of times the message was logged (optional)
        """
        if call_count is not None:
            self.assertEqual(self.mock_error_logger.call_count, call_count)
        self.mock_error_logger.assert_called_with(expected_message)

    def assert_no_errors_logged(self) -> None:
        """Assert that no error messages were logged."""
        self.mock_error_logger.assert_not_called()

    def assert_logs_info(self, expected_message: str, call_count: Optional[int] = None) -> None:
        """
        Assert that a specific info message was logged.

        Args:
            expected_message: The expected info message
            call_count: Expected number of times the message was logged (optional)
        """
        if call_count is not None:
            self.assertEqual(self.mock_info_logger.call_count, call_count)
        self.mock_info_logger.assert_called_with(expected_message)

    def assert_no_infos_logged(self) -> None:
        """Assert that no info messages were logged."""
        self.mock_info_logger.assert_not_called()

    def assert_logs_exception(self, expected_message: str, call_count: Optional[int] = None) -> None:
        """
        Assert that a specific exception message was logged.

        Args:
            expected_message: The expected exception message
            call_count: Expected number of times the message was logged (optional)
        """
        if call_count is not None:
            self.assertEqual(self.mock_exception_logger.call_count, call_count)
        self.mock_exception_logger.assert_called_with(expected_message)

    def assert_no_exceptions_logged(self) -> None:
        """Assert that no exception messages were logged."""
        self.mock_exception_logger.assert_not_called()

    def assert_logs_any_level(self, expected_message: str, log_level: str = "info") -> None:
        """
        Assert that a message was logged at any specified level.

        Args:
            expected_message: The expected log message
            log_level: The log level to check ('info', 'error', 'exception')
        """
        logger_method = getattr(self.mock_logger, log_level.lower())
        logger_method.assert_called_with(expected_message)

    def assert_transaction_committed(self, call_count: int = 1) -> None:
        """
        Assert that database transaction was committed.

        Args:
            call_count: Expected number of commit calls
        """
        self.assertEqual(self.mock_commit.call_count, call_count)

    def assert_transaction_rolled_back(self, call_count: int = 1) -> None:
        """
        Assert that database transaction was rolled back.

        Args:
            call_count: Expected number of rollback calls
        """
        self.assertEqual(self.mock_rollback.call_count, call_count)

    def reset_all_mocks(self) -> None:
        """
        Reset all mocks to their initial state.

        Useful when you need to clear mock call history during a test
        without affecting the mock setup.
        """
        self.mock_service.reset_mock()
        self.mock_model.reset_mock()
        self.mock_manager.reset_mock()
        self.mock_logger.reset_mock()
        self.mock_commit.reset_mock()
        self.mock_rollback.reset_mock()
        self.mock_cache.reset_mock()
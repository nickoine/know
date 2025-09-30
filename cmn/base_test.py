# Built-in
import json
from pathlib import Path
from typing import Optional, Union, Dict, Any
from unittest.mock import MagicMock, patch

# External
from rest_framework.test import APIClient
from django.contrib.auth.hashers import make_password
from django.test import SimpleTestCase, TestCase
from django.db import models

# Internal
from cmn import DBManager, BaseModel
from user.models import User
from user.repo import UserRepository
from questionnaire.repo import QuestionnaireRepository
from questionnaire.models import Questionnaire


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


class BaseApiTestCase(TestCase):
    """
    Base class for API integration tests.

    - On class setup: run all migrations once.
    - Before each test method: flush all data.
    - Provides self.client for making API requests.
    """
    _admin: Optional[User] = None
    _questionnaire: Optional[Questionnaire] = None

    client: APIClient = None


    def setUp(self) -> None:
        # Give each test its own client instance
        self.client = APIClient()
        super().setUp()


    def tearDown(self) -> None:
        super().tearDown()


    def load_admin_in_db(self) -> User:
        """
        Return a cached admin user, inserting into the DB.
        """

        if self._admin is None:
            self._admin_to_db()
        return self._admin  # type: ignore[return-value]


    def _admin_to_db(self) -> None:
        """
        Load `fixtures/admin_user.json`, create a user via UserRepository,
        set staff flags and hashed password, then cache it.
        """
        # 1) Load the JSON fixture
        fixtures_dir = Path(__file__).resolve().parent / "fixtures"
        with open(fixtures_dir / "admin.json", "r") as f:
            records = json.load(f)

        # Assuming a single‑record fixture:
        data = records[0].get("fields")

        # 2) Pull out the raw password
        raw_password = data.pop("password")

        # 3) Try to find existing user first, otherwise create new one
        user_repo = UserRepository()
        try:
            # Try to get existing user by username first
            user_queryset = user_repo.manager.filter_by(username=data.get('username'))
            user = user_queryset.first()

            if not user:
                # Try to get by email
                user_queryset = user_repo.manager.filter_by(email=data.get('email'))
                user = user_queryset.first()
        except Exception:
            user = None

        if not user:
            # Create the user via your repository (handles email, registration_method, etc.)
            user = user_repo.create_user(**data)

        # 4) Mark as admin & set hashed password
        user.is_staff = True

        # If the fixture password isn't already hashed, hash it now
        if not raw_password.startswith("pbkdf2_"):
            user.password = make_password(raw_password)
        else:
            user.password = raw_password

        user.save()

        # 5) Cache for future calls
        self._admin = user


    def load_questionnaire(self, to_db: bool = False) -> Union[Dict[str, Any], Questionnaire]:
        """
        Load the first record from `fixtures/questionnaire.json`.

        Args:
            to_db (bool):
                - If False, return the raw fixture data (a dict of fields).
                - If True, persist that data via the repository and return
                  the saved Questionnaire instance. The staff_id will be set
                  to reference the admin user created by load_admin_in_db().

        Returns:
            Union[Dict[str, Any], Questionnaire]: Fixture fields or model instance.

        Raises:
            FileNotFoundError: If the fixture file does not exist.
            ValueError: If the fixture file is empty or malformed.
        """
        # Locate the fixture
        fixtures_dir = Path(__file__).resolve().parent / "fixtures"
        fixture_path = fixtures_dir / "questionnaire.json"
        if not fixture_path.is_file():
            raise FileNotFoundError(f"Fixture not found at {fixture_path}")

        # Load JSON
        records = json.loads(fixture_path.read_text())
        if not records or not isinstance(records, list):
            raise ValueError("`questionnaire.json` must contain a non‑empty list of records")

        # Extract the first record's fields
        fields: Dict[str, Any] = records[0].get("fields", {})
        if not fields:
            raise ValueError("No `fields` key found in the first fixture record")

        # Persist if requested
        if to_db:
            # Ensure we have an admin user and set it as the staff_id
            admin_user = self.load_admin_in_db()
            fields = fields.copy()  # Don't modify original fixture data
            fields['staff_id'] = admin_user  # Pass the User instance, not the ID

            repo = QuestionnaireRepository()
            instance = repo.create_entity(**fields)
            return instance

        # Otherwise return raw data
        return fields

        self.mock_cache.reset_mock()

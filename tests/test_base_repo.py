from unittest.mock import patch, MagicMock, call
from cmn.base_test import TestClassBase
from cmn.base_repo import BaseRepository


class TestBaseRepoGet(TestClassBase):


    def setUp(self) -> None:
        super().setUp()

        self.test_data = 1
        self.repository = BaseRepository(model=self.real_test_model_as_class)
        self.repository._manager = self.mock_service
        self.repository._cache_manager = self.mock_service


        self.repository._cache_enabled = False


    def test_get_entity_by_id_without_cache_success(self):
        """Test successful fetch when cache is disabled."""

        # Arrange
        self.repository.manager.get_by_id.return_value = self.mock_model

        # Act
        result = self.repository.get_entity_by_id(self.test_data)

        # Assert
        self.assertEqual(result, self.mock_model)
        self.mock_cache.get.assert_not_called()
        self.mock_cache.set.assert_not_called()
        self.assert_no_errors_logged()


    def test_get_entity_by_id_without_cache_failed(self):
        """Test failed fetch when cache is disabled."""

        # Arrange
        self.repository.manager.get_by_id.return_value = None

        # Act
        result = self.repository.get_entity_by_id(self.test_data)

        # Assert
        self.assertEqual(result, None)
        self.mock_cache.get.assert_not_called()
        self.mock_cache.set.assert_not_called()
        self.assert_no_errors_logged()


    def test_get_entity_by_id_without_cache_exception(self):
        """Test failed fetch when cache is disabled and exception occurs"""

        # Arrange
        self.repository.manager.get_by_id.side_effect = Exception("DB error")

        # Act
        with patch("kyc.common.base_repo.logger.exception") as mock_logger:
            result = self.repository.get_entity_by_id(self.test_data)

        # Assert
        self.assertIsNone(result)
        mock_logger.assert_called_once()
        self.assertIn("Failed to fetch", mock_logger.call_args[0][0])
        self.assertIn(str(self.test_data), mock_logger.call_args[0][0])
        self.mock_cache.get.assert_not_called()


    def test_get_entity_by_id_with_cache_hit(self):
        """Test that get_entity_by_id() returns cached value and skips DB on cache hit."""

        # Arrange
        self.repository._cache_enabled = True

        expected_result = MagicMock()
        self.repository._cache_manager.get = MagicMock(return_value=expected_result)
        self.repository._cache_manager.set = MagicMock()
        self.repository._manager.get_by_id = MagicMock()

        # Act
        result = self.repository.get_entity_by_id(self.test_data)
        expected_key = f"{self.repository.model.__name__.lower()}:{self.test_data}"

        # Assert
        self.assertEqual(result, expected_result)
        self.repository._cache_manager.get.assert_called_once_with(expected_key)
        self.repository._manager.get_by_id.assert_not_called()
        self.repository._cache_manager.set.assert_not_called()


    def test_get_entity_by_id_cache_miss_hits_db_and_sets_cache(self):
        """Test that get_entity_by_id() hits DB and sets cache when cache is enabled but misses."""

        # Arrange
        self.repository._cache_enabled = True

        expected_result = self.mock_service
        self.repository._cache_manager.set = MagicMock()
        self.repository._cache_manager.get = MagicMock(return_value=None)
        self.repository._manager.get_by_id = MagicMock(return_value=expected_result)

        # Act
        result = self.repository.get_entity_by_id(self.test_data)
        expected_key = f"{self.repository.model.__name__.lower()}:{self.test_data}"

        # Assert
        self.assertEqual(result, expected_result)
        self.repository._cache_manager.get.assert_called_once_with(expected_key)
        self.repository._manager.get_by_id.assert_called_once_with(self.test_data)
        self.repository._cache_manager.set.assert_called_once_with(
            expected_key, expected_result, timeout=self.repository.CACHE_TIMEOUT
        )


class TestBaseRepoCreate(TestClassBase):


    def setUp(self) -> None:
        super().setUp()

        self.test_data = 1
        self.repository = BaseRepository(model=self.real_test_model_as_class)
        self.repository._manager = self.mock_service
        self.repository._cache_manager = self.mock_service

        self.repository._cache_enabled = False

        self.mock_instance1 = MagicMock(id=1)
        self.mock_instance2 = MagicMock(id=2)

        self.expected_calls = [
            call(f"modeltest:{self.mock_instance1.id}"),
            call(f"modeltest:{self.mock_instance2.id}")
        ]


    def test_create_entity_delete_cache_success(self):
        """Should create an entity and invalidate cache successfully."""

        # Arrange
        self.repository._cache_enabled = True
        self.mock_service.id = 2

        self.repository._manager.create_instance = MagicMock(return_value=self.mock_service)
        self.repository._cache_manager.delete = MagicMock()

        # Act
        result = self.repository.create_entity(name="Test")

        # Assert
        self.assertEqual(result, self.mock_service)
        expected_key = f"{self.repository.model.__name__.lower()}:{self.mock_service.id}"
        self.repository._cache_manager.delete.assert_called_once_with(expected_key)


    def test_create_entity_fail_and_handles_error(self):
        """Should log exception and not call cache when create_instance raises error."""

        # Arrange
        self.repository._cache_enabled = True
        self.repository._manager.create_instance = MagicMock(side_effect=Exception("Unexpected error"))
        self.repository._cache_manager.delete = MagicMock()

        with patch("kyc.common.base_repo.logger.exception") as mock_logger:

            # Act
            result = self.repository.create_entity(name="Test")

            # Assert
            self.assertIsNone(result)
            mock_logger.assert_called_once()
            self.assertIn("Unexpected error", mock_logger.call_args[0][0])
            self.repository._cache_manager.delete.assert_not_called()


    def test_bulk_create_entities_success(self):
        """Should bulk create entities and invalidate cache successfully."""

        # Arrange
        self.repository._cache_enabled = True

        self.repository._manager.bulk_create_instances = MagicMock(
            return_value=[self.mock_instance1, self.mock_instance2]
        )
        self.repository._cache_manager.delete = MagicMock()

        # Act
        self.repository.bulk_create_entities([self.mock_instance1, self.mock_instance2])

        # Assert
        self.repository._manager.bulk_create_instances.assert_called_once()
        self.repository._cache_manager.delete.assert_has_calls(self.expected_calls, any_order=True)
        self.assert_no_errors_logged()


    def test_bulk_create_entities_fail_and_handle_error(self):
        """Should log exception and skip cache invalidation when bulk creation fails."""

        # Arrange
        self.repository._cache_enabled = True
        self.repository._manager.bulk_create_instances.side_effect = Exception("Unexpected error")
        self.repository._cache_manager.delete = MagicMock()

        with patch("kyc.common.base_repo.logger.exception") as mock_logger:

            # Act & Assert: Check exception raised
            with self.assertRaises(Exception) as context:
                self.repository.bulk_create_entities([self.mock_instance1, self.mock_instance2])

            # Assert: exception was re-raised
            self.assertIn("Unexpected error", str(context.exception))

            # Assert: logger.exception was called with proper message
            mock_logger.assert_called_once()
            logged_msg = mock_logger.call_args[0][0]
            self.assertIn("Unexpected error during bulk create", logged_msg)

            # Assert: no cache deletion happened
            self.repository._cache_manager.delete.assert_not_called()


    def test_fetch_all_entities_success(self):
        """Should fetch all entities by internal method _fetch_all_entities."""

        # Arrange
        self.repository._manager.get_all.return_value = self.mock_service

        with patch("kyc.common.base_repo.logger.info") as mock_logger:

            # Act
            result = self.repository._fetch_all_entities()

            # Assert
            self.assertEqual(result, list(self.mock_service))
            mock_logger.assert_called_once()
            self.assertIn("Successfully fetched", mock_logger.call_args[0][0])
            self.repository._manager.get_all.assert_called_once()


    def test_fetch_all_entities_fail(self):
        """Test that fetch propagates database errors with proper logging."""

        # Arrange
        test_error = Exception("DB Error")
        self.repository._manager.get_all.side_effect = test_error

        with patch("kyc.common.base_repo.logger.error") as mock_logger:
            # Act & Assert
            with self.assertRaises(Exception) as context:
                self.repository._fetch_all_entities()

            self.assertIs(context.exception, test_error)

            mock_logger.assert_called_once()
            logged_msg = mock_logger.call_args[0][0]
            self.assertIn("Failed to fetch", logged_msg)
            self.assertIn("DB Error", logged_msg)


    def test_get_all_entities_with_cache_hit(self):
        """Should return cached entities when available."""

        # Arrange
        self.repository._cache_enabled = True
        cached_data = [self.mock_instance1, self.mock_instance2]
        self.repository._cache_manager.get_or_set = MagicMock(return_value=cached_data)

        # Act
        result = self.repository.get_all_entities()

        # Assert
        self.assertEqual(result, cached_data)
        self.repository._cache_manager.get_or_set.assert_called_once()
        self.repository._manager.get_all.assert_not_called()


    def test_get_all_entities_with_cache_error(self):
        """Should fall back to direct fetch when cache fails."""

        # Arrange
        self.repository._cache_enabled = True
        mock_entities = [self.mock_instance1, self.mock_instance2]

        # Set up cache error and successful fallback
        self.repository._cache_manager.get_or_set = MagicMock(
            side_effect=Exception("Cache unavailable")
        )
        self.repository._fetch_all_entities = MagicMock(return_value=mock_entities)

        with patch("kyc.common.base_repo.logger.warning") as mock_logger:
            # Act
            result = self.repository.get_all_entities()

            # Assert
            self.assertEqual(result, mock_entities)
            mock_logger.assert_called_once()
            self.assertIn("Cache operation failed", mock_logger.call_args[0][0])
            self.repository._fetch_all_entities.assert_called_once()


    def test_get_all_entities_handle_exception_when_fetch_fail(self):
        """Should log error and raise ValueError when fetch fails."""

        # Arrange
        test_error = Exception("DB connection failed")
        self.repository._fetch_all_entities = MagicMock(side_effect=test_error)

        with patch("kyc.common.base_repo.logger.error") as mock_logger:
            # Act & Assert
            with self.assertRaises(ValueError) as context:
                self.repository.get_all_entities()

            # Verify error handling
            self.assertIn("DB connection failed", str(context.exception))
            mock_logger.assert_called_once()
            self.assertIn("Failed to fetch all", mock_logger.call_args[0][0])


class TestBaseRepoUpdate(TestClassBase):


    def setUp(self) -> None:
        super().setUp()

        self.test_data = 1
        self.repository = BaseRepository(model=self.real_test_model_as_class)
        self.repository._manager = self.mock_service
        self.repository._cache_manager = self.mock_service

        self.repository._cache_enabled = False

        self.mock_instance1 = MagicMock(id=1)
        self.mock_instance2 = MagicMock(id=2)

        self.expected_calls = [
            call(f"modeltest:{self.mock_instance1.id}"),
            call(f"modeltest:{self.mock_instance2.id}")
        ]


    def test_update_entity_success_with_cache_invalidation(self):
        """Verifies complete success flow including cache clearance"""

        # Arrange
        update_data = {"name": "New Name"}
        self.repository._cache_enabled = True
        mock_instance = self.mock_service
        self.repository._manager.get_by_id.return_value = mock_instance
        self.repository._cache_manager.update = MagicMock()

        # Act
        result = self.repository.update_entity(self.test_data, **update_data)

        # Assert
        self.assertEqual(result, mock_instance)
        mock_instance.update.assert_called_once()
        self.repository._cache_manager.update.assert_called_once_with(**update_data)


    def test_update_entity_handles_database_failure(self):
        """Tests DB failure handling without cache interactions"""

        # Arrange
        update_data = {"name": "New Name"}
        self.repository._cache_enabled = True
        mock_instance = self.mock_service
        self.repository._manager.get_by_id.return_value = mock_instance
        self.repository._cache_manager.delete.side_effect = Exception("Cache error")

        # Act
        with patch("kyc.common.base_repo.logger.error") as mock_logger:
            result = self.repository.update_entity(self.test_data, **update_data)

            # Assert
            self.assertEqual(result, mock_instance)
            mock_logger.assert_called_once()
            self.assertIn("Failed to clear cache", mock_logger.call_args[0][0])


    def test_update_entity_not_found(self):
        """Test update when entity doesn't exist"""
        # Arrange

        update_data = {"name": "New Name"}

        # Properly mock the manager chain
        self.repository._manager = MagicMock()
        self.repository._manager.get_by_id = MagicMock()
        self.repository._manager.get_by_id.return_value = None

        # Act
        with patch("kyc.common.base_repo.logger.warning") as mock_logger:
            result = self.repository.update_entity(self.test_data, **update_data)

        # Assert
        self.assertIsNone(result)
        mock_logger.assert_called_once()
        self.assertIn("not found", mock_logger.call_args[0][0])

        # Verify manager was called correctly
        self.repository._manager.get_by_id.assert_called_once_with(self.test_data)


    def test_bulk_update_entities_success(self):
        """Should bulk update entities and invalidate cache successfully."""
        # Arrange
        self.repository._cache_enabled = True

        self.repository._manager.bulk_update_instances = MagicMock(
            return_value=[self.mock_instance1, self.mock_instance2]
        )
        self.repository._cache_manager.delete = MagicMock()

        # Act
        result = self.repository.bulk_update_entities(
            [self.mock_instance1, self.mock_instance2],
            ["field1", "field2"]
        )

        # Assert
        self.assertEqual(len(result), 2)
        self.repository._manager.bulk_update_instances.assert_called_once_with(
            [self.mock_instance1, self.mock_instance2],
            ["field1", "field2"]
        )
        # Verify cache was cleared for both instances
        self.assertEqual(self.repository._cache_manager.delete.call_count, 2)


    def test_bulk_update_entities_fail_and_handle_error(self):
        """Should log exception and skip cache invalidation when bulk creation fails."""

        # Arrange
        self.repository._cache_enabled = True
        self.repository._manager.bulk_update_instances.side_effect = Exception("Unexpected error")
        self.repository._cache_manager.delete = MagicMock()

        with patch("kyc.common.base_repo.logger.error") as mock_logger:

            # Act & Assert: Check exception raised
            with self.assertRaises(ValueError) as context:
                self.repository.bulk_update_entities([self.mock_instance1, self.mock_instance2], ["field"])

            # Assert: exception was re-raised
            self.assertIn("Bulk update failed: Unexpected error", str(context.exception))  # Updated message check

            # Assert: logger.error was called with proper message
            mock_logger.assert_called_once()
            logged_msg = mock_logger.call_args[0][0]
            self.assertIn("Unexpected error during bulk update", logged_msg)  # Updated message check

            # Assert: no cache deletion happened
            self.repository._cache_manager.delete.assert_not_called()


class TestBaseRepoDelete(TestClassBase):


    def setUp(self) -> None:
        super().setUp()

        self.test_data = 1
        self.repository = BaseRepository(model=self.real_test_model_as_class)
        self.repository._manager = self.mock_service
        self.repository._cache_manager = MagicMock()

        self.repository._cache_enabled = False
        self.mock_model.__name__ = "TestModel"

        self.mock_instance1 = MagicMock(id=1)
        self.mock_instance2 = MagicMock(id=2)

        self.expected_calls = [
            call(f"modeltest:{self.mock_instance1.id}"),
            call(f"modeltest:{self.mock_instance2.id}")
        ]


    def test_delete_entity_success_with_cache_invalidation(self):
        """Verifies complete success flow including cache clearance"""

        # Arrange
        self.repository._cache_enabled = True
        mock_instance = self.mock_service
        self.repository._manager.get_by_id.return_value = mock_instance
        self.repository._cache_manager.delete = MagicMock()

        # Act
        result = self.repository.delete_entity(self.test_data)

        # Assert
        self.assertEqual(result, mock_instance)
        mock_instance.delete.assert_called_once()
        self.repository._cache_manager.delete.assert_called_once_with(
            f"modeltest:{self.test_data}"
        )


    def test_delete_entity_handles_database_failure(self):
        """Tests DB failure handling without cache interactions."""

        # Arrange
        test_error = Exception("DB error")
        self.repository._manager.get_by_id.return_value = self.mock_service
        self.mock_service.delete.side_effect = test_error
        self.repository._cache_enabled = True

        # Act & Assert
        with patch.object(self.repository._cache_manager, 'delete') as mock_cache_delete:
            with self.assertRaises(ValueError) as context:
                self.repository.delete_entity(self.test_data)

            # Verify error propagation
            self.assertIn("DB error", str(context.exception))

            # Verify cache wasn't touched
            mock_cache_delete.assert_not_called()


    def test_delete_entity_handles_cache_failure_after_successful_delete(self):
        """Tests cache failure after successful DB operation"""

        # Arrange
        self.repository._cache_enabled = True
        mock_instance = MagicMock()
        self.repository._manager.get_by_id.return_value = mock_instance
        self.repository._cache_manager.delete.side_effect = Exception("Cache error")

        # Act
        with patch("kyc.common.base_repo.logger.error") as mock_logger:
            result = self.repository.delete_entity(self.test_data)

            # Assert
            self.assertEqual(result, mock_instance)
            mock_logger.assert_called_once()
            self.assertIn("Failed to clear cache", mock_logger.call_args[0][0])


    def test_delete_entity_returns_none_when_not_found(self):
        """Tests 'not found' scenario with warning logging"""

        # Arrange
        self.repository._manager.get_by_id.return_value = None

        # Act
        with patch("kyc.common.base_repo.logger.warning") as mock_logger:
            result = self.repository.delete_entity(self.test_data)

        # Assert
        self.assertIsNone(result)
        mock_logger.assert_called_once()
        self.assertIn("not found", mock_logger.call_args[0][0])


    def test_bulk_delete_entities_success(self):
        """Should bulk delete entities and invalidate cache successfully."""

        # Arrange
        self.repository._cache_enabled = True

        self.repository._manager.bulk_delete_instances = MagicMock(
            return_value=[self.mock_instance1, self.mock_instance2]
        )
        self.repository._cache_manager.delete = MagicMock()

        # Act
        self.repository.bulk_delete_entities([self.mock_instance1, self.mock_instance2], filter="field")

        # Assert
        self.repository._manager.bulk_delete_instances.assert_called_once()
        self.repository._cache_manager.delete.assert_has_calls(self.expected_calls, any_order=True)
        self.assert_no_errors_logged()


    def test_bulk_delete_entities_fail_and_handle_error(self):
        """Should log exception and skip cache invalidation when bulk creation fails."""

        # Arrange
        self.repository._cache_enabled = True
        self.repository._manager.bulk_delete_instances.side_effect = Exception("Unexpected error")
        self.repository._cache_manager.delete = MagicMock()

        with patch("kyc.common.base_repo.logger.exception") as mock_logger:

            # Act & Assert: Check exception raised
            with self.assertRaises(Exception) as context:
                self.repository.bulk_delete_entities([self.mock_instance1, self.mock_instance2])

            # Assert: exception was re-raised
            self.assertIn("Unexpected error", str(context.exception))

            # Assert: logger.exception was called with proper message
            mock_logger.assert_called_once()
            logged_msg = mock_logger.call_args[0][0]
            self.assertIn("Unexpected error during bulk delete", logged_msg)

            # Assert: no cache deletion happened
            self.repository._cache_manager.delete.assert_not_called()


    def test_bulk_delete_with_empty_list_early_return(self):
        """Tests empty input handling"""

        # Arrange
        self.repository._manager.bulk_delete_instances = MagicMock()

        # Act
        with patch("kyc.common.base_repo.logger.debug") as mock_logger:
            result, count = self.repository.bulk_delete_entities([])

        # Assert
        self.assertEqual(result, [])
        self.assertEqual(count, 0)
        mock_logger.assert_called_once_with(
            "Empty instances list provided for bulk delete"
        )
        self.repository._manager.bulk_delete_instances.assert_not_called()

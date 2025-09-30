import pytest
from unittest.mock import Mock, patch, call
from typing import cast, Any
from django.db import DatabaseError

from cmn.base_repo import BaseRepository
from cmn.base_test import TestClassBase


class BaseRepositoryConstructorTests(TestClassBase):
    """Test BaseRepository constructor and property initialization."""

    def test_init_with_model_parameter(self):
        """Test constructor with valid model parameter."""
        repo = BaseRepository(model=self.real_test_model_as_class)
        
        assert repo._model == self.real_test_model_as_class
        assert repo._cache_enabled is False
        assert repo._cache_manager is not None
        assert repo._manager is None

    def test_init_with_cache_enabled(self):
        """Test constructor with cache enabled."""
        repo = BaseRepository(model=self.real_test_model_as_class, cache_enabled=True)
        
        assert repo._cache_enabled is True
        assert repo._cache_manager is not None

    def test_init_without_model(self):
        """Test constructor without model parameter raises error."""
        with pytest.raises(ValueError, match="Repository must have a ._model defined"):
            BaseRepository()

    def test_model_property_returns_set_model(self):
        """Test model property returns the configured model."""
        repo = BaseRepository(model=self.real_test_model_as_class)
        
        assert repo.model == self.real_test_model_as_class

    def test_model_property_raises_when_none(self):
        """Test model property raises error when not configured."""
        # Create repo without model to test the error condition
        with pytest.raises(ValueError, match="Repository must have a ._model defined"):
            BaseRepository()

    def test_manager_property_lazy_loads(self):
        """Test manager property returns model.objects lazily."""
        repo = BaseRepository(model=self.real_test_model_as_class)
        
        manager = repo.manager
        
        assert manager == self.real_test_model_as_class.objects
        assert repo._manager == manager

    def test_manager_property_returns_cached_instance(self):
        """Test manager property returns cached instance on subsequent calls."""
        repo = BaseRepository(model=self.real_test_model_as_class)
        
        manager1 = repo.manager
        manager2 = repo.manager
        
        assert manager1 == manager2
        assert manager1 == self.real_test_model_as_class.objects

    def test_cache_enabled_property(self):
        """Test cache_enabled property returns correct value."""
        repo_disabled = BaseRepository(model=self.real_test_model_as_class, cache_enabled=False)
        repo_enabled = BaseRepository(model=self.real_test_model_as_class, cache_enabled=True)
        
        assert repo_disabled.cache_enabled is False
        assert repo_enabled.cache_enabled is True


class BaseRepositoryValidationTests(TestClassBase):
    """Test BaseRepository validation methods."""

    def setUp(self):
        super().setUp()
        self.repo = BaseRepository(model=self.real_test_model_as_class)

    def test_validate_id_with_valid_integer(self):
        """Test _validate_id with valid integer ID."""
        result = self.repo._validate_id(123)
        assert result == 123

    def test_validate_id_with_valid_string_integer(self):
        """Test _validate_id with string that converts to integer."""
        result = self.repo._validate_id("456")
        assert result == 456

    def test_validate_id_with_invalid_string(self):
        """Test _validate_id with non-numeric string."""
        with pytest.raises(ValueError, match="Invalid ID format"):
            self.repo._validate_id("invalid")

    def test_validate_id_with_none(self):
        """Test _validate_id with None value."""
        with pytest.raises(ValueError, match="ID cannot be None"):
            self.repo._validate_id(None)

    def test_validate_id_with_zero(self):
        """Test _validate_id with zero value."""
        with pytest.raises(ValueError, match="ID must be positive"):
            self.repo._validate_id(0)

    def test_validate_id_with_negative(self):
        """Test _validate_id with negative value."""
        with pytest.raises(ValueError, match="ID must be positive"):
            self.repo._validate_id(-1)

    def test_validate_kwargs_with_valid_data(self):
        """Test _validate_kwargs with valid data."""
        kwargs = {'name': 'test', 'value': 123}
        result = self.repo._validate_kwargs(kwargs, 'create')
        
        assert result == kwargs

    def test_validate_kwargs_with_empty_dict(self):
        """Test _validate_kwargs with empty dictionary."""
        with pytest.raises(ValueError, match="No data provided for create"):
            self.repo._validate_kwargs({}, 'create')

    def test_validate_kwargs_with_none(self):
        """Test _validate_kwargs with None value."""
        with pytest.raises(ValueError, match="No data provided for update"):
            self.repo._validate_kwargs(None, 'update')

    def test_validate_instances_list_with_valid_list(self):
        """Test _validate_instances_list with valid model instances."""
        instances = [self.real_mock_model, self.real_mock_model]
        result = self.repo._validate_instances_list(instances, 'bulk_create')
        
        assert result == instances

    def test_validate_instances_list_with_empty_list(self):
        """Test _validate_instances_list with empty list."""
        with pytest.raises(ValueError, match="Empty instances list provided for bulk_create"):
            self.repo._validate_instances_list([], 'bulk_create')

    def test_validate_instances_list_with_none(self):
        """Test _validate_instances_list with None value."""
        with pytest.raises(ValueError, match="Instances must be a list for bulk_update"):
            self.repo._validate_instances_list(None, 'bulk_update')

    def test_validate_instances_list_with_invalid_type(self):
        """Test _validate_instances_list with non-model instances."""
        non_model_object = object()  # Use a proper non-model object instead of string
        # Cast to suppress type checker warning - we're intentionally testing invalid input
        invalid_list = cast(Any, [non_model_object])
        with pytest.raises(ValueError, match="is not a Django model instance"):
            self.repo._validate_instances_list(invalid_list, 'bulk_delete')

    def test_validate_fields_list_with_valid_fields(self):
        """Test _validate_fields_list with valid field names."""
        fields = ['name', 'value', 'status']
        result = self.repo._validate_fields_list(fields, 'bulk_update')
        
        assert result == fields

    def test_validate_fields_list_with_empty_list(self):
        """Test _validate_fields_list with empty list."""
        with pytest.raises(ValueError, match="Empty fields list provided for bulk_update"):
            self.repo._validate_fields_list([], 'bulk_update')

    def test_validate_fields_list_with_none(self):
        """Test _validate_fields_list with None value."""
        with pytest.raises(ValueError, match="Fields must be a list for bulk_update"):
            self.repo._validate_fields_list(None, 'bulk_update')


class BaseRepositoryCacheTests(TestClassBase):
    """Test BaseRepository cache management methods."""

    def setUp(self):
        super().setUp()
        self.repo = BaseRepository(model=self.real_test_model_as_class, cache_enabled=True)
        self.repo._cache_manager = self.mock_cache_manager = Mock()

    def test_get_cache_key_for_entity(self):
        """Test _get_cache_key generates correct entity cache key."""
        key = self.repo._get_cache_key(123)
        expected = "test.modeltest.123"  # app_label is 'test' from ModelTest Meta class
        
        assert key == expected

    def test_get_cache_key_with_suffix(self):
        """Test _get_cache_key with suffix parameter."""
        key = self.repo._get_cache_key(123, "detail")
        expected = "test.modeltest.123.detail"  # app_label is 'test' from ModelTest Meta class
        
        assert key == expected

    def test_get_collection_cache_key(self):
        """Test _get_collection_cache_key generates correct collection key."""
        key = self.repo._get_collection_cache_key()
        expected = "test.modeltest.all"  # app_label is 'test' from ModelTest Meta class
        
        assert key == expected

    def test_get_collection_cache_key_with_suffix(self):
        """Test _get_collection_cache_key with suffix parameter."""
        key = self.repo._get_collection_cache_key("paginated")
        expected = "test.modeltest.paginated"  # app_label is 'test' from ModelTest Meta class
        
        assert key == expected

    def test_safe_cache_operation_success(self):
        """Test _safe_cache_operation with successful cache operation."""
        self.mock_cache_manager.get.return_value = "cached_value"
        
        result = self.repo._safe_cache_operation("get", "test_key")
        
        self.mock_cache_manager.get.assert_called_once_with("test_key")
        assert result == "cached_value"

    def test_safe_cache_operation_with_exception(self):
        """Test _safe_cache_operation handles cache exceptions gracefully."""
        self.mock_cache_manager.set.side_effect = Exception("Cache error")
        
        result = self.repo._safe_cache_operation("set", "test_key", "test_value")
        
        assert result is None
        # Verify that the cache manager set method was called with the expected parameters
        self.mock_cache_manager.set.assert_called_once_with("test_key", "test_value", 900)

    def test_invalidate_collection_caches(self):
        """Test _invalidate_collection_caches removes collection cache entries."""
        self.repo._invalidate_collection_caches()
        
        expected_calls = [
            call("test.modeltest.all"),  # Updated to match actual implementation
            call("test.modeltest.count"),
            call("test.modeltest.paginated")
        ]
        self.mock_cache_manager.delete.assert_has_calls(expected_calls, any_order=True)

    def test_clear_cache_specific_entity(self):
        """Test clear_cache removes specific entity cache."""
        self.repo.clear_cache(obj_id=123)
        
        self.mock_cache_manager.delete.assert_called_once_with("test.modeltest.123")

    def test_clear_cache_all_entities(self):
        """Test clear_cache removes all cache entries when no ID specified."""
        self.repo.clear_cache()
        
        expected_calls = [
            call("test.modeltest.all"),
            call("test.modeltest.count"),
            call("test.modeltest.paginated")
        ]
        self.mock_cache_manager.delete.assert_has_calls(expected_calls, any_order=True)


class BaseRepositoryGetEntityByIdTests(TestClassBase):
    """Test BaseRepository get_entity_by_id method."""

    def setUp(self):
        super().setUp()
        self.repo = BaseRepository(model=self.real_test_model_as_class, cache_enabled=True)
        self.repo._manager = self.mock_manager
        self.repo._cache_manager = self.mock_cache_manager = Mock()
        
        # Mock the logger specifically for base_repo module
        self.mock_repo_logger = self._start_patch_with_cleanup("cmn.base_repo.logger")

    def test_get_entity_by_id_cache_hit(self):
        """Test get_entity_by_id returns cached entity."""
        self.mock_cache_manager.get.return_value = self.real_mock_model
        
        result = self.repo.get_entity_by_id(123)
        
        self.mock_cache_manager.get.assert_called_once_with("test.modeltest.123")
        self.mock_manager.get_by_id.assert_not_called()
        assert result == self.real_mock_model

    def test_get_entity_by_id_cache_miss_db_hit(self):
        """Test get_entity_by_id with cache miss but database hit."""
        self.mock_cache_manager.get.return_value = None
        self.mock_manager.get_by_id.return_value = self.real_mock_model
        
        result = self.repo.get_entity_by_id(123)
        
        self.mock_cache_manager.get.assert_called_once_with("test.modeltest.123")
        self.mock_manager.get_by_id.assert_called_once_with(123)
        self.mock_cache_manager.set.assert_called_once_with(
            "test.modeltest.123", self.real_mock_model, 900
        )
        assert result == self.real_mock_model

    def test_get_entity_by_id_not_found(self):
        """Test get_entity_by_id when entity doesn't exist."""
        self.mock_cache_manager.get.return_value = None
        self.mock_manager.get_by_id.return_value = None
        
        result = self.repo.get_entity_by_id(123)
        
        assert result is None
        self.mock_cache_manager.set.assert_not_called()

    def test_get_entity_by_id_with_invalid_id(self):
        """Test get_entity_by_id with invalid ID raises validation error."""
        with pytest.raises(ValueError, match="Invalid ID format"):
            self.repo.get_entity_by_id("invalid")

    def test_get_entity_by_id_with_cache_disabled(self):
        """Test get_entity_by_id bypasses cache when disabled."""
        repo = BaseRepository(model=self.real_test_model_as_class, cache_enabled=False)
        repo._manager = self.mock_manager
        self.mock_manager.get_by_id.return_value = self.real_mock_model
        
        result = repo.get_entity_by_id(123)
        
        self.mock_manager.get_by_id.assert_called_once_with(123)
        assert result == self.real_mock_model

    def test_get_entity_by_id_handles_database_error(self):
        """Test get_entity_by_id handles database errors gracefully."""
        self.mock_cache_manager.get.return_value = None
        self.mock_manager.get_by_id.side_effect = DatabaseError("Connection failed")
        
        with pytest.raises(ValueError, match="Failed to fetch entity by ID: Connection failed"):
            self.repo.get_entity_by_id(123)
        
        # Verify error was logged with expected message format
        self.mock_repo_logger.error.assert_called_once()
        call_args = self.mock_repo_logger.error.call_args
        logged_message = call_args[0][0]
        
        # Check that the logged message contains expected components
        assert "Failed to fetch ModelTest by ID=123: Connection failed" in logged_message


class BaseRepositoryGetAllEntitiesTests(TestClassBase):
    """Test BaseRepository get_all_entities method."""

    def setUp(self):
        super().setUp()
        self.repo = BaseRepository(model=self.real_test_model_as_class, cache_enabled=True)
        self.repo._manager = self.mock_manager
        self.repo._cache_manager = self.mock_cache_manager = Mock()
        self.mock_entities = [self.real_mock_model, self.real_mock_model]
        
        # Mock the logger specifically for base_repo module
        self.mock_repo_logger = self._start_patch_with_cleanup("cmn.base_repo.logger")

    def test_get_all_entities_cache_hit(self):
        """Test get_all_entities returns cached results."""
        self.mock_cache_manager.get.return_value = self.mock_entities
        
        result = self.repo.get_all_entities()
        
        self.mock_cache_manager.get.assert_called_once_with("test.modeltest.all")
        self.mock_manager.get_all.assert_not_called()
        assert result == self.mock_entities

    def test_get_all_entities_cache_miss(self):
        """Test get_all_entities with cache miss loads from database."""
        self.mock_cache_manager.get.return_value = None
        self.mock_manager.get_all.return_value = self.mock_entities
        
        result = self.repo.get_all_entities()
        
        self.mock_manager.get_all.assert_called_once()
        self.mock_cache_manager.set.assert_called_once_with(
            "test.modeltest.all", self.mock_entities, 600
        )
        assert result == self.mock_entities

    def test_get_all_entities_with_pagination(self):
        """Test get_all_entities with limit and offset parameters."""
        # Create a larger mock list for pagination testing
        all_entities = [Mock(id=i) for i in range(50)]  # 50 entities
        expected_result = all_entities[20:30]  # offset=20, limit=10
        
        self.mock_cache_manager.get.return_value = None
        self.mock_manager.get_all.return_value = all_entities
        
        result = self.repo.get_all_entities(limit=10, offset=20)
        
        self.mock_manager.get_all.assert_called_once()
        cache_key = "test.modeltest.all.limit_10.offset_20"
        self.mock_cache_manager.set.assert_called_once_with(
            cache_key, expected_result, 600
        )
        assert result == expected_result

    def test_get_all_entities_with_invalid_limit(self):
        """Test get_all_entities validates limit parameter."""
        with pytest.raises(ValueError, match="Limit must be a positive integer"):
            self.repo.get_all_entities(limit=-1)

    def test_get_all_entities_with_invalid_offset(self):
        """Test get_all_entities validates offset parameter."""
        with pytest.raises(ValueError, match="Offset must be a non-negative integer"):
            self.repo.get_all_entities(offset=-1)

    def test_get_all_entities_handles_database_error(self):
        """Test get_all_entities handles database errors gracefully."""
        self.mock_cache_manager.get.return_value = None
        self.mock_manager.get_all.side_effect = DatabaseError("Query failed")
        
        with pytest.raises(ValueError, match="Failed to fetch instances"):
            self.repo.get_all_entities()
        
        # Logger should be called twice - once in _fetch_all_entities and once in get_all_entities
        assert self.mock_repo_logger.error.call_count == 2
        
        # Check the final error call
        final_call_args, final_call_kwargs = self.mock_repo_logger.error.call_args
        assert "Failed to fetch ModelTest instances: Query failed" in final_call_args[0]
        assert final_call_kwargs.get('exc_info') is True


class BaseRepositoryCreateEntityTests(TestClassBase):
    """Test BaseRepository create_entity method."""

    # Allow database access for transaction-decorated methods
    databases = ['default']

    def setUp(self):
        super().setUp()
        self.repo = BaseRepository(model=self.real_test_model_as_class, cache_enabled=True)
        self.repo._manager = self.mock_manager
        self.repo._cache_manager = self.mock_cache_manager = Mock()
        
        # Mock the logger specifically for base_repo module
        self.mock_repo_logger = self._start_patch_with_cleanup("cmn.base_repo.logger")

    @patch('cmn.base_repo.transaction')
    def test_create_entity_success(self, _mock_transaction):
        """Test create_entity successfully creates new entity."""
        kwargs = {'name': 'test', 'value': 123}
        self.mock_manager.create_instance.return_value = self.real_mock_model
        
        result = self.repo.create_entity(**kwargs)
        
        self.mock_manager.create_instance.assert_called_once_with(**kwargs)
        assert result == self.real_mock_model
        
        expected_cache_deletes = [
            call("test.modeltest.all"),
            call("test.modeltest.count"),
            call("test.modeltest.paginated")
        ]
        self.mock_cache_manager.delete.assert_has_calls(expected_cache_deletes, any_order=True)


    def test_create_entity_with_empty_data(self):
        """Test create_entity with empty data raises validation error."""
        with pytest.raises(ValueError, match="No data provided for create"):
            self.repo.create_entity()


    @patch('cmn.base_repo.transaction')
    def test_create_entity_handles_database_error(self, _mock_transaction):
        """Test create_entity handles database errors gracefully."""
        kwargs = {'name': 'test'}
        self.mock_manager.create_instance.side_effect = DatabaseError("Creation failed")
        
        with pytest.raises(ValueError, match="Failed to create entity: Creation failed"):
            self.repo.create_entity(**kwargs)
        
        # Verify the error was logged correctly
        self.mock_repo_logger.error.assert_called_once()
        logged_message = self.mock_repo_logger.error.call_args[0][0]
        assert "Unexpected error creating ModelTest" in logged_message
        assert "Creation failed" in logged_message


    @patch('cmn.base_repo.transaction')
    def test_create_entity_raises_error_when_manager_returns_none(self, _mock_transaction):
        """Test create_entity raises ValueError when manager returns None."""
        kwargs = {'name': 'test'}
        self.mock_manager.create_instance.return_value = None
        
        with pytest.raises(ValueError, match="Failed to create entity - manager returned None"):
            self.repo.create_entity(**kwargs)
        
        # Verify the manager was called with the correct arguments
        self.mock_manager.create_instance.assert_called_once_with(name='test')


class BaseRepositoryUpdateEntityTests(TestClassBase):
    """Test BaseRepository update_entity method."""

    # Allow database access for transaction-decorated methods
    databases = ['default']

    def setUp(self):
        super().setUp()
        self.repo = BaseRepository(model=self.real_test_model_as_class, cache_enabled=True)
        self.repo._manager = self.mock_manager
        self.repo._cache_manager = self.mock_cache_manager = Mock()
        
        # Mock the logger specifically for base_repo module
        self.mock_repo_logger = self._start_patch_with_cleanup("cmn.base_repo.logger")

    @patch('cmn.base_repo.transaction')
    def test_update_entity_success(self, _mock_transaction):
        """Test update_entity successfully updates existing entity."""
        kwargs = {'name': 'updated'}
        mock_instance = Mock()
        self.mock_manager.get_by_id.return_value = mock_instance
        
        result = self.repo.update_entity(123, **kwargs)
        
        self.mock_manager.get_by_id.assert_called_once_with(123)
        mock_instance.update.assert_called_once_with(**kwargs)
        assert result == mock_instance
        
        self.mock_cache_manager.delete.assert_any_call("test.modeltest.123")
        expected_collection_deletes = [
            call("test.modeltest.all"),
            call("test.modeltest.count"),
            call("test.modeltest.paginated")
        ]
        self.mock_cache_manager.delete.assert_has_calls(expected_collection_deletes, any_order=True)


    def test_update_entity_with_invalid_id(self):
        """Test update_entity with invalid ID raises validation error."""
        with pytest.raises(ValueError, match="Invalid ID format"):
            self.repo.update_entity("invalid", name="test")


    def test_update_entity_with_empty_data(self):
        """Test update_entity with empty data raises validation error."""
        with pytest.raises(ValueError, match="No data provided for update"):
            self.repo.update_entity(123)


    @patch('cmn.base_repo.transaction')
    def test_update_entity_handles_database_error(self, _mock_transaction):
        """Test update_entity handles database errors gracefully."""
        kwargs = {'name': 'test'}
        mock_instance = Mock()
        self.mock_manager.get_by_id.return_value = mock_instance
        mock_instance.update.side_effect = DatabaseError("Update failed")
        
        with pytest.raises(ValueError, match="Update failed: Update failed"):
            self.repo.update_entity(123, **kwargs)
        
        # Verify the error was logged correctly
        self.mock_repo_logger.error.assert_called_once()
        logged_message = self.mock_repo_logger.error.call_args[0][0]
        assert "Failed to update ModelTest ID=123" in logged_message
        assert "Update failed" in logged_message


class BaseRepositoryDeleteEntityTests(TestClassBase):
    """Test BaseRepository delete_entity method."""

    # Allow database access for transaction-decorated methods
    databases = ['default']

    def setUp(self):
        super().setUp()
        self.repo = BaseRepository(model=self.real_test_model_as_class, cache_enabled=True)
        self.repo._manager = self.mock_manager
        self.repo._cache_manager = self.mock_cache_manager = Mock()
        
        # Mock the logger specifically for base_repo module
        self.mock_repo_logger = self._start_patch_with_cleanup("cmn.base_repo.logger")


    @patch('cmn.base_repo.transaction')
    def test_delete_entity_success(self, _mock_transaction):
        """Test delete_entity successfully removes entity."""
        mock_instance = Mock()
        self.mock_manager.get_by_id.return_value = mock_instance
        
        result = self.repo.delete_entity(123)
        
        self.mock_manager.get_by_id.assert_called_once_with(123)
        mock_instance.delete.assert_called_once()
        assert result == mock_instance
        
        self.mock_cache_manager.delete.assert_any_call("test.modeltest.123")
        expected_collection_deletes = [
            call("test.modeltest.all"),
            call("test.modeltest.count"),
            call("test.modeltest.paginated")
        ]
        self.mock_cache_manager.delete.assert_has_calls(expected_collection_deletes, any_order=True)


    def test_delete_entity_with_invalid_id(self):
        """Test delete_entity with invalid ID raises validation error."""
        with pytest.raises(ValueError, match="Invalid ID format"):
            self.repo.delete_entity("invalid")


    @patch('cmn.base_repo.transaction')
    def test_delete_entity_handles_database_error(self, _mock_transaction):
        """Test delete_entity handles database errors gracefully."""
        mock_instance = Mock()
        self.mock_manager.get_by_id.return_value = mock_instance
        mock_instance.delete.side_effect = DatabaseError("Deletion failed")
        
        with pytest.raises(ValueError, match="Deletion failed: Deletion failed"):
            self.repo.delete_entity(123)
        
        # Verify the error was logged correctly
        self.mock_repo_logger.error.assert_called_once()
        logged_message = self.mock_repo_logger.error.call_args[0][0]
        assert "Failed to delete ModelTest ID=123: Deletion failed" in logged_message


    @patch('cmn.base_repo.transaction')
    def test_delete_entity_returns_none_when_not_found(self, _mock_transaction):
        """Test delete_entity returns None when entity doesn't exist."""
        self.mock_manager.get_by_id.return_value = None
        
        result = self.repo.delete_entity(123)
        
        assert result is None


class BaseRepositoryBulkOperationsTests(TestClassBase):
    """Test BaseRepository bulk operation methods."""

    # Allow database access for transaction-decorated methods
    databases = ['default']

    def setUp(self):
        super().setUp()
        self.repo = BaseRepository(model=self.real_test_model_as_class, cache_enabled=True)
        self.repo._manager = self.mock_manager
        self.repo._cache_manager = self.mock_cache_manager = Mock()
        self.mock_instances = [self.real_mock_model, self.real_mock_model]


    @patch('cmn.base_repo.logger')  
    def test_bulk_create_entities_success(self, mock_logger):
        """Test bulk_create_entities successfully creates multiple entities."""
        # Setup
        self.mock_manager.bulk_create_instances.return_value = self.mock_instances
        
        # Mock the transaction.atomic decorator to prevent database access
        with patch('cmn.base_repo.transaction.atomic') as mock_atomic:
            mock_atomic.return_value.__enter__ = Mock(return_value=Mock())
            mock_atomic.return_value.__exit__ = Mock(return_value=None)
            
            # Execute
            result = self.repo.bulk_create_entities(self.mock_instances)
            
            # Verify manager called with correct parameters (default batch_size=100)
            self.mock_manager.bulk_create_instances.assert_called_once_with(self.mock_instances, batch_size=100)
            
            # Verify correct return value
            assert result == self.mock_instances
            
            # Verify cache invalidation calls
            expected_cache_deletes = [
                call("test.modeltest.all"),
                call("test.modeltest.count"), 
                call("test.modeltest.paginated")
            ]
            self.mock_cache_manager.delete.assert_has_calls(expected_cache_deletes, any_order=True)
            
            # Verify logging calls
            mock_logger.debug.assert_called_once_with(
                f"Starting bulk create of {len(self.mock_instances)} ModelTest instances"
            )
            mock_logger.info.assert_called_once_with(
                f"Successfully created {len(self.mock_instances)}/{len(self.mock_instances)} ModelTest instances"
            )


    def test_bulk_create_entities_with_custom_batch_size(self):
        """Test bulk_create_entities with custom batch size."""
        with patch('cmn.base_repo.transaction'):
            self.mock_manager.bulk_create_instances.return_value = self.mock_instances
            
            self.repo.bulk_create_entities(self.mock_instances, batch_size=50)
            
            self.mock_manager.bulk_create_instances.assert_called_once_with(self.mock_instances, batch_size=50)


    def test_bulk_create_entities_with_empty_list(self):
        """Test bulk_create_entities with empty instance list raises error."""
        with pytest.raises(ValueError, match="Empty instances list provided for bulk create"):
            self.repo.bulk_create_entities([])


    def test_bulk_create_entities_with_invalid_batch_size(self):
        """Test bulk_create_entities with invalid batch size raises error."""
        with pytest.raises(ValueError, match="Batch size must be a positive integer"):
            self.repo.bulk_create_entities(self.mock_instances, batch_size=0)
        
        with pytest.raises(ValueError, match="Batch size must be a positive integer"):
            self.repo.bulk_create_entities(self.mock_instances, batch_size=-1)
        
        with pytest.raises(ValueError, match="Batch size must be a positive integer"):
            self.repo.bulk_create_entities(self.mock_instances, batch_size="invalid")


    @patch('cmn.base_repo.transaction')
    def test_bulk_create_entities_manager_returns_empty(self, _mock_transaction):
        """Test bulk_create_entities raises error when manager returns empty result."""
        self.mock_manager.bulk_create_instances.return_value = []
        
        with pytest.raises(ValueError, match="Bulk create failed - no instances were created"):
            self.repo.bulk_create_entities(self.mock_instances)


    @patch('cmn.base_repo.transaction')
    def test_bulk_update_entities_success(self, _mock_transaction):
        """Test bulk_update_entities successfully updates multiple entities."""
        fields = ['name', 'value']
        self.mock_manager.bulk_update_instances.return_value = self.mock_instances
        
        result = self.repo.bulk_update_entities(self.mock_instances, fields)
        
        self.mock_manager.bulk_update_instances.assert_called_once_with(
            self.mock_instances, fields, batch_size=100
        )
        assert result == self.mock_instances


    def test_bulk_update_entities_with_empty_fields(self):
        """Test bulk_update_entities with empty fields list raises error."""
        with pytest.raises(ValueError, match="Empty fields list provided for bulk update"):
            self.repo.bulk_update_entities(self.mock_instances, [])


    @patch('cmn.base_repo.transaction')
    def test_bulk_delete_entities_with_instances(self, _mock_transaction):
        """Test bulk_delete_entities with instance list."""
        self.mock_manager.bulk_delete_instances.return_value = self.mock_instances
        
        result = self.repo.bulk_delete_entities(instances=self.mock_instances)
        
        self.mock_manager.bulk_delete_instances.assert_called_once_with()
        assert result == (self.mock_instances, len(self.mock_instances))


    @patch('cmn.base_repo.transaction')
    def test_bulk_delete_entities_with_filters(self, _mock_transaction):
        """Test bulk_delete_entities with filter criteria."""
        filters = {'status': 'inactive'}
        self.mock_manager.bulk_delete_instances.return_value = self.mock_instances
        
        result = self.repo.bulk_delete_entities(**filters)
        
        self.mock_manager.bulk_delete_instances.assert_called_once_with(**filters)
        assert result == (self.mock_instances, len(self.mock_instances))


    def test_bulk_delete_entities_with_no_criteria(self):
        """Test bulk_delete_entities without instances or filters raises error."""
        with pytest.raises(ValueError, match="Either instances list or filters must be provided for bulk delete"):
            self.repo.bulk_delete_entities()


class BaseRepositoryUtilityMethodsTests(TestClassBase):
    """Test BaseRepository utility methods."""

    def setUp(self):
        super().setUp()
        self.repo = BaseRepository(model=self.real_test_model_as_class, cache_enabled=True)
        self.repo._manager = self.mock_manager
        self.repo._cache_manager = self.mock_cache_manager = Mock()


    def test_get_entities_iterator(self):
        """Test get_entities_iterator returns an iterator that yields entities in batches."""

        # Mock the _fetch_all_entities method to return test data in batches
        batch_1 = [Mock(id=1), Mock(id=2)]
        batch_2 = [Mock(id=3)]  # Smaller final batch (< batch_size, stops iteration)
        
        with patch.object(self.repo, '_fetch_all_entities') as mock_fetch:
            mock_fetch.side_effect = [batch_1, batch_2]
            result = self.repo.get_entities_iterator(batch_size=2)
            
            # Verify it returns an iterator/generator
            assert hasattr(result, '__iter__')
            assert hasattr(result, '__next__')
            
            # Collect all yielded entities
            entities = list(result)
            
            # Verify all entities were yielded
            assert len(entities) == 3
            assert entities[0].id == 1
            assert entities[1].id == 2  
            assert entities[2].id == 3
            
            # Verify _fetch_all_entities was called with correct parameters
            # Iterator stops when batch size < requested size, so only 2 calls
            expected_calls = [
                call(limit=2, offset=0),  # First batch
                call(limit=2, offset=2),  # Second batch (smaller, stops iteration)
            ]
            mock_fetch.assert_has_calls(expected_calls)


    def test_count_entities_cache_hit(self):
        """Test count_entities returns cached count."""
        self.mock_cache_manager.get.return_value = 42
        
        result = self.repo.count_entities(status='active')
        
        self.mock_cache_manager.get.assert_called_once()
        self.mock_manager.count.assert_not_called()
        assert result == 42


    def test_count_entities_cache_miss(self):
        """Test count_entities with cache miss queries database."""

        # Setup: Cache miss scenario
        self.mock_cache_manager.get.return_value = None
        
        # Mock the filter_by chain: manager.filter_by(**filters).count()
        mock_queryset = Mock()
        mock_queryset.count.return_value = 42
        self.mock_manager.filter_by.return_value = mock_queryset
        
        # Execute the method
        result = self.repo.count_entities(status='active')
        
        # Verify cache was checked first
        self.mock_cache_manager.get.assert_called_once()
        
        # Verify database was queried with correct filters
        self.mock_manager.filter_by.assert_called_once_with(status='active')
        mock_queryset.count.assert_called_once()
        
        # Verify result was cached
        self.mock_cache_manager.set.assert_called_once()
        
        # Verify correct result returned
        assert result == 42


    def test_exists_entity_with_filters(self):
        """Test exists_entity with filter criteria."""
        self.mock_manager.exists.return_value = True
        
        result = self.repo.exists_entity(name='test')
        
        self.mock_manager.exists.assert_called_once_with(name='test')
        assert result is True


    def test_exists_entity_without_filters(self):
        """Test exists_entity without filters raises error."""
        with pytest.raises(ValueError, match="At least one filter must be provided"):
            self.repo.exists_entity()


    def test_get_paginated_entities_success(self):
        """Test get_paginated_entities returns pagination metadata."""

        # Setup test data
        test_entities = [self.real_mock_model]
        
        # Mock count_entities to return total count (called internally)
        with patch.object(self.repo, 'count_entities') as mock_count:
            mock_count.return_value = 100
            
            # Mock the manager's filter_by to return a queryset
            mock_queryset = Mock()
            mock_queryset.__getitem__ = Mock(return_value=test_entities)  # Handles slicing
            self.mock_manager.filter_by.return_value = mock_queryset
            
            # Execute the method
            result = self.repo.get_paginated_entities(page=1, per_page=10, status='active')
            
            # Verify count_entities was called with filters
            mock_count.assert_called_once_with(status='active')
            
            # Verify filter_by was called correctly
            self.mock_manager.filter_by.assert_called_once_with(status='active')
            
            # Verify queryset was sliced correctly (offset=0, limit=10)
            mock_queryset.__getitem__.assert_called_once_with(slice(0, 10))
            
            # Verify the returned pagination structure
            expected_result = {
                'entities': test_entities,
                'total_count': 100,
                'page': 1,
                'per_page': 10,
                'total_pages': 10,
                'has_next': True,
                'has_previous': False
            }
            assert result == expected_result


    def test_get_paginated_entities_with_invalid_page(self):
        """Test get_paginated_entities validates page parameter."""
        with pytest.raises(ValueError, match="Page must be a positive integer, got 0"):
            self.repo.get_paginated_entities(page=0, per_page=10)


    def test_get_paginated_entities_with_invalid_per_page(self):
        """Test get_paginated_entities validates per_page parameter."""
        with pytest.raises(ValueError, match="Per-page count must be a positive integer, got 0"):
            self.repo.get_paginated_entities(page=1, per_page=0)


class BaseRepositorySecurityTests(TestClassBase):
    """Test BaseRepository security and logging methods."""

    def setUp(self):
        super().setUp()
        self.repo = BaseRepository(model=self.real_test_model_as_class)

    def test_sanitize_log_data_removes_sensitive_fields(self):
        """Test _sanitize_log_data removes sensitive information."""
        data = {
            'username': 'testuser',
            'password': 'secret123',
            'token': 'abc123',
            'api_key': 'key456',
            'secret': 'topsecret',
            'safe_field': 'safe_value'
        }
        
        result = self.repo._sanitize_log_data(data)
        
        assert result['username'] == 'testuser'
        assert result['password'] == '[REDACTED]'
        assert result['token'] == '[REDACTED]'
        assert result['api_key'] == '[REDACTED]'
        assert result['secret'] == '[REDACTED]'
        assert result['safe_field'] == 'safe_value'

    def test_sanitize_log_data_with_none(self):
        """Test _sanitize_log_data handles None input."""
        result = self.repo._sanitize_log_data(None)
        assert result is None

    def test_sanitize_log_data_with_non_dict(self):
        """Test _sanitize_log_data handles non-dictionary input."""
        result = self.repo._sanitize_log_data("string_data")
        assert result == "string_data"


class BaseRepositoryIntegrationTests(TestClassBase):
    """Test BaseRepository integration scenarios."""

    # Allow database access for transaction-decorated methods
    databases = ['default']

    def setUp(self):
        super().setUp()
        self.repo = BaseRepository(model=self.real_test_model_as_class, cache_enabled=True)
        self.repo._manager = self.real_mock_manager
        self.repo._cache_manager = Mock()
        
        # Mock the logger specifically for base_repo module
        self.mock_repo_logger = self._start_patch_with_cleanup("cmn.base_repo.logger")


    @patch('cmn.base_repo.transaction')
    def test_create_then_get_entity_flow(self, _mock_transaction):
        """Test complete create and retrieve workflow."""
        # Set up test entity with proper ID
        created_entity = self.real_mock_model
        created_entity.id = 123
        
        # Use consistent manager setup - switch to mock_manager for proper control
        self.repo._manager = self.mock_manager
        
        # Mock to create workflow
        self.mock_manager.create_instance.return_value = created_entity
        # Mock the get workflow - cache miss first, then DB hit
        self.repo._cache_manager.get.return_value = None
        self.mock_manager.get_by_id.return_value = created_entity
        
        # Execute the create-then-get workflow
        created = self.repo.create_entity(name='test', value=42)
        retrieved = self.repo.get_entity_by_id(123)
        
        # Verify both operations return the same entity
        assert created == created_entity
        assert retrieved == created_entity
        assert created.id == 123
        assert retrieved.id == 123
        
        # Verify create operation was called correctly
        self.mock_manager.create_instance.assert_called_once_with(name='test', value=42)
        
        # Verify get operation was called correctly 
        self.mock_manager.get_by_id.assert_called_once_with(123)
        
        # Verify cache operations during the workflow
        # 1. During get: cache miss, so check cache first
        expected_cache_key = "test.modeltest.123"
        self.repo._cache_manager.get.assert_called_with(expected_cache_key)
        
        # 2. During get: cache the retrieved entity
        self.repo._cache_manager.set.assert_called_with(expected_cache_key, created_entity, 900)
        
        # 3. During create: invalidate collection caches
        expected_cache_deletes = [
            call("test.modeltest.all"),
            call("test.modeltest.count"), 
            call("test.modeltest.paginated")
        ]
        self.repo._cache_manager.delete.assert_has_calls(expected_cache_deletes, any_order=True)


    @patch('cmn.base_repo.transaction')
    def test_update_invalidates_cache_correctly(self, _mock_transaction):
        """Test update operation properly invalidates caches."""
        updated_entity = self.real_mock_model
        updated_entity.id = 123
        
        # Mock the model's update method to avoid actual database operations
        updated_entity.update = Mock()
        
        # Switch to using mock_manager for consistency with other tests
        # and to avoid transaction decorator issues
        self.repo._manager = self.mock_manager
        self.mock_manager.get_by_id.return_value = updated_entity
        result = self.repo.update_entity(123, name='updated')
        assert result == updated_entity
        
        # Verify the update method was called
        updated_entity.update.assert_called_once_with(name='updated')
        
        expected_cache_deletes = [
            call("test.modeltest.123"),
            call("test.modeltest.all"),
            call("test.modeltest.count"),
            call("test.modeltest.paginated")
        ]
        self.repo._cache_manager.delete.assert_has_calls(expected_cache_deletes, any_order=True)


    def test_error_handling_with_real_manager(self):
        """Test error handling works with real manager instance."""
        with patch.object(self.real_mock_manager, 'get_by_id', side_effect=DatabaseError("Database connection failed")):
            self.repo._cache_manager.get.return_value = None
            
            with pytest.raises(ValueError, match="Failed to fetch entity by ID"):
                self.repo.get_entity_by_id(123)
            
            # The repository logger should log the error with exc_info=True
            self.mock_repo_logger.error.assert_called_once()
            args, kwargs = self.mock_repo_logger.error.call_args
            assert "Failed to fetch ModelTest by ID=123: Database connection failed" in args[0]
            assert kwargs.get('exc_info') is True

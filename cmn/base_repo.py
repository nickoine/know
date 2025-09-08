from __future__ import annotations

# External
from django.db import models, transaction

# Internal
from abc import ABC, abstractmethod
from typing import Optional, List, Type, TypeVar, Generic, Tuple, ClassVar, Dict, Any, Iterator
from .base_cache import CacheManager
from .base_model import DBManager, logger

T = TypeVar("T", bound=models.Model)


class Repository(ABC):
    """Abstract class that defines the contract for repositories."""


    @property
    @abstractmethod
    def model(self) -> Type[T]:
        """Return the model class this repository works with."""
        pass


    @property
    @abstractmethod
    def manager(self) -> DBManager[T]:
        """Return the manager instance for the model."""
        pass


    @abstractmethod
    def get_entity_by_id(self, obj_id: int) -> Optional[T]:
        """Fetch an entity by ID."""
        pass


    @abstractmethod
    def get_all_entities(self) -> List[T]:
        """Fetch all entities."""
        pass


    @abstractmethod
    def create_entity(self, **kwargs) -> Optional[T]:
        """Create a new entity."""
        pass


    @abstractmethod
    def update_entity(self, obj_id: int, **kwargs) -> Optional[T]:
        """Update an entity."""
        pass


    @abstractmethod
    def delete_entity(self, obj_id: int) -> Optional[T]:
        """Delete an entity."""
        pass


    @abstractmethod
    def bulk_create_entities(self, instances: List[T]) -> List[T]:
        """Bulk create new entities."""
        pass


    @abstractmethod
    def bulk_update_entities(self, instances: List[T], fields: List[str]) -> List[T]:
        """Bulk update entities."""
        pass


    @abstractmethod
    def bulk_delete_entities(self, instances: List[T], **filters) -> Tuple[List[T], int]:
        """Bulk delete entities."""
        pass


class BaseRepository(Repository, Generic[T]):

    """Base repository implementation with caching.
       Subclasses must define a `_model` class attribute pointing to a Django model."""

    CACHE_TIMEOUT = 60 * 15
    CACHE_KEY_FORMAT: ClassVar[str] = "{app_label}.{model_name}.{id}"

    _model: Type[T] = None
    _cache_enabled: bool = False
    _cache_manager: CacheManager
    _manager: Optional[DBManager[T]] = None


    def __init__(self, model: Type[T] = None, cache_enabled: bool = False) -> None:
        """Initialize repository with a model and caching option."""

        self._model = model or self._model
        if self._model is None:
            raise ValueError("Repository must have a ._model defined")
        self._cache_enabled = cache_enabled
        self._cache_manager = CacheManager()


    @property
    def model(self) -> Type[T]:
        """Return the model class this repository works with."""

        if not getattr(self, "_model", None):
            raise ValueError(f"{self.__class__.__name__} must define a `_model` class attribute.")
        return self._model  # type: ignore[return-value]


    @property
    def manager(self) -> DBManager[T]:
        """Return the manager instance for the model (lazy loaded with type safety)."""

        if self._manager is None:
            if not hasattr(self.model, "objects") or not isinstance(self.model.objects, models.Manager):
                model_class_name = self.model.__name__ if isinstance(self.model, type) else type(
                    self.model).__name__
                raise TypeError(f"{model_class_name} must have a valid Manager.")
            self._manager = self.model.objects  # type: ignore[assignment]
        return self._manager


    @property
    def cache_enabled(self) -> bool:
        return self._cache_enabled


    def _get_cache_key(self, obj_id: int, suffix: str = "") -> str:
        """Generate a cache key using the defined format with namespace isolation."""

        app_label = getattr(self.model._meta, 'app_label', 'default')
        model_name = self.model.__name__.lower()
        
        if suffix:
            return f"{app_label}.{model_name}.{obj_id}.{suffix}"
        return f"{app_label}.{model_name}.{obj_id}"


    def _get_collection_cache_key(self, suffix: str = "all") -> str:
        """Generate cache key for collection operations."""

        app_label = getattr(self.model._meta, 'app_label', 'default')
        model_name = self.model.__name__.lower()
        return f"{app_label}.{model_name}.{suffix}"


    @staticmethod
    def _validate_id(obj_id: Any) -> int:
        """Validate and convert ID to integer."""

        if obj_id is None:
            raise ValueError("ID cannot be None")
        
        if isinstance(obj_id, str):
            if not obj_id.strip():
                raise ValueError("ID cannot be empty string")
            if not obj_id.isdigit():
                raise ValueError(f"Invalid ID format: '{obj_id}' must be a positive integer")
            obj_id = int(obj_id)
        
        if not isinstance(obj_id, int):
            raise ValueError(f"ID must be an integer, got {type(obj_id).__name__}")
        
        if obj_id <= 0:
            raise ValueError(f"ID must be positive, got {obj_id}")
        
        return obj_id


    @staticmethod
    def _validate_kwargs(kwargs: Optional[Dict[str, Any]], operation: str = "operation") -> Dict[str, Any]:
        """Validate kwargs for create/update operations."""

        if not kwargs:
            raise ValueError(f"No data provided for {operation}")
        
        if not isinstance(kwargs, dict):
            raise ValueError(f"Data for {operation} must be a dictionary")
        
        # Remove None values and empty strings
        cleaned_kwargs = {k: v for k, v in kwargs.items() if v is not None and v != ""}
        
        if not cleaned_kwargs:
            raise ValueError(f"No valid data provided for {operation} after cleaning")
        
        return cleaned_kwargs


    @staticmethod
    def _validate_instances_list(instances: Optional[List[T]], operation: str = "operation") -> List[T]:
        """Validate list of instances for bulk operations."""

        if not isinstance(instances, list):
            raise ValueError(f"Instances must be a list for {operation}")
        
        if not instances:
            raise ValueError(f"Empty instances list provided for {operation}")
        
        # Validate each instance is of correct type
        for i, instance in enumerate(instances):
            if not isinstance(instance, models.Model):
                raise ValueError(
                    f"Instance at index {i} is not a Django model instance, got {type(instance).__name__}"
                )
        
        return instances


    @staticmethod
    def _validate_fields_list(fields: List[str], operation: str = "operation") -> List[str]:
        """Validate list of field names for bulk operations."""

        if not isinstance(fields, list):
            raise ValueError(f"Fields must be a list for {operation}")
        
        if not fields:
            raise ValueError(f"Empty fields list provided for {operation}")
        
        # Validate each field is a string
        for i, field in enumerate(fields):
            if not isinstance(field, str) or not field.strip():
                raise ValueError(
                    f"Field at index {i} must be a non-empty string, got {type(field).__name__}"
                )
        
        return [field.strip() for field in fields]


    def _sanitize_log_data(self, data: Any) -> Any:
        """Sanitize sensitive data from logs."""

        if isinstance(data, dict):
            sanitized = {}
            sensitive_fields = {'password', 'token', 'secret', 'key', 'api_key', 'auth', 'credential'}
            
            for key, value in data.items():
                if any(sensitive in key.lower() for sensitive in sensitive_fields):
                    sanitized[key] = "[REDACTED]"
                else:
                    sanitized[key] = self._sanitize_log_data(value)
            return sanitized
        elif isinstance(data, (list, tuple)):
            return [self._sanitize_log_data(item) for item in data]
        elif isinstance(data, str) and len(data) > 100:
            # Truncate long strings
            return data[:100] + "...[TRUNCATED]"
        return data


    def _invalidate_collection_caches(self) -> None:
        """Invalidate all collection-related cache entries."""

        if not self._cache_enabled:
            return
        
        try:
            # Invalidate common collection cache keys
            cache_keys = [
                self._get_collection_cache_key("all"),
                self._get_collection_cache_key("count"),
                self._get_collection_cache_key("paginated"),
            ]
            
            for cache_key in cache_keys:
                self._cache_manager.delete(cache_key)
                
        except Exception as e:
            logger.warning(
                f"Failed to invalidate collection caches for {self.model.__name__}: {str(e)}"
            )


    def _safe_cache_operation(self, operation: str, key: str, value: Any = None, timeout: int = None) -> Any:
        """Safely perform cache operations with error handling."""

        if not self._cache_enabled:
            return None
        try:
            if operation == "get":
                return self._cache_manager.get(key)
            elif operation == "set":
                self._cache_manager.set(key, value, timeout or self.CACHE_TIMEOUT)
                return True
            elif operation == "delete":
                self._cache_manager.delete(key)
                return True
            elif operation == "get_or_set":
                return self._cache_manager.get_or_set(key, value, timeout or self.CACHE_TIMEOUT)
        except Exception as e:
            logger.warning(
                f"Cache {operation} operation failed for key '{key}': {str(e)}"
            )
            return None


    def get_entity_by_id(self, obj_id: int) -> Optional[T]:
        """Fetch a single model instance by its ID with caching and comprehensive validation.
        
        Args:
            obj_id: The ID of the entity to fetch
            
        Returns:
            The entity instance or None if not found
            
        Raises:
            ValueError: If obj_id is invalid
        """
        try:
            validated_id = BaseRepository._validate_id(obj_id)
            cache_key = self._get_cache_key(validated_id)
            
            # Try cache first
            cached_instance = self._safe_cache_operation("get", cache_key)
            if cached_instance is not None:
                logger.debug(f"Cache hit for {self.model.__name__} ID={validated_id}")
                return cached_instance
            
            # Fetch from database
            instance = self.manager.get_by_id(validated_id)
            
            # Cache the result if found
            if instance is not None:
                self._safe_cache_operation("set", cache_key, instance)
                logger.debug(f"Fetched and cached {self.model.__name__} ID={validated_id}")
            else:
                logger.debug(f"{self.model.__name__} with ID={validated_id} not found")
            
            return instance
            
        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            sanitized_id = self._sanitize_log_data(obj_id)
            logger.error(
                f"Failed to fetch {self.model.__name__} by ID={sanitized_id}: {str(e)}",
                exc_info=True
            )
            raise ValueError(f"Failed to fetch entity by ID: {str(e)}") from e


    def get_all_entities(self, limit: Optional[int] = None, offset: int = 0) -> List[T]:
        """
        Fetch all instances with optional caching and pagination support.
        
        Args:
            limit: Maximum number of entities to return (None for all)
            offset: Number of entities to skip
            
        Returns:
            List of entity instances
            
        Raises:
            ValueError: If parameters are invalid or data retrieval fails
        """
        try:
            # Validate pagination parameters
            if limit is not None:
                if not isinstance(limit, int) or limit <= 0:
                    raise ValueError(f"Limit must be a positive integer, got {limit}")
            
            if not isinstance(offset, int) or offset < 0:
                raise ValueError(f"Offset must be a non-negative integer, got {offset}")
            
            # Generate cache key based on pagination
            cache_suffix = f"all.limit_{limit}.offset_{offset}" if limit else "all"
            cache_key = self._get_collection_cache_key(cache_suffix)
            
            # Try cache first
            if self._cache_enabled:
                cached_entities = self._safe_cache_operation("get", cache_key)
                if cached_entities is not None:
                    logger.debug(
                        f"Cache hit for {self.model.__name__} collection (limit={limit}, offset={offset})"
                    )
                    return cached_entities
            
            # Fetch from database
            entities = self._fetch_all_entities(limit, offset)
            
            # Cache the result
            self._safe_cache_operation("set", cache_key, entities, timeout=600)
            
            return entities
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(
                f"Failed to fetch {self.model.__name__} instances: {str(e)}",
                exc_info=True
            )
            raise ValueError(f"Failed to fetch instances: {str(e)}") from e


    def _fetch_all_entities(self, limit: Optional[int] = None, offset: int = 0) -> List[T]:
        """Internal method to fetch entities from database with pagination."""

        try:
            queryset = self.manager.get_all()
            
            if offset > 0:
                queryset = queryset[offset:]
            
            if limit is not None:
                queryset = queryset[:limit]
            
            entities = list(queryset)
            logger.debug(
                f"Successfully fetched {len(entities)} {self.model.__name__} instances "
                f"(limit={limit}, offset={offset})"
            )
            return entities
            
        except Exception as e:
            logger.error(
                f"Failed to fetch {self.model.__name__} instances from DB: {str(e)}",
                exc_info=True
            )
            raise


    def get_entities_iterator(self, batch_size: int = 100) -> Iterator[T]:
        """
        Memory-efficient iterator for processing large datasets.
        
        Args:
            batch_size: Number of entities to fetch per batch
            
        Yields:
            Individual entity instances
            
        Raises:
            ValueError: If batch_size is invalid
        """
        if not isinstance(batch_size, int) or batch_size <= 0:
            raise ValueError(f"Batch size must be a positive integer, got {batch_size}")
        
        try:
            offset = 0
            while True:
                batch = self._fetch_all_entities(limit=batch_size, offset=offset)
                if not batch:
                    break
                
                for entity in batch:
                    yield entity
                
                if len(batch) < batch_size:
                    # Last batch
                    break
                
                offset += batch_size
                
        except Exception as e:
            logger.error(
                f"Error in entities iterator for {self.model.__name__}: {str(e)}",
                exc_info=True
            )
            raise ValueError(f"Iterator failed: {str(e)}") from e


    @transaction.atomic
    def create_entity(self, **kwargs) -> Optional[T]:
        """
        Create an instance with comprehensive validation and cache management.
        
        Args:
            **kwargs: Field values for the new entity
            
        Returns:
            The created entity instance or None if creation fails
            
        Raises:
            ValueError: If validation fails or creation fails
        """
        try:
            # Validate input data
            validated_kwargs = BaseRepository._validate_kwargs(kwargs, "create")
            sanitized_data = self._sanitize_log_data(validated_kwargs)
            
            logger.debug(f"Creating {self.model.__name__} with data: {sanitized_data}")
            
            # Create the instance
            instance = self.manager.create_instance(**validated_kwargs)
            
            if not instance:
                raise ValueError("Failed to create entity - manager returned None")
            
            # Invalidate collection caches
            self._invalidate_collection_caches()
            
            logger.info(f"Successfully created {self.model.__name__} with ID={instance.id}")
            return instance
            
        except ValueError:
            raise
        except Exception as e:
            sanitized_data = self._sanitize_log_data(kwargs)
            logger.error(
                f"Unexpected error creating {self.model.__name__} with data {sanitized_data}: {str(e)}",
                exc_info=True
            )
            raise ValueError(f"Failed to create entity: {str(e)}") from e


    @transaction.atomic
    def update_entity(self, obj_id: int, **kwargs) -> Optional[T]:
        """
        Update an instance with comprehensive validation and cache management.
        
        Args:
            obj_id: ID of the entity to update
            **kwargs: Fields to update
            
        Returns:
            Updated entity or None if not found
            
        Raises:
            ValueError: If validation fails or update fails
        """
        try:
            # Validate inputs
            validated_id = BaseRepository._validate_id(obj_id)
            validated_kwargs = BaseRepository._validate_kwargs(kwargs, "update")
            sanitized_data = self._sanitize_log_data(validated_kwargs)
            
            # Retrieve the instance
            instance = self.manager.get_by_id(validated_id)
            if not instance:
                logger.warning(f"Update failed: {self.model.__name__} with ID {validated_id} not found")
                return None
            
            # Perform the update
            instance.update(**validated_kwargs)
            
            # Clear caches
            cache_key = self._get_cache_key(validated_id)
            self._safe_cache_operation("delete", cache_key)
            self._invalidate_collection_caches()
            
            logger.info(
                f"Successfully updated {self.model.__name__} ID={validated_id} "
                f"with data: {sanitized_data}"
            )
            
            return instance
            
        except ValueError:
            raise
        except Exception as e:
            sanitized_id = self._sanitize_log_data(obj_id)
            sanitized_data = self._sanitize_log_data(kwargs)
            logger.error(
                f"Failed to update {self.model.__name__} ID={sanitized_id} "
                f"with data {sanitized_data}: {str(e)}",
                exc_info=True
            )
            raise ValueError(f"Update failed: {str(e)}") from e


    @transaction.atomic
    def delete_entity(self, obj_id: int) -> Optional[T]:
        """
        Delete an instance with comprehensive validation and cache management.
        
        Args:
            obj_id: ID of the entity to delete
            
        Returns:
            The deleted entity instance or None if not found
            
        Raises:
            ValueError: If validation fails or deletion fails
        """
        try:
            # Validate input
            validated_id = BaseRepository._validate_id(obj_id)
            
            # Retrieve the instance
            instance = self.manager.get_by_id(validated_id)
            if not instance:
                logger.warning(f"Delete failed: {self.model.__name__} with ID {validated_id} not found")
                return None
            
            # Delete the instance
            instance.delete()
            
            # Clear caches
            cache_key = self._get_cache_key(validated_id)
            self._safe_cache_operation("delete", cache_key)
            self._invalidate_collection_caches()
            
            logger.info(f"Successfully deleted {self.model.__name__} ID={validated_id}")
            
            return instance
            
        except ValueError:
            raise
        except Exception as e:
            sanitized_id = self._sanitize_log_data(obj_id)
            logger.error(
                f"Failed to delete {self.model.__name__} ID={sanitized_id}: {str(e)}",
                exc_info=True
            )
            raise ValueError(f"Deletion failed: {str(e)}") from e


    @transaction.atomic
    def bulk_create_entities(self, instances: List[T], batch_size: int = 100) -> List[T]:
        """
        Bulk create instances with comprehensive validation and efficient cache management.
        
        Args:
            instances: List of entity instances to create
            batch_size: Number of instances to create per batch
            
        Returns:
            List of successfully created instances
            
        Raises:
            ValueError: If validation fails or creation fails
        """
        try:
            # Validate inputs
            validated_instances = self._validate_instances_list(instances, "bulk create")
            
            if not isinstance(batch_size, int) or batch_size <= 0:
                raise ValueError(f"Batch size must be a positive integer, got {batch_size}")
            
            logger.debug(
                f"Starting bulk create of {len(validated_instances)} {self.model.__name__} instances"
            )
            
            # Perform bulk creation
            created_instances = self.manager.bulk_create_instances(
                validated_instances, batch_size=batch_size
            )
            
            if not created_instances:
                raise ValueError("Bulk create failed - no instances were created")
            
            # Invalidate collection caches (more efficient than individual cache keys)
            self._invalidate_collection_caches()
            
            logger.info(
                f"Successfully created {len(created_instances)}/{len(validated_instances)} "
                f"{self.model.__name__} instances"
            )
            
            return created_instances
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error during bulk create of {self.model.__name__}: {str(e)}",
                exc_info=True
            )
            raise ValueError(f"Bulk create failed: {str(e)}") from e


    @transaction.atomic
    def bulk_update_entities(self, instances: List[T], fields: List[str], batch_size: int = 100) -> List[T]:
        """
        Bulk update multiple instances with comprehensive validation and efficient cache management.
        
        Args:
            instances: List of entity instances to update
            fields: List of field names being updated
            batch_size: Number of instances to update per batch
            
        Returns:
            List of successfully updated instances
            
        Raises:
            ValueError: If validation fails or bulk update fails
        """
        try:
            # Validate inputs
            validated_instances = self._validate_instances_list(instances, "bulk update")
            validated_fields = self._validate_fields_list(fields, "bulk update")
            
            if not isinstance(batch_size, int) or batch_size <= 0:
                raise ValueError(f"Batch size must be a positive integer, got {batch_size}")
            
            sanitized_fields = self._sanitize_log_data(validated_fields)
            logger.debug(
                f"Starting bulk update of {len(validated_instances)} {self.model.__name__} instances "
                f"(fields: {sanitized_fields})"
            )
            
            # Perform bulk update
            updated_instances = self.manager.bulk_update_instances(
                validated_instances, validated_fields, batch_size=batch_size
            )
            
            if not updated_instances:
                raise ValueError("Bulk update failed - no instances were updated")
            
            # Invalidate collection caches (more efficient than individual cache keys)
            self._invalidate_collection_caches()
            
            logger.info(
                f"Successfully updated {len(updated_instances)}/{len(validated_instances)} "
                f"{self.model.__name__} instances (fields: {sanitized_fields})"
            )
            
            return updated_instances
            
        except ValueError:
            raise
        except Exception as e:
            sanitized_fields = self._sanitize_log_data(fields) if fields else "None"
            logger.error(
                f"Unexpected error during bulk update of {self.model.__name__} instances "
                f"(fields: {sanitized_fields}): {str(e)}",
                exc_info=True
            )
            raise ValueError(f"Bulk update failed: {str(e)}") from e


    @transaction.atomic
    def bulk_delete_entities(self, instances: Optional[List[T]] = None, **filters) -> Tuple[List[T], int]:
        """
        Bulk delete multiple instances with comprehensive validation and efficient cache management.
        
        Args:
            instances: Optional list of entity instances for validation (can be None if using filters)
            **filters: Filters to identify instances to delete
            
        Returns:
            Tuple containing:
            - List of successfully deleted instances
            - Count of deleted instances
            
        Raises:
            ValueError: If validation fails or bulk deletion fails
        """
        try:
            # Validate inputs - either instances or filters must be provided
            if instances is not None:
                self._validate_instances_list(instances, "bulk delete")
            
            if not filters and instances is None:
                raise ValueError("Either instances list or filters must be provided for bulk delete")
            
            if not isinstance(filters, dict):
                raise ValueError("Filters must be a dictionary")
            
            sanitized_filters = self._sanitize_log_data(filters)
            logger.debug(
                f"Starting bulk delete of {self.model.__name__} instances "
                f"(filters: {sanitized_filters})"
            )
            
            # Perform bulk deletion
            deleted_instances = self.manager.bulk_delete_instances(**filters)
            deleted_count = len(deleted_instances)
            
            # Invalidate collection caches (more efficient than individual cache keys)
            self._invalidate_collection_caches()
            
            logger.info(
                f"Successfully deleted {deleted_count} {self.model.__name__} instances "
                f"(filters: {sanitized_filters})"
            )
            
            return deleted_instances, deleted_count
            
        except ValueError:
            raise
        except Exception as e:
            sanitized_filters = self._sanitize_log_data(filters)
            logger.error(
                f"Unexpected error during bulk delete of {self.model.__name__} instances "
                f"(filters: {sanitized_filters}): {str(e)}",
                exc_info=True
            )
            raise ValueError(f"Bulk delete failed: {str(e)}") from e


    def count_entities(self, **filters) -> int:
        """
        Count entities with optional filtering and caching.
        
        Args:
            **filters: Optional filters to apply
            
        Returns:
            Number of entities matching the filters
            
        Raises:
            ValueError: If count operation fails
        """
        try:
            # Validate filters
            if filters and not isinstance(filters, dict):
                raise ValueError("Filters must be a dictionary")
            
            # Generate cache key based on filters
            filters_str = "_".join(f"{k}_{v}" for k, v in sorted(filters.items())) if filters else "all"
            cache_key = self._get_collection_cache_key(f"count_{filters_str}")
            
            # Try cache first
            cached_count = self._safe_cache_operation("get", cache_key)
            if cached_count is not None:
                logger.debug(f"Cache hit for {self.model.__name__} count (filters: {filters})")
                return cached_count
            
            # Count from database
            if filters:
                count = self.manager.filter_by(**filters).count()
            else:
                count = self.manager.count()
            
            # Cache the result
            self._safe_cache_operation("set", cache_key, count, timeout=300)  # 5-minute cache
            
            logger.debug(f"Counted {count} {self.model.__name__} instances (filters: {filters})")
            return count
            
        except ValueError:
            raise
        except Exception as e:
            sanitized_filters = self._sanitize_log_data(filters)
            logger.error(
                f"Failed to count {self.model.__name__} instances "
                f"(filters: {sanitized_filters}): {str(e)}",
                exc_info=True
            )
            raise ValueError(f"Count operation failed: {str(e)}") from e


    def exists_entity(self, **filters) -> bool:
        """
        Check if any entities exist with the given filters.
        
        Args:
            **filters: Filters to check existence
            
        Returns:
            True if at least one entity exists, False otherwise
            
        Raises:
            ValueError: If existence check fails
        """
        try:
            if not filters:
                raise ValueError("At least one filter must be provided for existence check")
            
            if not isinstance(filters, dict):
                raise ValueError("Filters must be a dictionary")
            
            # Use manager's exists method for efficiency
            exists = self.manager.exists(**filters)
            
            sanitized_filters = self._sanitize_log_data(filters)
            logger.debug(
                f"Existence check for {self.model.__name__} (filters: {sanitized_filters}): {exists}"
            )
            
            return exists
            
        except ValueError:
            raise
        except Exception as e:
            sanitized_filters = self._sanitize_log_data(filters)
            logger.error(
                f"Failed existence check for {self.model.__name__} "
                f"(filters: {sanitized_filters}): {str(e)}",
                exc_info=True
            )
            raise ValueError(f"Existence check failed: {str(e)}") from e


    def clear_cache(self, obj_id: Optional[int] = None) -> None:
        """
        Clear cache entries for this repository.
        
        Args:
            obj_id: If provided, clear cache for specific entity. If None, clear all collection caches.
            
        Raises:
            ValueError: If obj_id is invalid
        """
        try:
            if obj_id is not None:
                # Clear specific entity cache
                validated_id = BaseRepository._validate_id(obj_id)
                cache_key = self._get_cache_key(validated_id)
                self._safe_cache_operation("delete", cache_key)
                logger.debug(f"Cleared cache for {self.model.__name__} ID={validated_id}")
            else:
                # Clear collection caches
                self._invalidate_collection_caches()
                logger.debug(f"Cleared collection caches for {self.model.__name__}")
                
        except ValueError:
            raise
        except Exception as e:
            logger.error(
                f"Failed to clear cache for {self.model.__name__}: {str(e)}",
                exc_info=True
            )
            # Don't raise here - cache clearing is not critical for business logic


    def get_paginated_entities(self, page: int = 1, per_page: int = 20, **filters) -> Dict[str, Any]:
        """
        Get paginated entities with comprehensive pagination information.
        
        Args:
            page: Page number (1-based)
            per_page: Number of entities per page
            **filters: Optional filters to apply
            
        Returns:
            Dictionary containing:
            - entities: List of entities for the current page
            - total_count: Total number of entities
            - page: Current page number
            - per_page: Entities per page
            - total_pages: Total number of pages
            - has_next: Whether there is a next page
            - has_previous: Whether there is a previous page
            
        Raises:
            ValueError: If pagination parameters are invalid
        """
        try:
            # Validate pagination parameters
            if not isinstance(page, int) or page < 1:
                raise ValueError(f"Page must be a positive integer, got {page}")
            
            if not isinstance(per_page, int) or per_page < 1:
                raise ValueError(f"Per-page count must be a positive integer, got {per_page}")
            
            if per_page > 1000:  # Reasonable limit
                raise ValueError(f"Per-page count too large, maximum is 1000, got {per_page}")
            
            # Get total count
            total_count = self.count_entities(**filters)
            
            # Calculate pagination
            total_pages = (total_count + per_page - 1) // per_page  # Ceiling division
            offset = (page - 1) * per_page
            
            # Get entities for current page
            if filters:
                queryset = self.manager.filter_by(**filters)
                entities = list(queryset[offset:offset + per_page])
            else:
                entities = self._fetch_all_entities(limit=per_page, offset=offset)
            
            result = {
                'entities': entities,
                'total_count': total_count,
                'page': page,
                'per_page': per_page,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_previous': page > 1
            }
            
            sanitized_filters = self._sanitize_log_data(filters)
            logger.debug(
                f"Retrieved page {page} of {self.model.__name__} entities "
                f"(per_page={per_page}, total={total_count}, filters: {sanitized_filters})"
            )
            
            return result
            
        except ValueError:
            raise
        except Exception as e:
            sanitized_filters = self._sanitize_log_data(filters)
            logger.error(
                f"Failed to get paginated {self.model.__name__} entities "
                f"(page={page}, per_page={per_page}, filters: {sanitized_filters}): {str(e)}",
                exc_info=True
            )
            raise ValueError(f"Pagination failed: {str(e)}") from e

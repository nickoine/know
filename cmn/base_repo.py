from __future__ import annotations

# External
from django.db import models

# Internal
from abc import ABC, abstractmethod
from typing import Optional, List, Type, TypeVar, Generic, Tuple, ClassVar
from .base_cache import CacheManager
from .base_model import DBManager, logger

T = TypeVar("T", bound=models.Model)


class Repository(ABC):
    """Abstract class that defines the contract for repositories."""

    _manager: DBManager = None


    @property
    @abstractmethod
    def model(self) -> Type[T]:
        """Return the model class this repository works with."""
        if not getattr(self, "_model", None):
            raise ValueError(f"{self.__class__.__name__} must define a `_model` class attribute.")
        return self._model  # type: ignore[return-value]


    @property
    def manager(self) -> DBManager[T]:
        """Return the manager instance for the model (lazy loaded)."""

        if self._manager is None:
            if not hasattr(self.model, "objects") or not isinstance(self.model.objects, models.Manager):
                model_class_name = self.model.__name__ if isinstance(self.model, type) else type(
                    self.model).__name__
                raise TypeError(f"{model_class_name} must have a valid Manager.")

            self._manager = self.model.objects
        return self._manager


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


    def __init__(self, model: Type[T] = None, cache_enabled: bool = False) -> None:
        """Initialize repository with a model and caching option."""

        self._model = model or self._model
        if self._model is None:
            raise ValueError("Repository must have a ._model defined")
        self._cache_enabled = cache_enabled
        self._cache_manager = CacheManager()



    @property
    def model(self) -> Type[T]:
        return super().model


    @property
    def cache_enabled(self) -> bool:
        return self._cache_enabled


    def _get_cache_key(self, obj_id: int) -> str:
        """Generate a cache key for the given instance."""
        return f"{self.model.__name__.lower()}:{obj_id}"


    def get_entity_by_id(self, obj_id: int) -> Optional[T]:
        """Fetch a single model instance by its ID with caching."""

        cache_key = self._get_cache_key(obj_id)

        if self._cache_enabled:
            cached = self._cache_manager.get(cache_key)
            if cached:
                return cached

        try:
            instance = self.manager.get_by_id(obj_id)
        except Exception as e:
            logger.exception(f"Failed to fetch {self.model.__name__} by ID={obj_id}: {e}")
            return None

        if instance and self._cache_enabled:
            self._cache_manager.set(cache_key, instance, timeout=self.CACHE_TIMEOUT)

        return instance


    def get_all_entities(self) -> List[T]:
        """
        Fetch all instances with optional caching.

        Returns:
            List of all entity instances

        Raises:
            ValueError: If data retrieval fails
        """
        cache_key = f"{self.model.__name__.lower()}_all"

        try:
            if self._cache_enabled:
                try:
                    return self._cache_manager.get_or_set(
                        cache_key,
                        lambda: self._fetch_all_entities(),
                        timeout=600
                    )

                except Exception as cache_error:
                    logger.warning(
                        f"Cache operation failed for {self.model.__name__}, "
                        f"falling back to direct fetch: {str(cache_error)}"
                    )
                    return self._fetch_all_entities()

            return self._fetch_all_entities()

        except Exception as e:
            logger.error(
                f"Failed to fetch all {self.model.__name__} instances: {str(e)}",
                exc_info=True
            )
            raise ValueError(f"Failed to fetch instances: {str(e)}") from e


    def _fetch_all_entities(self) -> List[T]:
        """Internal method to fetch entities without caching."""

        try:
            entities = list(self.manager.get_all())
            logger.info(f"Successfully fetched {len(entities)} {self.model.__name__} instances")
            return entities

        except Exception as e:
            logger.error(
                f"Failed to fetch {self.model.__name__} instances from DB: {str(e)}",
                exc_info=True
            )
            raise


    # @transaction.atomic
    def create_entity(self, **kwargs) -> Optional[T]:
        """Create an instance and invalidate relevant cache."""

        try:
            instance = self.manager.create_instance(**kwargs)
            if not instance:
                logger.warning(f"Failed to create entity with data: {kwargs}")
                return None

            if self._cache_enabled:
                self._cache_manager.delete(self._get_cache_key(instance.id))

            return instance

        except Exception as e:
            logger.exception(f"Unexpected error in create_entity: {e}")
            return None


    # @transaction.atomic
    def update_entity(self, obj_id: int, **kwargs) -> Optional[T]:
        """
        Update an instance and clear relevant cache.

        Args:
            obj_id: ID of the entity to update
            **kwargs: Fields to update

        Returns:
            Updated entity or None if not found

        Raises:
            ValueError: If update fails
        """
        # Retrieve the instance
        instance = self.manager.get_by_id(obj_id)
        if not instance:
            logger.warning(
                f"Update failed: {self.model.__name__} with ID {obj_id} not found"
            )
            return None

        # Perform the update
        try:
            instance.update(**kwargs)
        except Exception as update_error:
            logger.error(
                f"Failed to update {self.model.__name__} {obj_id}: {str(update_error)}",
                exc_info=True
            )
            raise ValueError(f"Update failed: {str(update_error)}") from update_error

        # Clear cache if enabled
        if self._cache_enabled:
            try:
                self._cache_manager.delete(self._get_cache_key(obj_id))
            except Exception as cache_error:
                logger.error(
                    f"Failed to clear cache for {self.model.__name__}: {obj_id}"
                    f"{str(cache_error)}",
                    exc_info=True
                )
                # Continue despite cache error - business logic should still work

        return instance

    # def _clear_cache_safely(self, obj_id: str) -> None:
    #     """Gracefully handle cache clearing without affecting main operation."""
    #     try:
    #         self._cache_manager.delete(self._get_cache_key(obj_id))
    #     except Exception as cache_error:
    #         logger.warning(
    #             f"Cache clearance warning for {self.model.__name__}:{obj_id}. "
    #             f"System will continue but cached data may be stale. Error: {cache_error}"
    #         )
    #         # Metrics or monitoring hook could be added here
    #         # e.g., track_cache_clearance_failure()


    # @transaction.atomic
    def delete_entity(self, obj_id: int) -> Optional[T]:
        """
        Delete an instance and clear its cache entry.

        Args:
            obj_id: ID of the entity to delete

        Returns:
            The deleted entity instance or None if not found

        Raises:
            ValueError: If deletion fails
        """
        instance = self.manager.get_by_id(obj_id)
        if not instance:
            logger.warning(
                f"Delete failed: {self.model.__name__} with ID {obj_id} not found"
            )
            return None

        try:
            instance.delete()
        except Exception as delete_error:
            logger.error(
                f"Failed to delete {self.model.__name__} {obj_id}: {str(delete_error)}",
                exc_info=True
            )
            raise ValueError(f"Deletion failed: {str(delete_error)}") from delete_error

        if self._cache_enabled:
            try:
                self._cache_manager.delete(self._get_cache_key(obj_id))
            except Exception as cache_error:
                logger.error(
                    f"Failed to clear cache for deleted {self.model.__name__}: {obj_id}"
                    f"{str(cache_error)}",
                    exc_info=True
                )
                # Continue despite cache error - main deletion succeeded

        return instance


    # @transaction.atomic
    def bulk_create_entities(self, instances: List[T]) -> List[T]:
        """
        Bulk create instances and invalidate cache keys (if enabled).

        This method performs a batch insert and optionally clears per-entity cache
        based on each instance's `id`.

        Returns:
            List of successfully created instances.

        Raises:
            ValueError: If database creation fails.
        """
        if not instances:
            logger.debug("Empty instances list provided for bulk create")
            return []

        try:
            # Bulk insert
            created_instances = self.manager.bulk_create_instances(instances)
            logger.info(
                f"Successfully created {len(created_instances)}/{len(instances)} "
                f"{self.model.__name__} instances"
            )

            # Invalidate cache
            if self._cache_enabled:
                failed = []
                for instance in created_instances:

                    try:
                        self._cache_manager.delete(self._get_cache_key(instance.id))
                    except Exception as e:
                        failed.append(instance.id)
                        logger.warning(
                            f"Failed to invalidate cache for {self.model.__name__}({instance.id}): {e}"
                        )

                if failed:
                    logger.warning(
                        f"Cache invalidation failed for {len(failed)} {self.model.__name__} instances: {failed}"
                    )

            return created_instances

        except Exception as e:
            logger.exception(f"Unexpected error during bulk create of {self.model.__name__}: {e}")
            raise


    # @transaction.atomic
    def bulk_update_entities(self, instances: List[T], fields: List[str]) -> List[T]:
        """
        Bulk update multiple instances and manage cache invalidation.

        Args:
            instances: List of entity instances to update
            fields: List of field names being updated

        Returns:
            List of successfully updated instances

        Raises:
            ValueError: If bulk update fails
        """
        if not instances:
            logger.debug("Empty instances list provided for bulk update")
            return []

        if not fields:
            logger.warning("Empty fields list provided for bulk update")
            raise ValueError("At least one field must be specified for update")

        try:
            updated_instances = self.manager.bulk_update_instances(instances, fields)
            logger.info(
                f"Successfully updated {len(updated_instances)}/{len(instances)} "
                f"{self.model.__name__} instances (fields: {fields})"
            )

            # Handle cache invalidation if enabled
            if self._cache_enabled and updated_instances:
                failed_cache_deletes = []

                for instance in updated_instances:
                    try:
                        self._cache_manager.delete(self._get_cache_key(getattr(instance, 'id', None)))

                    except Exception as cache_error:
                        failed_cache_deletes.append(getattr(instance, 'id', 'unknown'))
                        logger.warning(
                            f"Failed to clear cache for {self.model.__name__} instance: "
                            f"{getattr(instance, 'id', 'unknown')}. Error: {str(cache_error)}"
                        )

                if failed_cache_deletes:
                    logger.warning(
                        f"Failed to clear cache for {len(failed_cache_deletes)} "
                        f"{self.model.__name__} instances (IDs: {failed_cache_deletes})"
                    )

            return updated_instances

        except Exception as update_error:
            logger.error(
                f"Unexpected error during bulk update of {self.model.__name__} instances",
                exc_info=True
            )
            raise ValueError(f"Bulk update failed: {str(update_error)}") from update_error


    # @transaction.atomic
    def bulk_delete_entities(self, instances: List[T], **filters) -> Tuple[List[T], int]:
        """
        Bulk delete multiple instances and manage cache invalidation.

        Args:
            instances: List of entity instances to delete (for validation)
            **filters: Filters to identify instances to delete

        Returns:
            Tuple containing:
            - List of successfully deleted instances
            - Count of deleted instances

        Raises:
            ValueError: If bulk deletion fails
        """
        if not instances:
            logger.debug("Empty instances list provided for bulk delete")
            return [], 0

        # Attempt bulk deletion
        try:
            deleted_instances = self.manager.bulk_delete_instances(**filters)
            deleted_count = len(deleted_instances)
            logger.info(
                f"Successfully deleted {deleted_count} {self.model.__name__} instances."
                f"(Filters: {filters})"
            )

            # Handle cache invalidation if enabled
            if self._cache_enabled and deleted_instances:
                failed_cache_deletes = []
                for instance in deleted_instances:

                    try:
                        self._cache_manager.delete(self._get_cache_key(instance.id))

                    except Exception as cache_error:
                        failed_cache_deletes.append(instance.id)
                        logger.warning(
                            f"Failed to clear cache for deleted {self.model.__name__} "
                            f"{instance.id}: {str(cache_error)}"
                        )

                if failed_cache_deletes:
                    logger.warning(
                        f"Failed to clear cache for {len(failed_cache_deletes)} "
                        f"deleted {self.model.__name__} instances (IDs: {failed_cache_deletes})"
                    )

            return deleted_instances, len(deleted_instances)

        except Exception as e:
            logger.exception(
                f"Unexpected error during bulk delete of {self.model.__name__} instances, {e}"
            )
            raise

from __future__ import annotations

# External
from django.db import transaction, IntegrityError, DatabaseError
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.query import QuerySet
from django.db import models

# Internal
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, TypeVar, Generic
import logging

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from typing import Optional, List


T = TypeVar("T", bound=models.Model)


class AbstractManager(ABC):
    """Abstract manager for common query operations."""

    @abstractmethod
    def get_by_id(self, obj_id: int | str) -> Optional[T]:
        pass


    @abstractmethod
    def create_instance(self, **kwargs) -> Optional[T]:
        pass


class DBManager(models.Manager, AbstractManager, Generic[T]):
    """Manager for common query operations."""


    def get_by_id(self, obj_id: int | str) -> Optional[T]:
        """Fetch an instance by ID if it's valid."""

        if not isinstance(obj_id, (int, str)) or not str(obj_id).isdigit():
            return None

        try:
            return self.filter(id=obj_id).first()

        except ObjectDoesNotExist:
            return None
        except Exception as e:
            logger.exception(f"Unexpected error during fetching by id {obj_id}",None, e)
            raise ValueError(str(e)) from e


    def get_all(self) -> QuerySet[T]:
        """Return all objects of the model."""
        return self.all()


    def filter_by(self, **filters) -> QuerySet[T]:
        """Return objects that match the given filters."""
        return self.filter(**filters)


    def exists(self, **filters) -> bool:
        """Check if an object with given filters exists."""
        return self.filter(**filters).exists()


    def create_instance(self, **kwargs) -> Optional[T]:
        """Create and return an instance."""

        if not kwargs:
            return None
        if not getattr(self, "model", None):
            raise ValueError("BaseManager must be attached to a model before creating instances")
        instance = None

        try:
            instance = self.model(**kwargs)
            instance.save()
            return instance

        except IntegrityError as e:
            logger.error("IntegrityError", instance, e)
        except DatabaseError as e:
            logger.error("DatabaseError", instance, e)
        except Exception as e:
            logger.exception("Unexpected error", instance, e)

        return None


    def bulk_create_instances(self,
                              objects: List[models.Model],
                              batch_size: int = 100
    ) -> List[T]:
        """Bulk create instances and return the created objects."""

        if not objects:
            return []

        try:
            created_instances = self.bulk_create(objects, batch_size=batch_size)
            return created_instances

        except IntegrityError as e:
            logger.error(f"IntegrityError during bulk_create", None, e)

        except Exception as e:
            logger.exception(f"Unexpected error during bulk_create", None, e)
            raise
        return []


    def bulk_update_instances(self,
                              objects: List[T],
                              fields: List[str],
                              *,
                              batch_size: int = 100
    ) -> List[T]:
        """Atomically bulk update instances in batches."""

        if not objects or not fields:
            return []

        try:
            for i in range(0, len(objects), batch_size):
                batch = objects[i:i + batch_size]
                self.bulk_update(batch, fields=fields)
            return objects

        except IntegrityError as e:
            logger.error("IntegrityError during bulk_create", None, e)

        except Exception as e:
            logger.exception(f"Unexpected error during bulk_create", None, e)
            raise
        return []


    def bulk_delete_instances(self, **filters) -> List[T]:
        """Bulk delete instances matching filters atomically."""

        if not filters:
            return []

        try:
            instances = list(self.filter_by(**filters))
            if instances:
                self.filter_by(pk__in=[obj.pk for obj in instances]).delete()
            return instances

        except IntegrityError as e:
            logger.error(f"IntegrityError during bulk_delete", None, e)

        except Exception as e:
            logger.exception(f"Unexpected error during bulk_delete", None, e)
            raise
        return  []


class BaseModel(models.Model):
    """Abstract base model with common CRUD methods."""

    id = models.AutoField(primary_key=True)
    objects = DBManager()


    class Meta:
        abstract = True


    @classmethod
    def commit(cls) -> None:
        """Commit all pending changes in the database session."""

        try:
            transaction.commit()

        except Exception as e:
            transaction.rollback()
            logger.exception(f"Transaction commit failed: {e}")
            raise e


    def before_update(self) -> None:
        """Hook to run custom logic before updating."""

        try:
            logger.info(f"Running before_update hook for {self.__class__.__name__}.")
            self._before_update_hook()
        except Exception as e:
            logger.exception(f"Unexpected error in before_update for {self.__class__.__name__}: {e}")
            raise e


    def _before_update_hook(self) -> None:
        pass


    def after_update(self) -> None:
        """Hook to run custom logic after updating."""

        try:
            logger.info(f"Running after_update hook for {self.__class__.__name__}.")
            self._after_update_hook()
        except Exception as e:
            logger.exception(f"Unexpected error in after_update for {self.__class__.__name__}: {e}")
            raise e


    def _after_update_hook(self) -> None: # for test
        pass


    def update(self, **kwargs) -> None:
        """Update model fields and save the instance safely."""

        if kwargs is None or not kwargs:
            return None

        try:
            self.before_update()

            for attr, value in kwargs.items():
                setattr(self, attr, value)
            self.save()
            logger.info(f"Updated {self.__class__.__name__} (ID: {self.pk}) successfully")

            self.after_update()

        except Exception as e:
            logger.exception(f"Error updating {self.__class__.__name__}: {e}")
            raise


    def before_save(self) -> None:
        """Hook to run custom logic before saving."""

        try:
            logger.info(f"Running before_save hook for {self.__class__.__name__}.")
            self._before_save_hook()
        except Exception as e:
            logger.exception(f"Unexpected error in before_save for {self.__class__.__name__}: {e}")
            raise e


    def _before_save_hook(self) -> None:
        pass


    def after_save(self) -> None:
        """Hook to run custom logic after saving."""

        try:
            logger.info(f"Running after_save hook for {self.__class__.__name__}.")
            self._after_save_hook()
        except Exception as e:
            logger.exception(f"Unexpected error in after_save for {self.__class__.__name__}: {e}")
            raise e


    def _after_save_hook(self) -> None:
        pass


    def save(self, commit: bool = False, *args, **kwargs) -> None:
        """Save instance with transaction handling."""

        if args:
            raise ValueError("Unexpected positional arguments passed to save()")
        if not isinstance(commit, bool):
            raise ValueError("Commit must be a boolean")
        if kwargs:
            raise ValueError(f"Unexpected keyword arguments: {', '.join(kwargs.keys())}")

        try:
            self.before_save()
            super().save(*args, **kwargs)
            logger.info(f"Successfully saved {self.__class__.__name__} (ID: {self.pk})")
            self.after_save()

        except IntegrityError as e:
            logger.error(f"IntegrityError in {self.__class__.__name__}.save(): {e}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error in {self.__class__.__name__}.save(): {e}")
            raise


    def delete(self, *args, **kwargs) -> None:
        """Delete instance with exception handling."""

        try:
            super().delete(*args, **kwargs)
            logger.info(f"Deleted {self.__class__.__name__} (ID: {self.pk}) successfully")

        except Exception as e:
            logger.exception(f"Error deleting {self.__class__.__name__} (ID: {self.pk}): {e}")
            raise

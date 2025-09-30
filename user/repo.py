# External
from __future__ import annotations

# Internal
from cmn.base_repo import BaseRepository
from .models import User
from typing import TYPE_CHECKING, Tuple

if TYPE_CHECKING:
    from typing import Optional, List, Type


class UserRepository(BaseRepository[User]):
    """Repository for handling User model operations."""


    def __init__(self, model: Type[User] = User, cache_enabled: bool = True):
        super().__init__(model=model, cache_enabled=cache_enabled)


    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Fetch a user by ID with caching."""
        return self.get_entity_by_id(user_id)


    def get_all_users(self) -> List[User]:
        """Retrieve all users."""
        return self.get_all_entities()


    def create_user(self, **kwargs) -> Optional[User]:
        """Create a new user within an atomic transaction and clear cache."""
        return self.create_entity(**kwargs)


    def update_user_by_id(self, user_id: int, **kwargs) -> Optional[User]:
        """Update a user by ID atomically and refresh cache."""
        return self.update_entity(user_id, **kwargs)


    def delete_user_by_id(self, user_id: int) -> Optional[User]:
        """Delete a user by ID atomically and clear cache."""
        return self.delete_entity(user_id)


    def bulk_create_users(self, users: List[User]) -> List[User]:
        """Bulk create user instances atomically."""
        return self.bulk_create_entities(users)


    def bulk_update_users(self, users: List[User], fields: List[str]) -> List[User]:
        """Bulk update user instances atomically."""
        return self.bulk_update_entities(users, fields)


    def bulk_delete_users(self, **filters) -> Tuple[List[User], int]:
        """Bulk delete users atomically based on filters."""
        return self.bulk_delete_entities(**filters)


    def get_verified_users(self) -> List[User]:
        """Retrieve all verified users."""
        return list(self.manager.filter_by(is_verified=True))


    def get_unverified_users(self) -> List[User]:
        """Retrieve all unverified users."""
        return list(self.manager.filter_by(is_verified=False))

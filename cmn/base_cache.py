from __future__ import annotations

# External
from django.core.cache import caches

# Internal
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from django.core.cache.backends.base import BaseCache


class AbstractCacheManager(ABC):
    """Abstract base class for cache managers."""


    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Retrieve an item from cache."""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> None:
        """Set an item in cache."""
        pass

    @abstractmethod
    def get_or_set(self, key: str, default: Callable[[], Any], timeout: Optional[int] = None) -> Any:
        """Retrieve an item from cache or set it if not present."""
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete an item from cache."""
        pass

    @abstractmethod
    def incr(self, key: str, delta: int = 1) -> int:
        """Increment a cache value atomically."""
        pass


class CacheManager(AbstractCacheManager):
    """Django-based cache manager with Redis compatibility."""

    CACHE_BACKEND: str = "default"  # Change to 'redis' when switching
    CACHE_TIMEOUT: int = 60 * 15


    def __init__(self, cache_backend: Optional[str] = None) -> None:
        """Allow setting a different cache backend at runtime."""
        self.cache_backend = cache_backend or self.CACHE_BACKEND


    def _get_cache(self) -> BaseCache:
        """Get the appropriate cache backend."""
        return caches[self.cache_backend]


    def get(self, key: str) -> Optional[Any]:
        """Retrieve an item from cache."""
        return self._get_cache().get(key)


    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> None:
        """Set an item in cache."""
        self._get_cache().set(key, value, timeout or self.CACHE_TIMEOUT)


    def get_or_set(self, key: str, default: Callable[[], Any], timeout: Optional[int] = None) -> Any:
        """Retrieve an item from cache or set it if not present."""
        return self._get_cache().get_or_set(key, default, timeout or self.CACHE_TIMEOUT)


    def delete(self, key: str) -> None:
        """Delete an item from cache."""
        self._get_cache().delete(key)


    def incr(self, key: str, delta: int = 1) -> int:
        """Increment a cache value atomically, defaulting to 1 if key does not exist."""

        cache = self._get_cache()
        try:
            return cache.incr(key, delta=delta)
        except ValueError:
            self.set(key, 1)
            return 1


    def clear(self) -> None:
        """Clear all cache entries for this backend."""
        self._get_cache().clear()



# class RedisCacheManager(AbstractCacheManager):
#     """Cache manager using Redis directly for high-performance needs."""
#
#     # features can be added:
#     # auto-refreshing cache and cache invalidation hooks
#
#     CACHE_TIMEOUT: int = 60 * 15
#
#     def __init__(self):
#         self.redis = get_redis_connection("default")  # Direct Redis connection
#
#
#     def get(self, key: str) -> Optional[Any]:
#         """Retrieve an item from Redis (JSON deserialized)."""
#
#         data = self.redis.get(key)
#         return json.loads(data) if data else None
#
#
#     def set(self, key: str, value: Any, timeout: Optional[int] = None) -> None:
#         """Store an item in Redis with optional expiration (JSON serialized)."""
#
#         timeout = timeout or self.CACHE_TIMEOUT
#         self.redis.setex(key, timeout, json.dumps(value))
#
#
#     def get_or_set(self, key: str, default: Callable[[], Any], timeout: Optional[int] = None) -> Any:
#         """Retrieve an item from cache or set it if not present."""
#
#         timeout = timeout or self.CACHE_TIMEOUT
#         data = self.redis.get(key)
#
#         if data:
#             return json.loads(data)
#
#         value = default()
#         self.redis.setex(key, timeout, json.dumps(value))
#         return value
#
#
#     def delete(self, key: str) -> None:
#         """Delete an item from cache."""
#         self.redis.delete(key)
#
#
#     def incr(self, key: str, delta: int = 1) -> int:
#         """Atomically increment a cache value (default to 1 if missing)."""
#         return self.redis.incrby(key, delta)
#
#
#     def bulk_get(self, keys: List[str]) -> Dict[str, Any]:
#         """Retrieve multiple values from Redis in one call."""
#
#         results = self.redis.mget(keys)
#         return {key: json.loads(value) if value else None for key, value in zip(keys, results)}
#
#
#     def bulk_set(self, data: Dict[str, Any], timeout: Optional[int] = None) -> None:
#         """Store multiple values in Redis in a single batch."""
#
#         timeout = timeout or self.CACHE_TIMEOUT
#         pipeline = self.redis.pipeline()
#
#         for key, value in data.items():
#             pipeline.setex(key, timeout, json.dumps(value))
#
#         pipeline.execute()  # Execute all at once
#
#     def bulk_delete(self, keys: List[str]) -> None:
#         """Delete multiple keys at once."""
#         self.redis.delete(*keys)

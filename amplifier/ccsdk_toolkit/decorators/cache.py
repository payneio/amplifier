"""
Cache Decorator

Adds response caching to functions working with Claude Code SDK.
Supports TTL, cache size limits, and invalidation strategies.
"""

import asyncio
import functools
import hashlib
import json
import logging
import time
from collections import OrderedDict
from collections.abc import Callable
from typing import Any
from typing import TypeVar

logger = logging.getLogger(__name__)

# Type variables for generic decorator
F = TypeVar("F", bound=Callable[..., Any])

# Global cache storage
_cache_storage: dict[str, OrderedDict] = {}
_cache_metadata: dict[str, dict] = {}


def with_cache(
    ttl: float | None = 300.0,
    max_size: int = 100,
    cache_key_func: Callable | None = None,
    skip_args: list[int] | None = None,
    cache_name: str | None = None,
) -> Callable[[F], F]:
    """
    Add caching to function results.

    Args:
        ttl: Time to live in seconds (None = no expiration)
        max_size: Maximum cache size (LRU eviction)
        cache_key_func: Custom function to generate cache key
        skip_args: List of argument indices to skip in cache key
        cache_name: Optional cache namespace

    Returns:
        Decorated function with caching

    Example:
        @with_cache(ttl=300, max_size=50)
        async def analyze_code(client, code: str):
            return await client.query(f"Analyze: {code}")
    """
    skip_args = skip_args or [0]  # Skip first arg (usually client) by default

    def decorator(func: F) -> F:
        # Get cache namespace
        namespace = cache_name or func.__name__
        if namespace not in _cache_storage:
            _cache_storage[namespace] = OrderedDict()
            _cache_metadata[namespace] = {"hits": 0, "misses": 0, "evictions": 0}

        cache = _cache_storage[namespace]
        metadata = _cache_metadata[namespace]

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            if cache_key_func:
                cache_key = cache_key_func(*args, **kwargs)
            else:
                cache_key = _generate_cache_key(args, kwargs, skip_args)

            # Check cache
            if cache_key in cache:
                entry = cache[cache_key]
                # Check TTL
                if ttl is None or (time.time() - entry["timestamp"]) < ttl:
                    # Move to end (LRU)
                    cache.move_to_end(cache_key)
                    metadata["hits"] += 1
                    logger.debug(f"Cache hit for {func.__name__} (key: {cache_key[:16]}...)")
                    return entry["result"]
                # Expired
                del cache[cache_key]

            # Cache miss
            metadata["misses"] += 1
            logger.debug(f"Cache miss for {func.__name__} (key: {cache_key[:16]}...)")

            # Execute function
            result = await func(*args, **kwargs)

            # Store in cache
            cache[cache_key] = {"result": result, "timestamp": time.time()}
            cache.move_to_end(cache_key)

            # Evict if needed
            while len(cache) > max_size:
                evicted_key = next(iter(cache))
                del cache[evicted_key]
                metadata["evictions"] += 1

            return result

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Generate cache key
            if cache_key_func:
                cache_key = cache_key_func(*args, **kwargs)
            else:
                cache_key = _generate_cache_key(args, kwargs, skip_args)

            # Check cache
            if cache_key in cache:
                entry = cache[cache_key]
                # Check TTL
                if ttl is None or (time.time() - entry["timestamp"]) < ttl:
                    # Move to end (LRU)
                    cache.move_to_end(cache_key)
                    metadata["hits"] += 1
                    logger.debug(f"Cache hit for {func.__name__} (key: {cache_key[:16]}...)")
                    return entry["result"]
                # Expired
                del cache[cache_key]

            # Cache miss
            metadata["misses"] += 1
            logger.debug(f"Cache miss for {func.__name__} (key: {cache_key[:16]}...)")

            # Execute function
            result = func(*args, **kwargs)

            # Store in cache
            cache[cache_key] = {"result": result, "timestamp": time.time()}
            cache.move_to_end(cache_key)

            # Evict if needed
            while len(cache) > max_size:
                evicted_key = next(iter(cache))
                del cache[evicted_key]
                metadata["evictions"] += 1

            return result

        # Add cache control methods
        wrapper = async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        wrapper.cache_clear = lambda: cache.clear()  # type: ignore
        wrapper.cache_info = lambda: {  # type: ignore
            "size": len(cache),
            "max_size": max_size,
            "ttl": ttl,
            **metadata,
        }

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


def _generate_cache_key(args: tuple, kwargs: dict, skip_args: list[int]) -> str:
    """Generate a cache key from function arguments."""
    # Filter out skipped arguments
    cache_args = [arg for i, arg in enumerate(args) if i not in skip_args]

    # Create key data
    key_data = {
        "args": _serialize_for_cache(cache_args),
        "kwargs": _serialize_for_cache(kwargs) if kwargs else None,
    }

    # Generate hash
    key_str = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.sha256(key_str.encode()).hexdigest()


def _serialize_for_cache(obj: Any) -> Any:
    """Serialize object for cache key generation."""
    if obj is None or isinstance(obj, bool | int | float | str):
        return obj
    if isinstance(obj, list | tuple):
        return [_serialize_for_cache(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _serialize_for_cache(v) for k, v in obj.items()}
    # For complex objects, use string representation
    return str(obj)


def clear_cache(cache_name: str | None = None) -> None:
    """
    Clear cache for specific function or all caches.

    Args:
        cache_name: Optional cache namespace to clear
    """
    if cache_name:
        if cache_name in _cache_storage:
            _cache_storage[cache_name].clear()
            _cache_metadata[cache_name] = {"hits": 0, "misses": 0, "evictions": 0}
    else:
        for name in _cache_storage:
            _cache_storage[name].clear()
            _cache_metadata[name] = {"hits": 0, "misses": 0, "evictions": 0}


def get_cache_info(cache_name: str | None = None) -> dict:
    """
    Get cache statistics.

    Args:
        cache_name: Optional cache namespace

    Returns:
        Dictionary with cache statistics
    """
    if cache_name:
        if cache_name not in _cache_storage:
            return {}
        cache = _cache_storage[cache_name]
        metadata = _cache_metadata[cache_name]
        return {
            cache_name: {
                "size": len(cache),
                **metadata,
            }
        }
    result = {}
    for name in _cache_storage:
        cache = _cache_storage[name]
        metadata = _cache_metadata[name]
        result[name] = {
            "size": len(cache),
            **metadata,
        }
    return result

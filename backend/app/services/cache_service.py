"""Simple in-memory response cache for API endpoints.

Caches expensive query results with TTL-based expiration. Designed for
single-process deployment; for multi-process use a shared cache like Redis.
"""

import logging
import time
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)

_cache: dict[str, tuple[Any, float]] = {}

# Default TTL: 5 minutes for rankings, 1 hour for player details
DEFAULT_TTL = 300  # seconds


def cached(ttl: int = DEFAULT_TTL):
    """Decorator for caching async function results by arguments.

    Args:
        ttl: Time-to-live in seconds.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key from function name and hashable args
            key_parts = [func.__name__]
            for a in args:
                if not hasattr(a, "__dict__"):  # Skip db sessions
                    key_parts.append(str(a))
            for k, v in sorted(kwargs.items()):
                key_parts.append(f"{k}={v}")
            cache_key = ":".join(key_parts)

            # Check cache
            if cache_key in _cache:
                value, expiry = _cache[cache_key]
                if time.time() < expiry:
                    return value
                else:
                    del _cache[cache_key]

            # Cache miss — execute function
            result = await func(*args, **kwargs)
            _cache[cache_key] = (result, time.time() + ttl)
            return result

        return wrapper
    return decorator


def invalidate_all() -> int:
    """Clear all cached entries. Returns number of entries cleared."""
    count = len(_cache)
    _cache.clear()
    logger.info(f"Cache invalidated: {count} entries cleared")
    return count


def invalidate_prefix(prefix: str) -> int:
    """Clear cached entries matching a key prefix."""
    keys_to_delete = [k for k in _cache if k.startswith(prefix)]
    for k in keys_to_delete:
        del _cache[k]
    return len(keys_to_delete)


def cache_stats() -> dict:
    """Get cache statistics."""
    now = time.time()
    active = sum(1 for _, (_, exp) in _cache.items() if exp > now)
    expired = len(_cache) - active
    return {
        "total_entries": len(_cache),
        "active_entries": active,
        "expired_entries": expired,
    }

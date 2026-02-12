"""Tests for the API cache service."""

import asyncio
import pytest

from backend.app.services.cache_service import (
    cached,
    invalidate_all,
    invalidate_prefix,
    cache_stats,
    _cache,
)


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before each test."""
    _cache.clear()
    yield
    _cache.clear()


class TestCacheDecorator:
    @pytest.mark.asyncio
    async def test_cache_hit(self):
        """Second call should return cached result without re-executing."""
        call_count = 0

        @cached(ttl=60)
        async def expensive_func(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = await expensive_func(5)
        result2 = await expensive_func(5)

        assert result1 == 10
        assert result2 == 10
        assert call_count == 1  # Only called once

    @pytest.mark.asyncio
    async def test_different_args_different_cache(self):
        """Different arguments should produce different cache entries."""
        @cached(ttl=60)
        async def func(x: int) -> int:
            return x * 2

        r1 = await func(5)
        r2 = await func(10)

        assert r1 == 10
        assert r2 == 20

    @pytest.mark.asyncio
    async def test_cache_expiry(self):
        """Expired entries should trigger re-execution."""
        call_count = 0

        @cached(ttl=0)  # Immediate expiry
        async def func() -> str:
            nonlocal call_count
            call_count += 1
            return "result"

        await func()
        await func()  # Should re-execute since TTL=0

        assert call_count == 2


class TestCacheManagement:
    @pytest.mark.asyncio
    async def test_invalidate_all(self):
        """invalidate_all should clear all entries."""
        @cached(ttl=60)
        async def func(x: int) -> int:
            return x

        await func(1)
        await func(2)
        assert cache_stats()["total_entries"] == 2

        count = invalidate_all()
        assert count == 2
        assert cache_stats()["total_entries"] == 0

    @pytest.mark.asyncio
    async def test_invalidate_prefix(self):
        """invalidate_prefix should clear matching entries only."""
        _cache["rankings:all"] = ("data", float("inf"))
        _cache["rankings:sleepers"] = ("data", float("inf"))
        _cache["players:detail"] = ("data", float("inf"))

        count = invalidate_prefix("rankings")
        assert count == 2
        assert len(_cache) == 1

    def test_cache_stats(self):
        """cache_stats should report correct counts."""
        import time
        _cache["active"] = ("data", time.time() + 3600)
        _cache["expired"] = ("data", time.time() - 100)

        stats = cache_stats()
        assert stats["total_entries"] == 2
        assert stats["active_entries"] == 1
        assert stats["expired_entries"] == 1

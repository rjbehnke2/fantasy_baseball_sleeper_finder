"""Tests for the scouting report cost monitor."""

import pytest

from backend.llm.generators.cost_monitor import CostMonitor


class TestCostMonitor:
    def test_allows_generation_under_limits(self):
        """Should allow generation when under all limits."""
        monitor = CostMonitor(max_per_hour=10, max_per_day=100, max_concurrent=5)
        allowed, reason = monitor.can_generate()
        assert allowed is True
        assert reason == ""

    def test_blocks_when_concurrent_limit_reached(self):
        """Should block when too many concurrent requests."""
        monitor = CostMonitor(max_concurrent=2)
        monitor.record_start()
        monitor.record_start()

        allowed, reason = monitor.can_generate()
        assert allowed is False
        assert "Concurrent" in reason

    def test_blocks_when_hourly_limit_reached(self):
        """Should block when hourly limit is exceeded."""
        monitor = CostMonitor(max_per_hour=3, max_per_day=100, max_concurrent=10)

        for _ in range(3):
            monitor.record_start()
            monitor.record_completion()

        allowed, reason = monitor.can_generate()
        assert allowed is False
        assert "Hourly" in reason

    def test_completion_decrements_active(self):
        """record_completion should decrement active request count."""
        monitor = CostMonitor(max_concurrent=2)
        monitor.record_start()
        monitor.record_start()
        assert monitor._active_requests == 2

        monitor.record_completion()
        assert monitor._active_requests == 1

    def test_failure_decrements_active(self):
        """record_failure should decrement active count without recording success."""
        monitor = CostMonitor()
        monitor.record_start()
        monitor.record_failure()
        assert monitor._active_requests == 0
        assert monitor._total_generated == 0

    def test_stats_reporting(self):
        """get_stats should return expected structure."""
        monitor = CostMonitor(max_per_hour=50, max_per_day=200)
        monitor.record_start()
        monitor.record_completion(estimated_tokens=3000)
        monitor.record_start()
        monitor.record_completion(estimated_tokens=2500)

        stats = monitor.get_stats()
        assert stats["total_generated"] == 2
        assert stats["total_tokens_estimated"] == 5500
        assert stats["hourly_count"] == 2
        assert stats["daily_count"] == 2
        assert stats["active_requests"] == 0
        assert "estimated_cost_usd" in stats

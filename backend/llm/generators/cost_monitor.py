"""Scouting report cost monitoring and throttling.

Tracks Claude API usage for scouting report generation and enforces
rate limits to control costs.
"""

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Default limits
DEFAULT_MAX_REPORTS_PER_HOUR = 100
DEFAULT_MAX_REPORTS_PER_DAY = 500
DEFAULT_MAX_CONCURRENT = 10


@dataclass
class CostMonitor:
    """Tracks and throttles scouting report generation."""

    max_per_hour: int = DEFAULT_MAX_REPORTS_PER_HOUR
    max_per_day: int = DEFAULT_MAX_REPORTS_PER_DAY
    max_concurrent: int = DEFAULT_MAX_CONCURRENT

    _hourly_timestamps: list[float] = field(default_factory=list)
    _daily_timestamps: list[float] = field(default_factory=list)
    _active_requests: int = 0
    _total_generated: int = 0
    _total_tokens_estimated: int = 0

    def can_generate(self) -> tuple[bool, str]:
        """Check if a new report can be generated within rate limits.

        Returns:
            Tuple of (allowed, reason_if_blocked).
        """
        now = time.time()

        # Check concurrent limit
        if self._active_requests >= self.max_concurrent:
            return False, f"Concurrent limit reached ({self.max_concurrent})"

        # Clean old timestamps
        one_hour_ago = now - 3600
        one_day_ago = now - 86400
        self._hourly_timestamps = [t for t in self._hourly_timestamps if t > one_hour_ago]
        self._daily_timestamps = [t for t in self._daily_timestamps if t > one_day_ago]

        # Check hourly limit
        if len(self._hourly_timestamps) >= self.max_per_hour:
            return False, f"Hourly limit reached ({self.max_per_hour}/hr)"

        # Check daily limit
        if len(self._daily_timestamps) >= self.max_per_day:
            return False, f"Daily limit reached ({self.max_per_day}/day)"

        return True, ""

    def record_start(self) -> None:
        """Record the start of a report generation."""
        self._active_requests += 1

    def record_completion(self, estimated_tokens: int = 2000) -> None:
        """Record the completion of a report generation.

        Args:
            estimated_tokens: Estimated total tokens used (input + output).
        """
        now = time.time()
        self._active_requests = max(0, self._active_requests - 1)
        self._hourly_timestamps.append(now)
        self._daily_timestamps.append(now)
        self._total_generated += 1
        self._total_tokens_estimated += estimated_tokens

    def record_failure(self) -> None:
        """Record a failed generation (decrement active count)."""
        self._active_requests = max(0, self._active_requests - 1)

    def get_stats(self) -> dict:
        """Get current usage statistics."""
        now = time.time()
        one_hour_ago = now - 3600
        one_day_ago = now - 86400

        hourly_count = len([t for t in self._hourly_timestamps if t > one_hour_ago])
        daily_count = len([t for t in self._daily_timestamps if t > one_day_ago])

        # Rough cost estimate: ~$0.003 per 1K input tokens, ~$0.015 per 1K output tokens
        # Average report: ~1500 input + ~800 output tokens
        estimated_cost = self._total_tokens_estimated * 0.008 / 1000  # Blended rate

        return {
            "active_requests": self._active_requests,
            "hourly_count": hourly_count,
            "hourly_limit": self.max_per_hour,
            "daily_count": daily_count,
            "daily_limit": self.max_per_day,
            "total_generated": self._total_generated,
            "total_tokens_estimated": self._total_tokens_estimated,
            "estimated_cost_usd": round(estimated_cost, 2),
        }


# Singleton instance
monitor = CostMonitor()

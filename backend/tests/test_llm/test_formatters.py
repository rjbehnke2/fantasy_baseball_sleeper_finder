"""Tests for the LLM context formatters."""

import pytest

from backend.llm.prompts.formatters import format_player_context


class TestPlayerContextFormatting:
    def _make_player(self, **overrides):
        base = {
            "full_name": "Test Player",
            "age": 27,
            "team": "NYY",
            "position": "SS",
            "prospect_rank": None,
            "mlb_service_time": "4.123",
        }
        base.update(overrides)
        return base

    def _make_stats(self, **overrides):
        base = {
            "season": 2023, "pa": 600,
            "avg": 0.280, "obp": 0.350, "slg": 0.450,
            "woba": 0.350, "xwoba": 0.340, "wrc_plus": 125,
            "iso": 0.170, "babip": 0.310,
            "k_pct": 0.20, "bb_pct": 0.10,
            "barrel_pct": 0.12, "hard_hit_pct": 0.42,
            "avg_exit_velocity": 90.5, "sprint_speed": 27.5,
            "war": 4.5,
        }
        base.update(overrides)
        return base

    def _make_scores(self, **overrides):
        base = {
            "ai_value_score": 78.5,
            "sleeper_score": 65.0,
            "bust_score": 20.0,
            "consistency_score": 80.0,
            "improvement_score": 35.0,
            "regression_direction": 0.015,
            "auction_value": 28.0,
            "dynasty_value": 72.0,
            "surplus_value": 5.0,
            "expected_cost": 23.0,
        }
        base.update(overrides)
        return base

    def test_basic_context_generation(self):
        """Should generate a non-empty context string with key sections."""
        context = format_player_context(
            self._make_player(),
            [self._make_stats()],
            self._make_scores(),
        )

        assert "Test Player" in context
        assert "NYY" in context
        assert "AI Model Scores" in context
        assert "Auction Valuation" in context

    def test_multi_season_trends(self):
        """Should include trend information when multiple seasons provided."""
        stats = [
            self._make_stats(season=2023, k_pct=0.18),
            self._make_stats(season=2022, k_pct=0.22),
            self._make_stats(season=2021, k_pct=0.26),
        ]
        context = format_player_context(
            self._make_player(),
            stats,
            self._make_scores(),
        )

        assert "Year-over-Year Trends" in context

    def test_differentials_section(self):
        """Should include actual vs expected differentials."""
        context = format_player_context(
            self._make_player(),
            [self._make_stats()],
            self._make_scores(),
        )

        assert "Performance vs. Expected" in context or "Luck Gap" in context

    def test_dynasty_context(self):
        """Should include dynasty-specific context."""
        context = format_player_context(
            self._make_player(age=24),
            [self._make_stats()],
            self._make_scores(),
        )

        assert "Dynasty Context" in context

    def test_improvement_breakdown(self):
        """Should include improvement breakdown when available."""
        scores = self._make_scores(stat_improvement_breakdown={
            "k_pct": {"direction": "improving", "r_squared": 0.95, "values": [0.26, 0.22, 0.18]},
        })
        context = format_player_context(
            self._make_player(),
            [self._make_stats()],
            scores,
        )

        assert "Skills Trajectory" in context
        assert "k_pct" in context

    def test_consistency_breakdown(self):
        """Should include consistency breakdown when available."""
        scores = self._make_scores(stat_consistency_breakdown={
            "k_pct": {"consistency": 0.95, "cv": 0.05},
        })
        context = format_player_context(
            self._make_player(),
            [self._make_stats()],
            scores,
        )

        assert "Consistency Breakdown" in context

    def test_auction_context(self):
        """Should include auction dollar values."""
        context = format_player_context(
            self._make_player(),
            [self._make_stats()],
            self._make_scores(auction_value=28.0, surplus_value=5.0),
        )

        assert "$28.0" in context
        assert "surplus" in context.lower()

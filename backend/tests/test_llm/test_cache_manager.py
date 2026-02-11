"""Tests for the scouting report cache manager."""

import pytest

from backend.llm.generators.cache_manager import is_report_stale, select_batch_players


class TestStalenessDetection:
    def test_no_cached_snapshot_is_stale(self):
        """Missing cached snapshot should always be stale."""
        assert is_report_stale(None, {"sleeper_score": 50}) is True

    def test_same_scores_not_stale(self):
        """Identical scores should not be stale."""
        snapshot = {"sleeper_score": 60, "bust_score": 30, "ai_value_score": 75}
        current = {"sleeper_score": 60, "bust_score": 30, "ai_value_score": 75}
        assert is_report_stale(snapshot, current) is False

    def test_small_change_not_stale(self):
        """Small score changes should not trigger staleness."""
        snapshot = {"sleeper_score": 60, "bust_score": 30, "ai_value_score": 75}
        current = {"sleeper_score": 62, "bust_score": 28, "ai_value_score": 76}
        assert is_report_stale(snapshot, current) is False

    def test_large_score_change_is_stale(self):
        """Score change > 10 points should trigger staleness."""
        snapshot = {"sleeper_score": 60, "bust_score": 30, "ai_value_score": 75}
        current = {"sleeper_score": 75, "bust_score": 30, "ai_value_score": 75}
        assert is_report_stale(snapshot, current) is True

    def test_dollar_value_change_is_stale(self):
        """Auction value change > $5 should trigger staleness."""
        snapshot = {"auction_value": 25.0}
        current = {"auction_value": 35.0}
        assert is_report_stale(snapshot, current) is True

    def test_regression_direction_flip_is_stale(self):
        """Regression direction flipping sign should trigger staleness."""
        snapshot = {"regression_direction": 0.05}
        current = {"regression_direction": -0.05}
        assert is_report_stale(snapshot, current) is True


class TestBatchPlayerSelection:
    def test_selects_top_value_players(self):
        """Should select top players by AI value score."""
        scores = {
            i: {"ai_value_score": 100 - i, "sleeper_score": 0, "bust_score": 0, "age": 28}
            for i in range(300)
        }
        result = select_batch_players(scores, top_n_value=10, top_n_sleepers=5, top_n_busts=5)

        # Top 10 by value should get "full" reports
        for pid in range(10):
            assert "full" in result.get(pid, [])

    def test_selects_top_sleepers(self):
        """Should select top sleepers for spotlight reports."""
        scores = {
            i: {"ai_value_score": 50, "sleeper_score": 100 - i, "bust_score": 0, "age": 28}
            for i in range(100)
        }
        result = select_batch_players(scores, top_n_value=5, top_n_sleepers=10, top_n_busts=5)

        for pid in range(10):
            assert "sleeper_spotlight" in result.get(pid, [])

    def test_player_can_get_multiple_report_types(self):
        """A top player who is also a top sleeper should get both report types."""
        scores = {
            1: {"ai_value_score": 99, "sleeper_score": 99, "bust_score": 0, "age": 28},
        }
        result = select_batch_players(scores, top_n_value=5, top_n_sleepers=5, top_n_busts=5)

        assert "full" in result[1]
        assert "sleeper_spotlight" in result[1]

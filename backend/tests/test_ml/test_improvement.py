"""Tests for the improvement scoring module."""

import pandas as pd
import pytest

from backend.ml.models.improvement_model import (
    calculate_batter_improvement,
    calculate_pitcher_improvement,
)


def _make_batting_df(player_data: dict) -> pd.DataFrame:
    rows = []
    for pid, seasons in player_data.items():
        for season in seasons:
            row = {"player_id": pid, **season}
            rows.append(row)
    return pd.DataFrame(rows)


class TestBatterImprovement:
    def test_improving_young_player_scores_high(self):
        """A young player showing steady improvement in skills stats should score high."""
        data = {
            1: [
                {"season": 2023, "pa": 600, "k_pct": 0.18, "bb_pct": 0.12,
                 "barrel_pct": 0.14, "hard_hit_pct": 0.45, "avg_exit_velocity": 92.0,
                 "sprint_speed": 28.0},
                {"season": 2022, "pa": 550, "k_pct": 0.22, "bb_pct": 0.10,
                 "barrel_pct": 0.10, "hard_hit_pct": 0.40, "avg_exit_velocity": 90.0,
                 "sprint_speed": 27.8},
                {"season": 2021, "pa": 400, "k_pct": 0.26, "bb_pct": 0.08,
                 "barrel_pct": 0.07, "hard_hit_pct": 0.35, "avg_exit_velocity": 88.0,
                 "sprint_speed": 27.5},
            ],
        }
        ages = {1: 25}
        df = _make_batting_df(data)
        result = calculate_batter_improvement(df, ages)

        assert len(result) == 1
        score = result.iloc[0]["improvement_score"]
        assert score > 30, f"Improving young player should score >30, got {score}"

    def test_declining_old_player_scores_negative(self):
        """An old player with declining skills stats should score negative."""
        data = {
            2: [
                {"season": 2023, "pa": 500, "k_pct": 0.28, "bb_pct": 0.06,
                 "barrel_pct": 0.05, "hard_hit_pct": 0.30, "avg_exit_velocity": 86.0,
                 "sprint_speed": 25.0},
                {"season": 2022, "pa": 550, "k_pct": 0.24, "bb_pct": 0.08,
                 "barrel_pct": 0.08, "hard_hit_pct": 0.35, "avg_exit_velocity": 88.0,
                 "sprint_speed": 26.0},
                {"season": 2021, "pa": 600, "k_pct": 0.20, "bb_pct": 0.10,
                 "barrel_pct": 0.11, "hard_hit_pct": 0.40, "avg_exit_velocity": 90.0,
                 "sprint_speed": 27.0},
            ],
        }
        ages = {2: 35}
        df = _make_batting_df(data)
        result = calculate_batter_improvement(df, ages)

        assert len(result) == 1
        score = result.iloc[0]["improvement_score"]
        assert score < -10, f"Declining old player should score <-10, got {score}"

    def test_flat_player_scores_near_zero(self):
        """A player with stable stats should score near zero."""
        data = {
            3: [
                {"season": 2023, "pa": 600, "k_pct": 0.22, "bb_pct": 0.09,
                 "barrel_pct": 0.10, "hard_hit_pct": 0.38, "avg_exit_velocity": 89.5,
                 "sprint_speed": 27.0},
                {"season": 2022, "pa": 580, "k_pct": 0.22, "bb_pct": 0.09,
                 "barrel_pct": 0.10, "hard_hit_pct": 0.38, "avg_exit_velocity": 89.5,
                 "sprint_speed": 27.0},
                {"season": 2021, "pa": 590, "k_pct": 0.22, "bb_pct": 0.09,
                 "barrel_pct": 0.10, "hard_hit_pct": 0.38, "avg_exit_velocity": 89.5,
                 "sprint_speed": 27.0},
            ],
        }
        ages = {3: 28}
        df = _make_batting_df(data)
        result = calculate_batter_improvement(df, ages)

        assert len(result) == 1
        score = result.iloc[0]["improvement_score"]
        assert -10 <= score <= 10, f"Flat player should score near 0, got {score}"

    def test_age_multiplier_applied(self):
        """Young player improvement should be weighted higher than old player."""
        # Same improvement pattern, different ages
        base_seasons = [
            {"season": 2023, "pa": 600, "k_pct": 0.18, "bb_pct": 0.12,
             "barrel_pct": 0.14, "hard_hit_pct": 0.45, "avg_exit_velocity": 92.0,
             "sprint_speed": 28.0},
            {"season": 2022, "pa": 550, "k_pct": 0.22, "bb_pct": 0.10,
             "barrel_pct": 0.10, "hard_hit_pct": 0.40, "avg_exit_velocity": 90.0,
             "sprint_speed": 27.8},
            {"season": 2021, "pa": 500, "k_pct": 0.26, "bb_pct": 0.08,
             "barrel_pct": 0.07, "hard_hit_pct": 0.35, "avg_exit_velocity": 88.0,
             "sprint_speed": 27.5},
        ]

        young_data = {10: base_seasons}
        old_data = {20: base_seasons}

        young_df = _make_batting_df(young_data)
        old_df = _make_batting_df(old_data)

        young_result = calculate_batter_improvement(young_df, {10: 24})
        old_result = calculate_batter_improvement(old_df, {20: 34})

        young_score = young_result.iloc[0]["improvement_score"]
        old_score = old_result.iloc[0]["improvement_score"]

        assert young_score > old_score, (
            f"Young player ({young_score}) should score higher than old player ({old_score})"
        )

    def test_insufficient_data(self):
        """Players with only 1 season should get no score."""
        data = {
            5: [{"season": 2023, "pa": 600, "k_pct": 0.20, "bb_pct": 0.10}],
        }
        df = _make_batting_df(data)
        result = calculate_batter_improvement(df, {5: 28})
        assert len(result) == 0

    def test_stat_breakdown_included(self):
        """Result should include per-stat improvement breakdown."""
        data = {
            6: [
                {"season": 2023, "pa": 600, "k_pct": 0.18, "bb_pct": 0.12,
                 "barrel_pct": 0.14, "hard_hit_pct": 0.45, "avg_exit_velocity": 92.0,
                 "sprint_speed": 28.0},
                {"season": 2022, "pa": 550, "k_pct": 0.22, "bb_pct": 0.10,
                 "barrel_pct": 0.10, "hard_hit_pct": 0.40, "avg_exit_velocity": 90.0,
                 "sprint_speed": 27.8},
            ],
        }
        df = _make_batting_df(data)
        result = calculate_batter_improvement(df, {6: 25})

        assert "stat_improvement_breakdown" in result.columns
        breakdown = result.iloc[0]["stat_improvement_breakdown"]
        assert "k_pct" in breakdown
        assert "direction" in breakdown["k_pct"]
        assert "r_squared" in breakdown["k_pct"]


class TestPitcherImprovement:
    def test_improving_pitcher(self):
        """A pitcher showing steady K% improvement should score positive."""
        data = {
            10: [
                {"season": 2023, "ip": 180, "k_pct": 0.30, "bb_pct": 0.06,
                 "k_bb_pct": 0.24, "swstr_pct": 0.14, "csw_pct": 0.32, "gb_pct": 0.48},
                {"season": 2022, "ip": 170, "k_pct": 0.26, "bb_pct": 0.07,
                 "k_bb_pct": 0.19, "swstr_pct": 0.12, "csw_pct": 0.30, "gb_pct": 0.46},
                {"season": 2021, "ip": 160, "k_pct": 0.22, "bb_pct": 0.08,
                 "k_bb_pct": 0.14, "swstr_pct": 0.10, "csw_pct": 0.28, "gb_pct": 0.44},
            ],
        }
        ages = {10: 25}
        df = pd.DataFrame([row for seasons in data.values() for row in seasons])
        df["player_id"] = 10
        result = calculate_pitcher_improvement(df, ages)

        assert len(result) == 1
        score = result.iloc[0]["improvement_score"]
        assert score > 30, f"Improving pitcher should score >30, got {score}"

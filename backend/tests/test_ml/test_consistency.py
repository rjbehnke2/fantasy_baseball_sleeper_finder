"""Tests for the consistency scoring module."""

import pandas as pd
import pytest

from backend.ml.models.consistency_model import (
    calculate_batter_consistency,
    calculate_pitcher_consistency,
)


def _make_batting_df(player_data: dict) -> pd.DataFrame:
    """Helper to create batting DataFrame from simplified data."""
    rows = []
    for pid, seasons in player_data.items():
        for season in seasons:
            row = {"player_id": pid, **season}
            rows.append(row)
    return pd.DataFrame(rows)


class TestBatterConsistency:
    def test_highly_consistent_player(self):
        """A player with nearly identical stats across 3 seasons should score high."""
        data = {
            1: [
                {"season": 2023, "pa": 600, "k_pct": 0.20, "bb_pct": 0.10, "iso": 0.200,
                 "barrel_pct": 0.10, "avg_exit_velocity": 90.0, "hard_hit_pct": 0.40,
                 "gb_pct": 0.45, "fb_pct": 0.35, "woba": 0.350, "wrc_plus": 120,
                 "sprint_speed": 27.0},
                {"season": 2022, "pa": 580, "k_pct": 0.21, "bb_pct": 0.10, "iso": 0.195,
                 "barrel_pct": 0.10, "avg_exit_velocity": 89.8, "hard_hit_pct": 0.39,
                 "gb_pct": 0.44, "fb_pct": 0.36, "woba": 0.345, "wrc_plus": 118,
                 "sprint_speed": 27.1},
                {"season": 2021, "pa": 590, "k_pct": 0.20, "bb_pct": 0.09, "iso": 0.205,
                 "barrel_pct": 0.11, "avg_exit_velocity": 90.2, "hard_hit_pct": 0.41,
                 "gb_pct": 0.45, "fb_pct": 0.34, "woba": 0.355, "wrc_plus": 122,
                 "sprint_speed": 27.2},
            ],
        }
        df = _make_batting_df(data)
        result = calculate_batter_consistency(df)

        assert len(result) == 1
        score = result.iloc[0]["consistency_score"]
        assert score > 80, f"Highly consistent player should score >80, got {score}"

    def test_volatile_player_scores_lower(self):
        """A player with wildly different stats should score lower."""
        data = {
            2: [
                {"season": 2023, "pa": 500, "k_pct": 0.30, "bb_pct": 0.05, "iso": 0.100,
                 "barrel_pct": 0.04, "avg_exit_velocity": 85.0, "hard_hit_pct": 0.30,
                 "gb_pct": 0.50, "fb_pct": 0.30, "woba": 0.280, "wrc_plus": 80,
                 "sprint_speed": 26.0},
                {"season": 2022, "pa": 500, "k_pct": 0.15, "bb_pct": 0.12, "iso": 0.250,
                 "barrel_pct": 0.14, "avg_exit_velocity": 92.0, "hard_hit_pct": 0.48,
                 "gb_pct": 0.35, "fb_pct": 0.45, "woba": 0.380, "wrc_plus": 140,
                 "sprint_speed": 27.5},
                {"season": 2021, "pa": 400, "k_pct": 0.25, "bb_pct": 0.08, "iso": 0.170,
                 "barrel_pct": 0.09, "avg_exit_velocity": 88.0, "hard_hit_pct": 0.38,
                 "gb_pct": 0.42, "fb_pct": 0.38, "woba": 0.320, "wrc_plus": 105,
                 "sprint_speed": 26.8},
            ],
        }
        df = _make_batting_df(data)
        result = calculate_batter_consistency(df)

        assert len(result) == 1
        score = result.iloc[0]["consistency_score"]
        assert score < 75, f"Volatile player should score <75, got {score}"

    def test_minimum_seasons_required(self):
        """Players with only 1 season should get no score."""
        data = {
            3: [{"season": 2023, "pa": 600, "k_pct": 0.20, "bb_pct": 0.10, "iso": 0.200}],
        }
        df = _make_batting_df(data)
        result = calculate_batter_consistency(df)

        assert len(result) == 0, "Player with 1 season should not get a consistency score"

    def test_minimum_playing_time_filter(self):
        """Seasons with insufficient PA should be excluded."""
        data = {
            4: [
                {"season": 2023, "pa": 600, "k_pct": 0.20, "bb_pct": 0.10, "iso": 0.200},
                {"season": 2022, "pa": 50, "k_pct": 0.30, "bb_pct": 0.05, "iso": 0.100},
                {"season": 2021, "pa": 580, "k_pct": 0.21, "bb_pct": 0.09, "iso": 0.195},
            ],
        }
        df = _make_batting_df(data)
        result = calculate_batter_consistency(df)

        # Should still produce a score using 2023 and 2021 (skipping 2022 low-PA)
        assert len(result) == 1

    def test_stat_breakdown_included(self):
        """Result should include per-stat consistency breakdown."""
        data = {
            5: [
                {"season": 2023, "pa": 600, "k_pct": 0.20, "bb_pct": 0.10, "iso": 0.200},
                {"season": 2022, "pa": 580, "k_pct": 0.21, "bb_pct": 0.10, "iso": 0.195},
            ],
        }
        df = _make_batting_df(data)
        result = calculate_batter_consistency(df)

        assert "stat_consistency_breakdown" in result.columns
        breakdown = result.iloc[0]["stat_consistency_breakdown"]
        assert "k_pct" in breakdown
        assert "consistency" in breakdown["k_pct"]


class TestPitcherConsistency:
    def test_consistent_pitcher(self):
        """A consistent pitcher should score high."""
        data = {
            10: [
                {"season": 2023, "ip": 180, "k_pct": 0.28, "k_bb_pct": 0.20,
                 "swstr_pct": 0.12, "csw_pct": 0.30, "gb_pct": 0.45,
                 "fip": 3.20, "siera": 3.30, "xera": 3.40, "stuff_plus": 110},
                {"season": 2022, "ip": 175, "k_pct": 0.27, "k_bb_pct": 0.19,
                 "swstr_pct": 0.12, "csw_pct": 0.30, "gb_pct": 0.44,
                 "fip": 3.30, "siera": 3.40, "xera": 3.50, "stuff_plus": 108},
                {"season": 2021, "ip": 170, "k_pct": 0.27, "k_bb_pct": 0.19,
                 "swstr_pct": 0.11, "csw_pct": 0.29, "gb_pct": 0.46,
                 "fip": 3.25, "siera": 3.35, "xera": 3.45, "stuff_plus": 109},
            ],
        }
        df = pd.DataFrame([row for seasons in data.values() for row in seasons])
        df["player_id"] = 10
        result = calculate_pitcher_consistency(df)

        assert len(result) == 1
        score = result.iloc[0]["consistency_score"]
        assert score > 80

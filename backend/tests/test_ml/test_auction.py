"""Tests for auction valuation engine."""

import pandas as pd
import pytest

from backend.app.services.auction_service import (
    calculate_dynasty_value,
    calculate_sgp_values,
    calculate_surplus_value,
)


class TestSGPValues:
    def test_better_players_get_higher_values(self):
        """Players with better stats should get higher auction values."""
        batters = pd.DataFrame([
            {"player_id": 1, "hr": 40, "rbi": 110, "r": 100, "sb": 20, "avg": 0.290},
            {"player_id": 2, "hr": 15, "rbi": 60, "r": 65, "sb": 5, "avg": 0.250},
        ])
        pitchers = pd.DataFrame([
            {"player_id": 3, "w": 15, "sv": 0, "so": 220, "era": 2.80, "whip": 1.05},
            {"player_id": 4, "w": 8, "sv": 0, "so": 120, "era": 4.20, "whip": 1.30},
        ])

        batter_vals, pitcher_vals = calculate_sgp_values(batters, pitchers)

        star = batter_vals[batter_vals["player_id"] == 1].iloc[0]
        avg_player = batter_vals[batter_vals["player_id"] == 2].iloc[0]
        assert star["auction_value"] > avg_player["auction_value"]

    def test_minimum_value_is_one_dollar(self):
        """No player should be valued at less than $1."""
        batters = pd.DataFrame([
            {"player_id": 1, "hr": 0, "rbi": 10, "r": 15, "sb": 0, "avg": 0.190},
        ])
        pitchers = pd.DataFrame(columns=["player_id", "w", "sv", "so", "era", "whip"])

        batter_vals, _ = calculate_sgp_values(batters, pitchers)
        assert batter_vals["auction_value"].min() >= 1.0


class TestSurplusValue:
    def test_surplus_is_value_minus_cost(self):
        """Surplus value should be auction value minus expected cost."""
        df = pd.DataFrame([
            {"player_id": 1, "auction_value": 30.0},
            {"player_id": 2, "auction_value": 10.0},
        ])
        costs = {1: 25.0, 2: 15.0}
        result = calculate_surplus_value(df, expected_costs=costs)

        assert result[result["player_id"] == 1].iloc[0]["surplus_value"] == 5.0
        assert result[result["player_id"] == 2].iloc[0]["surplus_value"] == -5.0


class TestDynastyValue:
    def test_young_player_worth_more_in_dynasty(self):
        """A young player should have higher dynasty value than an older one with same stats."""
        df = pd.DataFrame([
            {"player_id": 1, "auction_value": 20.0, "expected_cost": 15.0},
            {"player_id": 2, "auction_value": 20.0, "expected_cost": 15.0},
        ])
        ages = {1: 24, 2: 33}

        result = calculate_dynasty_value(df, player_ages=ages)
        young = result[result["player_id"] == 1].iloc[0]
        old = result[result["player_id"] == 2].iloc[0]

        assert young["dynasty_value"] > old["dynasty_value"]
        assert young["keep_cut_horizon"] > old["keep_cut_horizon"]

    def test_dynasty_value_is_0_to_100(self):
        """Dynasty value should be normalized to 0-100 scale."""
        df = pd.DataFrame([
            {"player_id": 1, "auction_value": 40.0, "expected_cost": 30.0},
            {"player_id": 2, "auction_value": 5.0, "expected_cost": 3.0},
        ])
        ages = {1: 25, 2: 35}

        result = calculate_dynasty_value(df, player_ages=ages)
        assert result["dynasty_value"].max() <= 100.0
        assert result["dynasty_value"].min() >= 0.0

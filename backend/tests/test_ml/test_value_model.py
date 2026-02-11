"""Tests for the composite AI Value Score model."""

import pandas as pd
import pytest

from backend.ml.models.value_model import calculate_ai_value_scores


class TestAIValueScore:
    def _make_scores_df(self, players: list[dict]) -> pd.DataFrame:
        return pd.DataFrame(players)

    def test_high_value_player_scores_high(self):
        """A player with strong scores across the board should rank high."""
        df = self._make_scores_df([{
            "player_id": 1,
            "sleeper_score": 80.0,
            "bust_score": 10.0,
            "regression_direction": 0.02,
            "consistency_score": 85.0,
            "improvement_score": 50.0,
            "auction_value": 35.0,
            "dynasty_value": 90.0,
            "surplus_value": 10.0,
        }])
        ages = {1: 25}
        result = calculate_ai_value_scores(df, ages)

        score = result.iloc[0]["ai_value_score"]
        assert score > 70, f"High-value player should score >70, got {score}"

    def test_bust_risk_player_scores_lower(self):
        """A player with high bust risk should score lower."""
        df = self._make_scores_df([{
            "player_id": 2,
            "sleeper_score": 20.0,
            "bust_score": 85.0,
            "regression_direction": -0.03,
            "consistency_score": 30.0,
            "improvement_score": -40.0,
            "auction_value": 25.0,
            "dynasty_value": 20.0,
            "surplus_value": -5.0,
        }])
        ages = {2: 34}
        result = calculate_ai_value_scores(df, ages)

        score = result.iloc[0]["ai_value_score"]
        assert score < 50, f"Bust-risk player should score <50, got {score}"

    def test_score_in_valid_range(self):
        """All scores should be between 0 and 100."""
        df = self._make_scores_df([
            {"player_id": 1, "sleeper_score": 100, "bust_score": 0,
             "consistency_score": 100, "improvement_score": 100,
             "auction_value": 50, "dynasty_value": 100},
            {"player_id": 2, "sleeper_score": 0, "bust_score": 100,
             "consistency_score": 0, "improvement_score": -100,
             "auction_value": 1, "dynasty_value": 0},
        ])
        ages = {1: 24, 2: 38}
        result = calculate_ai_value_scores(df, ages)

        for _, row in result.iterrows():
            assert 0 <= row["ai_value_score"] <= 100

    def test_young_player_bonus(self):
        """A young pre-peak player should get an age curve bonus."""
        young = self._make_scores_df([{
            "player_id": 1, "sleeper_score": 50, "bust_score": 50,
            "consistency_score": 50, "improvement_score": 0,
            "auction_value": 20, "dynasty_value": 50,
        }])
        old = self._make_scores_df([{
            "player_id": 2, "sleeper_score": 50, "bust_score": 50,
            "consistency_score": 50, "improvement_score": 0,
            "auction_value": 20, "dynasty_value": 50,
        }])

        young_result = calculate_ai_value_scores(young, {1: 24})
        old_result = calculate_ai_value_scores(old, {2: 36})

        assert young_result.iloc[0]["ai_value_score"] > old_result.iloc[0]["ai_value_score"]

    def test_value_components_included(self):
        """Result should include component breakdown dict."""
        df = self._make_scores_df([{
            "player_id": 1, "sleeper_score": 60, "bust_score": 30,
            "consistency_score": 70, "improvement_score": 20,
            "auction_value": 25, "dynasty_value": 60,
        }])
        result = calculate_ai_value_scores(df, {1: 27})

        assert "value_components" in result.columns
        components = result.iloc[0]["value_components"]
        assert "projected_value" in components
        assert "sleeper_upside" in components
        assert "bust_safety" in components
        assert "dynasty_premium" in components

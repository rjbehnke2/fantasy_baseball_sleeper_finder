"""Tests for the feature engineering pipeline."""

import numpy as np
import pandas as pd
import pytest

from backend.data_pipeline.transformers.feature_engineering import (
    engineer_batting_features,
    engineer_pitching_features,
)


class TestBattingFeatureEngineering:
    def _make_batting_df(self, seasons: list[dict]) -> pd.DataFrame:
        return pd.DataFrame(seasons)

    def test_differential_features(self):
        """Should compute actual-vs-expected differentials."""
        df = self._make_batting_df([
            {"player_id": 1, "season": 2023, "pa": 600,
             "woba": 0.350, "xwoba": 0.320, "avg": 0.280, "xba": 0.260,
             "slg": 0.450, "xslg": 0.420, "babip": 0.320,
             "k_pct": 0.20, "bb_pct": 0.10, "barrel_pct": 0.10},
        ])
        result = engineer_batting_features(df, {1: 27})

        assert len(result) == 1
        row = result.iloc[0]
        assert abs(row["woba_minus_xwoba"] - 0.030) < 0.001
        assert abs(row["ba_minus_xba"] - 0.020) < 0.001
        assert abs(row["babip_minus_league"] - 0.024) < 0.001

    def test_yoy_delta_features(self):
        """Should compute year-over-year deltas correctly."""
        df = self._make_batting_df([
            {"player_id": 1, "season": 2023, "pa": 600,
             "k_pct": 0.18, "bb_pct": 0.12, "barrel_pct": 0.14},
            {"player_id": 1, "season": 2022, "pa": 550,
             "k_pct": 0.22, "bb_pct": 0.10, "barrel_pct": 0.10},
        ])
        result = engineer_batting_features(df, {1: 27})

        row = result.iloc[0]
        assert abs(row["k_pct_yoy_delta"] - (-0.04)) < 0.001
        assert abs(row["bb_pct_yoy_delta"] - 0.02) < 0.001
        assert abs(row["barrel_pct_yoy_delta"] - 0.04) < 0.001

    def test_age_bucket_features(self):
        """Should assign correct age buckets."""
        df = self._make_batting_df([
            {"player_id": 1, "season": 2023, "pa": 600, "k_pct": 0.20},
            {"player_id": 2, "season": 2023, "pa": 600, "k_pct": 0.20},
            {"player_id": 3, "season": 2023, "pa": 600, "k_pct": 0.20},
        ])
        ages = {1: 23, 2: 28, 3: 35}
        result = engineer_batting_features(df, ages)

        age_map = {row["player_id"]: row for _, row in result.iterrows()}
        assert age_map[1]["age_bucket"] == 0  # pre-peak
        assert age_map[2]["age_bucket"] == 1  # peak
        assert age_map[3]["age_bucket"] == 3  # late decline

    def test_trend_slope_features(self):
        """Should compute multi-year trend slopes."""
        df = self._make_batting_df([
            {"player_id": 1, "season": 2023, "pa": 600, "barrel_pct": 0.14},
            {"player_id": 1, "season": 2022, "pa": 550, "barrel_pct": 0.10},
            {"player_id": 1, "season": 2021, "pa": 500, "barrel_pct": 0.06},
        ])
        result = engineer_batting_features(df, {1: 27})

        row = result.iloc[0]
        # Slope should be ~0.04 per year (steady improvement)
        assert row["barrel_pct_3yr_trend"] is not None
        assert row["barrel_pct_3yr_trend"] > 0.03

    def test_empty_input(self):
        """Empty input should return empty DataFrame."""
        result = engineer_batting_features(pd.DataFrame(), {})
        assert len(result) == 0

    def test_missing_ages_excluded(self):
        """Players without age data should be excluded."""
        df = self._make_batting_df([
            {"player_id": 1, "season": 2023, "pa": 600, "k_pct": 0.20},
        ])
        result = engineer_batting_features(df, {})  # No ages
        assert len(result) == 0


class TestPitchingFeatureEngineering:
    def test_pitcher_differential_features(self):
        """Should compute pitcher differential features."""
        df = pd.DataFrame([{
            "player_id": 10, "season": 2023, "ip": 180, "gs": 30,
            "era": 3.50, "fip": 3.80, "xera": 3.60, "xfip": 3.70,
            "babip": 0.280, "lob_pct": 0.78, "hr_fb_pct": 0.10,
            "k_pct": 0.28, "bb_pct": 0.07, "k_bb_pct": 0.21,
            "swstr_pct": 0.12, "csw_pct": 0.30,
        }])
        result = engineer_pitching_features(df, {10: 27})

        assert len(result) == 1
        row = result.iloc[0]
        assert abs(row["era_minus_fip"] - (-0.30)) < 0.01
        assert abs(row["era_minus_xera"] - (-0.10)) < 0.01
        assert row["is_starter"] == 1

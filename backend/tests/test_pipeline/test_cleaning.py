"""Tests for data cleaning utilities."""

import numpy as np
import pandas as pd
import pytest

from backend.data_pipeline.transformers.cleaning import (
    _parse_pct_column,
    clean_batting_stats,
    clean_pitching_stats,
)


class TestParsePercentage:
    def test_string_percentage(self):
        """Should parse '25.0%' -> 0.25."""
        series = pd.Series(["25.0%", "10.5%", "0.0%"])
        result = _parse_pct_column(series)
        assert abs(result.iloc[0] - 0.25) < 0.001
        assert abs(result.iloc[1] - 0.105) < 0.001

    def test_float_in_0_to_1_range(self):
        """Should pass through floats already in 0-1 range."""
        series = pd.Series([0.25, 0.105, 0.0])
        result = _parse_pct_column(series)
        assert abs(result.iloc[0] - 0.25) < 0.001

    def test_float_in_0_to_100_range(self):
        """Should convert floats in 0-100 range to 0-1."""
        series = pd.Series([25.0, 10.5, 0.0])
        result = _parse_pct_column(series)
        assert abs(result.iloc[0] - 0.25) < 0.001

    def test_handles_nan(self):
        """Should handle NaN values."""
        series = pd.Series(["25.0%", "", None])
        result = _parse_pct_column(series)
        assert not np.isnan(result.iloc[0])
        assert np.isnan(result.iloc[1])


class TestCleanBattingStats:
    def test_renames_columns(self):
        """Should rename FanGraphs columns to our schema."""
        df = pd.DataFrame({
            "IDfg": ["12345"],
            "Name": ["Mike Trout"],
            "Team": ["LAA"],
            "Season": [2024],
            "PA": [600],
            "HR": [30],
            "AVG": [0.280],
            "K%": [0.22],
        })
        result = clean_batting_stats(df)

        assert "fangraphs_id" in result.columns
        assert "full_name" in result.columns
        assert "k_pct" in result.columns
        assert result.iloc[0]["full_name"] == "Mike Trout"

    def test_drops_unknown_columns(self):
        """Should not include unmapped columns."""
        df = pd.DataFrame({
            "IDfg": ["12345"],
            "Name": ["Test Player"],
            "Season": [2024],
            "PA": [100],
            "SomeRandomStat": [42],
        })
        result = clean_batting_stats(df)
        assert "SomeRandomStat" not in result.columns

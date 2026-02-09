"""Data cleaning utilities for baseball statistics.

Handles column name normalization, type coercion, null handling, and
mapping of FanGraphs column names to our schema column names.
"""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# FanGraphs batting columns -> our schema columns
BATTING_COLUMN_MAP = {
    "IDfg": "fangraphs_id",
    "Name": "full_name",
    "Team": "team",
    "Season": "season",
    "PA": "pa",
    "AB": "ab",
    "H": "h",
    "HR": "hr",
    "RBI": "rbi",
    "R": "r",
    "SB": "sb",
    "CS": "cs",
    "AVG": "avg",
    "OBP": "obp",
    "SLG": "slg",
    "OPS": "ops",
    "ISO": "iso",
    "BABIP": "babip",
    "wOBA": "woba",
    "xwOBA": "xwoba",
    "wRC+": "wrc_plus",
    "WAR": "war",
    "K%": "k_pct",
    "BB%": "bb_pct",
    "Barrel%": "barrel_pct",
    "HardHit%": "hard_hit_pct",
    "EV": "avg_exit_velocity",
    "LA": "avg_launch_angle",
    "Spd": "sprint_speed",
    "GB%": "gb_pct",
    "FB%": "fb_pct",
    "LD%": "ld_pct",
    "xBA": "xba",
    "xSLG": "xslg",
}

# FanGraphs pitching columns -> our schema columns
PITCHING_COLUMN_MAP = {
    "IDfg": "fangraphs_id",
    "Name": "full_name",
    "Team": "team",
    "Season": "season",
    "W": "w",
    "L": "l",
    "SV": "sv",
    "HLD": "hld",
    "IP": "ip",
    "GS": "gs",
    "G": "g",
    "SO": "so",
    "BB": "bb",
    "H": "h",
    "HR": "hr",
    "ERA": "era",
    "WHIP": "whip",
    "BABIP": "babip",
    "FIP": "fip",
    "xFIP": "xfip",
    "SIERA": "siera",
    "WAR": "war",
    "K%": "k_pct",
    "BB%": "bb_pct",
    "K-BB%": "k_bb_pct",
    "SwStr%": "swstr_pct",
    "CSW%": "csw_pct",
    "Barrel%": "barrel_pct_against",
    "HardHit%": "hard_hit_pct_against",
    "GB%": "gb_pct",
    "FB%": "fb_pct",
    "HR/FB": "hr_fb_pct",
    "LOB%": "lob_pct",
    "Stuff+": "stuff_plus",
    "xERA": "xera",
}


def clean_batting_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and normalize FanGraphs batting stats.

    Args:
        df: Raw DataFrame from pybaseball.batting_stats().

    Returns:
        Cleaned DataFrame with normalized column names and types.
    """
    # Rename columns we know about, drop the rest
    available = {k: v for k, v in BATTING_COLUMN_MAP.items() if k in df.columns}
    cleaned = df[list(available.keys())].rename(columns=available).copy()

    # Convert percentage strings to floats (FanGraphs sometimes returns "25.0%" strings)
    pct_cols = [c for c in cleaned.columns if c.endswith("_pct")]
    for col in pct_cols:
        cleaned[col] = _parse_pct_column(cleaned[col])

    # Ensure correct types
    int_cols = ["pa", "ab", "h", "hr", "rbi", "r", "sb", "cs", "wrc_plus", "season"]
    for col in int_cols:
        if col in cleaned.columns:
            cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce").astype("Int64")

    float_cols = [c for c in cleaned.columns if c not in int_cols + ["fangraphs_id", "full_name", "team"]]
    for col in float_cols:
        if col in cleaned.columns:
            cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")

    cleaned["fangraphs_id"] = cleaned["fangraphs_id"].astype(str)

    logger.info(f"Cleaned batting stats: {len(cleaned)} rows, {len(cleaned.columns)} columns")
    return cleaned


def clean_pitching_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and normalize FanGraphs pitching stats.

    Args:
        df: Raw DataFrame from pybaseball.pitching_stats().

    Returns:
        Cleaned DataFrame with normalized column names and types.
    """
    available = {k: v for k, v in PITCHING_COLUMN_MAP.items() if k in df.columns}
    cleaned = df[list(available.keys())].rename(columns=available).copy()

    pct_cols = [c for c in cleaned.columns if c.endswith("_pct")]
    for col in pct_cols:
        cleaned[col] = _parse_pct_column(cleaned[col])

    int_cols = ["w", "l", "sv", "hld", "gs", "g", "so", "bb", "h", "hr", "season"]
    for col in int_cols:
        if col in cleaned.columns:
            cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce").astype("Int64")

    float_cols = [c for c in cleaned.columns if c not in int_cols + ["fangraphs_id", "full_name", "team"]]
    for col in float_cols:
        if col in cleaned.columns:
            cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")

    cleaned["fangraphs_id"] = cleaned["fangraphs_id"].astype(str)

    logger.info(f"Cleaned pitching stats: {len(cleaned)} rows, {len(cleaned.columns)} columns")
    return cleaned


def _parse_pct_column(series: pd.Series) -> pd.Series:
    """Convert percentage column to float, handling both '25.0%' strings and 0.25 floats."""
    if series.dtype.kind in ("O", "U") or str(series.dtype) == "str" or str(series.dtype) == "string":
        # String percentage like "25.0%"
        stripped = series.astype(str).str.replace("%", "", regex=False).str.strip()
        stripped = stripped.replace({"": np.nan, "None": np.nan, "nan": np.nan})
        return pd.to_numeric(stripped, errors="coerce") / 100.0
    # Already a float — check if it's in 0-1 range or 0-100 range
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.max() > 1.0:
        return numeric / 100.0
    return numeric

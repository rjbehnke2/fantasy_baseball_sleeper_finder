"""Feature engineering for ML models.

Computes differential features (actual vs. expected), trend features (YoY deltas),
age curve features, and context features from raw batting/pitching season data.
"""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Peak ages for age curve calculations
BATTER_PEAK_AGE = 27
PITCHER_PEAK_AGE = 26


def engineer_batting_features(batting_df: pd.DataFrame, player_ages: dict[int, int]) -> pd.DataFrame:
    """Build ML-ready feature matrix from multi-season batting data.

    Args:
        batting_df: DataFrame with batting_seasons rows (must include player_id, season).
        player_ages: Dict mapping player_id -> current age.

    Returns:
        DataFrame with one row per player, containing all engineered features.
    """
    if batting_df.empty:
        return pd.DataFrame()

    features = []
    for player_id, group in batting_df.groupby("player_id"):
        seasons = group.sort_values("season", ascending=False)
        age = player_ages.get(player_id)
        if age is None or len(seasons) == 0:
            continue

        latest = seasons.iloc[0]
        row = {"player_id": player_id}

        # --- Differential features (actual vs. expected) ---
        row["woba_minus_xwoba"] = _safe_diff(latest, "woba", "xwoba")
        row["ba_minus_xba"] = _safe_diff(latest, "avg", "xba")
        row["slg_minus_xslg"] = _safe_diff(latest, "slg", "xslg")
        row["babip_minus_league"] = _safe_sub(latest.get("babip"), 0.296)

        # --- Year-over-year delta features ---
        yoy_stats = [
            "barrel_pct", "hard_hit_pct", "k_pct", "bb_pct", "avg_exit_velocity",
            "woba", "xwoba", "iso", "wrc_plus", "sprint_speed",
        ]
        for stat in yoy_stats:
            row[f"{stat}_yoy_delta"] = _yoy_delta(seasons, stat)
            row[f"{stat}_2yr_trend"] = _multi_year_trend_slope(seasons, stat, n=2)
            row[f"{stat}_3yr_trend"] = _multi_year_trend_slope(seasons, stat, n=3)

        # --- Age curve features ---
        row["age"] = age
        row["years_from_peak"] = age - BATTER_PEAK_AGE
        row["age_bucket"] = _age_bucket(age, BATTER_PEAK_AGE)
        row["pre_peak"] = 1 if age < BATTER_PEAK_AGE else 0

        # --- Playing time trend ---
        row["pa_yoy_delta"] = _yoy_delta(seasons, "pa")
        row["pa_latest"] = latest.get("pa", 0) or 0

        # --- Latest stats as features ---
        for stat in ["barrel_pct", "hard_hit_pct", "k_pct", "bb_pct",
                      "avg_exit_velocity", "sprint_speed", "woba", "xwoba",
                      "iso", "babip", "war", "gb_pct", "fb_pct", "ld_pct"]:
            row[f"latest_{stat}"] = latest.get(stat)

        row["seasons_available"] = len(seasons)
        features.append(row)

    result = pd.DataFrame(features)
    logger.info(f"Engineered {len(result)} batter feature rows with {len(result.columns)} features")
    return result


def engineer_pitching_features(
    pitching_df: pd.DataFrame, player_ages: dict[int, int]
) -> pd.DataFrame:
    """Build ML-ready feature matrix from multi-season pitching data.

    Args:
        pitching_df: DataFrame with pitching_seasons rows (must include player_id, season).
        player_ages: Dict mapping player_id -> current age.

    Returns:
        DataFrame with one row per player, containing all engineered features.
    """
    if pitching_df.empty:
        return pd.DataFrame()

    features = []
    for player_id, group in pitching_df.groupby("player_id"):
        seasons = group.sort_values("season", ascending=False)
        age = player_ages.get(player_id)
        if age is None or len(seasons) == 0:
            continue

        latest = seasons.iloc[0]
        row = {"player_id": player_id}

        # --- Differential features ---
        row["era_minus_fip"] = _safe_diff(latest, "era", "fip")
        row["era_minus_xera"] = _safe_diff(latest, "era", "xera")
        row["fip_minus_xfip"] = _safe_diff(latest, "fip", "xfip")
        row["babip_minus_league"] = _safe_sub(latest.get("babip"), 0.296)
        row["lob_pct_minus_league"] = _safe_sub(latest.get("lob_pct"), 0.72)
        row["hr_fb_pct_minus_league"] = _safe_sub(latest.get("hr_fb_pct"), 0.132)

        # --- Year-over-year delta features ---
        yoy_stats = [
            "k_pct", "bb_pct", "k_bb_pct", "swstr_pct", "csw_pct",
            "barrel_pct_against", "hard_hit_pct_against", "gb_pct",
            "era", "fip", "siera", "whip",
        ]
        for stat in yoy_stats:
            row[f"{stat}_yoy_delta"] = _yoy_delta(seasons, stat)
            row[f"{stat}_2yr_trend"] = _multi_year_trend_slope(seasons, stat, n=2)
            row[f"{stat}_3yr_trend"] = _multi_year_trend_slope(seasons, stat, n=3)

        # --- Age curve features ---
        row["age"] = age
        row["years_from_peak"] = age - PITCHER_PEAK_AGE
        row["age_bucket"] = _age_bucket(age, PITCHER_PEAK_AGE)
        row["pre_peak"] = 1 if age < PITCHER_PEAK_AGE else 0

        # --- Role features ---
        row["is_starter"] = 1 if (latest.get("gs", 0) or 0) > 5 else 0
        row["ip_latest"] = latest.get("ip", 0) or 0
        row["ip_yoy_delta"] = _yoy_delta(seasons, "ip")

        # --- Latest stats ---
        for stat in ["k_pct", "bb_pct", "k_bb_pct", "swstr_pct", "csw_pct",
                      "era", "fip", "xfip", "siera", "whip", "war",
                      "barrel_pct_against", "hard_hit_pct_against",
                      "gb_pct", "lob_pct", "hr_fb_pct", "stuff_plus", "xera"]:
            row[f"latest_{stat}"] = latest.get(stat)

        row["seasons_available"] = len(seasons)
        features.append(row)

    result = pd.DataFrame(features)
    logger.info(
        f"Engineered {len(result)} pitcher feature rows with {len(result.columns)} features"
    )
    return result


# ---- Helper functions ----


def _safe_diff(row, col_a: str, col_b: str) -> float | None:
    """Compute row[col_a] - row[col_b], returning None if either is missing."""
    a = row.get(col_a) if isinstance(row, dict) else getattr(row, col_a, None)
    b = row.get(col_b) if isinstance(row, dict) else getattr(row, col_b, None)
    if a is not None and b is not None and not (np.isnan(a) or np.isnan(b)):
        return float(a - b)
    return None


def _safe_sub(val, baseline: float) -> float | None:
    """Subtract a baseline from a value, returning None if val is missing."""
    if val is not None and not (isinstance(val, float) and np.isnan(val)):
        return float(val - baseline)
    return None


def _yoy_delta(seasons: pd.DataFrame, stat: str) -> float | None:
    """Compute most-recent minus previous season for a stat."""
    vals = seasons[stat].dropna() if stat in seasons.columns else pd.Series(dtype=float)
    if len(vals) < 2:
        return None
    return float(vals.iloc[0] - vals.iloc[1])


def _multi_year_trend_slope(seasons: pd.DataFrame, stat: str, n: int = 3) -> float | None:
    """Fit a linear regression slope across up to n seasons.

    Returns the slope (per-season change rate) or None if insufficient data.
    Seasons are ordered most recent first, so we reverse for regression.
    """
    if stat not in seasons.columns:
        return None
    vals = seasons[stat].dropna().head(n)
    if len(vals) < 2:
        return None
    # Reverse so x=0 is oldest, x=n-1 is most recent
    y = vals.values[::-1].astype(float)
    x = np.arange(len(y), dtype=float)
    # Simple least squares
    try:
        slope = np.polyfit(x, y, 1)[0]
        return float(slope)
    except (np.linalg.LinAlgError, ValueError):
        return None


def _age_bucket(age: int, peak_age: int) -> int:
    """Encode age into bucket: 0=pre-peak, 1=peak, 2=early-decline, 3=late-decline."""
    if age < peak_age:
        return 0
    elif age <= peak_age + 2:
        return 1
    elif age <= 32:
        return 2
    else:
        return 3

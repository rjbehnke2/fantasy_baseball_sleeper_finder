"""Skills-stat trajectory scoring (Improvement Score).

Quantifies whether a player shows genuine developmental trajectory by measuring
consistent YoY improvement in skills stats. Uses trend slope × r² × age multiplier.

Not an ML model — a statistical calculation from multi-year trends.
"""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Skills stats to track for hitters: stat -> (higher_is_improvement, stickiness_weight)
HITTER_SKILLS_STATS = {
    "k_pct": (False, 1.0),          # Lower K% = improvement
    "bb_pct": (True, 1.0),          # Higher BB% = improvement
    "barrel_pct": (True, 0.7),
    "hard_hit_pct": (True, 0.7),
    "avg_exit_velocity": (True, 0.7),
    "sprint_speed": (True, 0.4),
}

# Skills stats for pitchers
PITCHER_SKILLS_STATS = {
    "k_pct": (True, 1.0),           # Higher K% = improvement for pitchers
    "bb_pct": (False, 1.0),         # Lower BB% = improvement
    "k_bb_pct": (True, 1.0),
    "swstr_pct": (True, 0.7),
    "csw_pct": (True, 0.7),
    "gb_pct": (True, 0.7),          # Generally higher GB% = improvement
}

# Age multipliers: improvement that aligns with natural development is more credible
AGE_MULTIPLIERS = [
    (27, 1.2),   # age < 27: aligns with development
    (30, 1.0),   # age 27-30: neutral
    (33, 0.6),   # age 30-33: against aging curve
    (99, 0.3),   # age > 33: almost certainly noise
]

MIN_SEASONS = 2
PREFERRED_SEASONS = 3


def calculate_batter_improvement(
    batting_df: pd.DataFrame, player_ages: dict[int, int]
) -> pd.DataFrame:
    """Calculate improvement scores for all batters.

    Args:
        batting_df: DataFrame with batting seasons (must have player_id, season columns).
        player_ages: Dict mapping player_id -> current age.

    Returns:
        DataFrame with player_id, improvement_score (-100 to 100), stat_breakdown.
    """
    return _calculate_improvement(
        batting_df, HITTER_SKILLS_STATS, player_ages, "pa", min_playing_time=200
    )


def calculate_pitcher_improvement(
    pitching_df: pd.DataFrame, player_ages: dict[int, int]
) -> pd.DataFrame:
    """Calculate improvement scores for all pitchers.

    Args:
        pitching_df: DataFrame with pitching seasons (must have player_id, season columns).
        player_ages: Dict mapping player_id -> current age.

    Returns:
        DataFrame with player_id, improvement_score (-100 to 100), stat_breakdown.
    """
    return _calculate_improvement(
        pitching_df, PITCHER_SKILLS_STATS, player_ages, "ip", min_playing_time=40
    )


def _calculate_improvement(
    df: pd.DataFrame,
    skills_stats: dict,
    player_ages: dict[int, int],
    playing_time_col: str,
    min_playing_time: float,
) -> pd.DataFrame:
    """Core improvement scoring.

    For each player:
    1. Get last 3 seasons with sufficient playing time
    2. For each skills stat, fit a linear regression (trend_slope, trend_r²)
    3. Compute stat_improvement = normalize(slope) × r²
    4. Weight by stickiness tier, apply age multiplier
    5. Scale to -100..100
    """
    results = []

    for player_id, group in df.groupby("player_id"):
        age = player_ages.get(player_id)
        if age is None:
            continue

        qualifying = group[
            (group[playing_time_col].notna()) & (group[playing_time_col] >= min_playing_time)
        ].sort_values("season", ascending=False).head(PREFERRED_SEASONS)

        if len(qualifying) < MIN_SEASONS:
            continue

        stat_breakdown = {}
        weighted_sum = 0.0
        weight_total = 0.0

        for stat, (higher_is_improvement, tier_weight) in skills_stats.items():
            if stat not in qualifying.columns:
                continue

            values = qualifying[stat].dropna()
            if len(values) < MIN_SEASONS:
                continue

            # Fit linear regression: x = season index (0=oldest), y = stat value
            y = values.values[::-1].astype(float)  # Reverse so oldest first
            x = np.arange(len(y), dtype=float)

            try:
                coeffs = np.polyfit(x, y, 1)
                slope = coeffs[0]

                # Calculate R²
                y_pred = np.polyval(coeffs, x)
                ss_res = np.sum((y - y_pred) ** 2)
                ss_tot = np.sum((y - np.mean(y)) ** 2)
                r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
                r_squared = max(0.0, r_squared)  # Clamp to non-negative
            except (np.linalg.LinAlgError, ValueError):
                continue

            # Normalize slope relative to the stat's mean to make cross-stat comparable
            mean_val = abs(np.mean(y))
            if mean_val > 1e-6:
                normalized_slope = slope / mean_val
            else:
                normalized_slope = slope

            # If lower is improvement, flip the sign
            if not higher_is_improvement:
                normalized_slope = -normalized_slope

            # Improvement signal: slope discounted by fit quality
            stat_signal = normalized_slope * r_squared

            stat_breakdown[stat] = {
                "slope": round(float(slope), 6),
                "r_squared": round(float(r_squared), 4),
                "normalized_slope": round(float(normalized_slope), 6),
                "signal": round(float(stat_signal), 6),
                "direction": "improving" if stat_signal > 0.01 else (
                    "declining" if stat_signal < -0.01 else "flat"
                ),
                "seasons_used": len(values),
                "values": [round(float(v), 4) for v in y],
            }

            weighted_sum += tier_weight * stat_signal
            weight_total += tier_weight

        if weight_total == 0:
            continue

        raw_score = weighted_sum / weight_total

        # Apply age multiplier
        age_mult = _get_age_multiplier(age)

        # Scale to -100..100 range
        # A raw_score of ~0.15 (15% normalized improvement per year with good r²)
        # should map to roughly 70-80 on the scale
        scaled = raw_score * age_mult * 500  # Empirical scaling factor
        improvement_score = max(-100, min(100, round(scaled, 1)))

        results.append({
            "player_id": player_id,
            "improvement_score": improvement_score,
            "stat_improvement_breakdown": stat_breakdown,
            "age_multiplier": age_mult,
            "seasons_used": len(qualifying),
        })

    result_df = pd.DataFrame(results)
    logger.info(f"Calculated improvement scores for {len(result_df)} players")
    return result_df


def _get_age_multiplier(age: int) -> float:
    """Get the age-based trust multiplier for improvement signals."""
    for threshold, multiplier in AGE_MULTIPLIERS:
        if age < threshold:
            return multiplier
    return 0.3

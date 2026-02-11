"""Multi-year consistency scoring weighted by stat stickiness.

Measures how repeatable a player's skills-based performance is across seasons.
Stats are weighted by their year-over-year correlation (stickiness) so that
consistency in K% matters more than consistency in BABIP.

Not an ML model — a statistical calculation.
"""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Stickiness tiers: stat -> (tier_weight, higher_is_better)
# Weights reflect YoY correlation strength
BATTER_STICKY_STATS = {
    # Tier 1 (weight 1.0) — highest YoY correlation
    "k_pct": (1.0, False),        # r = .84; lower is better for hitters
    "bb_pct": (1.0, True),        # r = .76
    "iso": (1.0, True),           # r = .76
    # Tier 2 (weight 0.7)
    "barrel_pct": (0.7, True),    # r = .80
    "avg_exit_velocity": (0.7, True),  # r = .82
    "hard_hit_pct": (0.7, True),  # r = .78
    "gb_pct": (0.7, None),        # r = .75; direction depends on player type
    "fb_pct": (0.7, None),        # r = .72
    # Tier 3 (weight 0.4)
    "woba": (0.4, True),
    "wrc_plus": (0.4, True),
    "sprint_speed": (0.4, True),
}

PITCHER_STICKY_STATS = {
    # Tier 1
    "k_pct": (1.0, True),         # r = .75; higher is better for pitchers
    "k_bb_pct": (1.0, True),      # r = .70+
    "swstr_pct": (1.0, True),
    # Tier 2
    "csw_pct": (0.7, True),
    "gb_pct": (0.7, None),        # r = .78
    "fip": (0.7, False),          # lower is better
    "siera": (0.7, False),
    # Tier 3
    "xera": (0.4, False),
    "stuff_plus": (0.4, True),
}

MIN_SEASONS = 2
PREFERRED_SEASONS = 3


def calculate_batter_consistency(batting_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate consistency scores for all batters.

    Args:
        batting_df: DataFrame with batting seasons (must have player_id, season columns).

    Returns:
        DataFrame with player_id, consistency_score (0-100), stat_breakdown (dict).
    """
    return _calculate_consistency(batting_df, BATTER_STICKY_STATS, "pa", min_playing_time=200)


def calculate_pitcher_consistency(pitching_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate consistency scores for all pitchers.

    Args:
        pitching_df: DataFrame with pitching seasons (must have player_id, season columns).

    Returns:
        DataFrame with player_id, consistency_score (0-100), stat_breakdown (dict).
    """
    return _calculate_consistency(pitching_df, PITCHER_STICKY_STATS, "ip", min_playing_time=40)


def _calculate_consistency(
    df: pd.DataFrame,
    sticky_stats: dict,
    playing_time_col: str,
    min_playing_time: float,
) -> pd.DataFrame:
    """Core consistency calculation across players.

    For each player:
    1. Get last 3 seasons with sufficient playing time
    2. For each sticky stat, compute CV (coefficient of variation)
    3. Convert CV to per-stat consistency (1 - normalized_cv)
    4. Weighted average using stickiness tier weights
    5. Scale to 0-100
    """
    results = []

    for player_id, group in df.groupby("player_id"):
        # Filter to qualifying seasons and take the most recent 3
        qualifying = group[
            (group[playing_time_col].notna()) & (group[playing_time_col] >= min_playing_time)
        ].sort_values("season", ascending=False).head(PREFERRED_SEASONS)

        if len(qualifying) < MIN_SEASONS:
            continue

        stat_breakdown = {}
        weighted_sum = 0.0
        weight_total = 0.0

        for stat, (tier_weight, _direction) in sticky_stats.items():
            if stat not in qualifying.columns:
                continue

            values = qualifying[stat].dropna()
            if len(values) < MIN_SEASONS:
                continue

            mean_val = values.mean()
            std_val = values.std(ddof=1)

            # CV = std / |mean| — measures relative variability
            # Handle edge cases: if mean is 0 or very small, use absolute std
            if abs(mean_val) > 1e-6:
                cv = std_val / abs(mean_val)
            else:
                cv = std_val * 10  # Penalize if mean is ~0 but there's variance

            # Normalize CV: cap at 1.0 (anything above = wildly inconsistent)
            normalized_cv = min(cv, 1.0)

            # Per-stat consistency: 1 = perfectly consistent, 0 = wildly variable
            stat_consistency = 1.0 - normalized_cv

            stat_breakdown[stat] = {
                "consistency": round(stat_consistency, 4),
                "cv": round(cv, 4),
                "mean": round(mean_val, 4),
                "std": round(std_val, 4),
                "seasons_used": len(values),
            }

            weighted_sum += tier_weight * stat_consistency
            weight_total += tier_weight

        if weight_total == 0:
            continue

        raw_score = weighted_sum / weight_total
        # Scale to 0-100
        consistency_score = round(raw_score * 100, 1)

        results.append({
            "player_id": player_id,
            "consistency_score": consistency_score,
            "stat_consistency_breakdown": stat_breakdown,
            "seasons_used": len(qualifying),
        })

    result_df = pd.DataFrame(results)
    logger.info(f"Calculated consistency scores for {len(result_df)} players")
    return result_df

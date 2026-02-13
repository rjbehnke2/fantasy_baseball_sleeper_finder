"""Composite AI Value Score — single 0-100 number combining all model outputs.

Weighted for dynasty auction leagues: long-term trajectory, age curves, and
surplus value all factor into the final score. Integrates career trajectory
projections for multi-season dynasty value.
"""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Default weights (calibrated for dynasty auction format)
# trajectory_outlook added for career trajectory model integration
DEFAULT_WEIGHTS = {
    "projected_value": 0.22,      # Marcel + regression adjustment
    "sleeper_upside": 0.10,       # sleeper_score * (1 - current_value_pct)
    "bust_safety": 0.08,          # 100 - bust_score
    "consistency": 0.12,          # consistency_score
    "age_curve": 0.08,            # Age-based factor
    "dynasty_premium": 0.13,      # Long-term outlook
    "improvement": 0.10,          # Skills trajectory
    "opportunity": 0.05,          # Playing time / role security
    "trajectory_outlook": 0.12,   # Career trajectory model projection
}

BATTER_PEAK_AGE = 27
PITCHER_PEAK_AGE = 26


def calculate_ai_value_scores(
    scores_df: pd.DataFrame,
    player_ages: dict[int, int],
    player_types: dict[int, str] | None = None,
    weights: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Calculate composite AI Value Score for all players.

    Args:
        scores_df: DataFrame with player_id and all model score columns:
            - sleeper_score (0-100)
            - bust_score (0-100)
            - regression_direction (signed float)
            - consistency_score (0-100)
            - improvement_score (-100 to 100)
            - auction_value (dollar amount)
            - dynasty_value (0-100)
        player_ages: Dict mapping player_id -> current age.
        player_types: Dict mapping player_id -> "batter" or "pitcher".
        weights: Custom weight overrides.

    Returns:
        DataFrame with player_id and ai_value_score (0-100), plus component breakdown.
    """
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    # Normalize weights to sum to 1
    total_w = sum(w.values())
    w = {k: v / total_w for k, v in w.items()}

    results = []
    for _, row in scores_df.iterrows():
        pid = row["player_id"]
        age = player_ages.get(pid, 30)
        ptype = (player_types or {}).get(pid, "batter")
        peak_age = BATTER_PEAK_AGE if ptype == "batter" else PITCHER_PEAK_AGE

        components = {}

        # 1. Projected value (normalized from auction_value)
        auction_val = row.get("auction_value", 0) or 0
        # Scale: $40+ = 100, $1 = 10
        components["projected_value"] = min(100, max(0, auction_val * 2.5))

        # 2. Sleeper upside
        sleeper = row.get("sleeper_score", 0) or 0
        components["sleeper_upside"] = sleeper

        # 3. Bust safety (inverse of bust score)
        bust = row.get("bust_score", 0) or 0
        components["bust_safety"] = 100 - bust

        # 4. Consistency
        consistency = row.get("consistency_score") or 50  # Default to neutral
        components["consistency"] = consistency

        # 5. Age curve factor
        components["age_curve"] = _age_curve_score(age, peak_age)

        # 6. Dynasty premium
        dynasty = row.get("dynasty_value", 0) or 0
        components["dynasty_premium"] = dynasty

        # 7. Improvement score (rescale from -100..100 to 0..100)
        improvement = row.get("improvement_score", 0) or 0
        components["improvement"] = min(100, max(0, (improvement + 100) / 2))

        # 8. Opportunity (playing time proxy from auction value ranking)
        components["opportunity"] = min(100, max(0, auction_val * 3))

        # 9. Trajectory outlook (from career trajectory model)
        components["trajectory_outlook"] = _trajectory_outlook_score(
            age, peak_age, improvement, dynasty
        )

        # Weighted combination
        ai_value = sum(w[k] * components[k] for k in w if k in components)
        ai_value = round(max(0, min(100, ai_value)), 1)

        results.append({
            "player_id": pid,
            "ai_value_score": ai_value,
            "value_components": {k: round(v, 1) for k, v in components.items()},
        })

    result_df = pd.DataFrame(results)
    logger.info(f"Calculated AI Value Scores for {len(result_df)} players")
    return result_df


def _trajectory_outlook_score(
    age: int, peak_age: int, improvement: float, dynasty: float
) -> float:
    """Score combining trajectory model signals (0-100).

    Blends the career trajectory outlook with improvement momentum and
    dynasty value for a forward-looking assessment.
    """
    # Base: dynasty value already captures multi-year outlook
    base = dynasty * 0.5

    # Improvement momentum (rescaled from -100..100 to contribution)
    if improvement > 0:
        # Positive improvement more valuable for younger players
        age_trust = max(0.3, 1.0 - max(0, age - peak_age) * 0.12)
        base += improvement * 0.3 * age_trust
    else:
        # Negative improvement is a penalty
        base += improvement * 0.2

    # Years-to-peak bonus (further from peak in the young direction = more upside)
    years_to_peak = peak_age - age
    if years_to_peak > 0:
        base += min(20, years_to_peak * 5)  # Up to +20 for very young players
    elif years_to_peak < -5:
        base -= min(15, abs(years_to_peak + 5) * 3)  # Penalty for well past peak

    return max(0, min(100, base))


def _age_curve_score(age: int, peak_age: int) -> float:
    """Score based on position on the age curve (0-100).

    Pre-peak players get a premium, post-peak get a penalty.
    """
    if age < peak_age - 2:
        return 90  # Young and developing
    elif age < peak_age:
        return 85  # Approaching peak
    elif age <= peak_age + 2:
        return 75  # Peak years
    elif age <= 32:
        return 55  # Early decline
    elif age <= 35:
        return 35  # Late decline
    else:
        return 15  # Very late career

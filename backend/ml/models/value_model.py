"""Composite AI Value Score — single 0-100 number combining all model outputs.

Weighted for dynasty auction leagues: long-term trajectory, age curves, and
surplus value all factor into the final score.
"""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Default weights (calibrated for dynasty auction format)
DEFAULT_WEIGHTS = {
    "projected_value": 0.25,      # Marcel + regression adjustment
    "sleeper_upside": 0.10,       # sleeper_score * (1 - current_value_pct)
    "bust_safety": 0.10,          # 100 - bust_score
    "consistency": 0.15,          # consistency_score
    "age_curve": 0.10,            # Age-based factor
    "dynasty_premium": 0.15,      # Long-term outlook
    "improvement": 0.10,          # Skills trajectory
    "opportunity": 0.05,          # Playing time / role security
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

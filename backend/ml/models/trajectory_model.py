"""Career trajectory model — multi-season value projection with confidence bands.

Projects a player's year-by-year fantasy value over the next N seasons using:
1. Research-based aging curves (position-specific)
2. Player-specific adjustment from improvement score + consistency
3. Injury/decline risk widening confidence bands further into the future

This replaces the planned TFT model with a practical statistical approach
that uses the same aging-curve research and integrates with existing scores.
"""

import logging
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

# Research-based aging curves: age -> multiplier on peak value
# Sources: FanGraphs aging curves, Tom Tango's research, Jeff Zimmerman studies
# These represent the average % of peak production at each age
BATTER_AGING_CURVE = {
    20: 0.55, 21: 0.65, 22: 0.75, 23: 0.83, 24: 0.90, 25: 0.95,
    26: 0.98, 27: 1.00, 28: 0.98, 29: 0.95, 30: 0.91, 31: 0.87,
    32: 0.82, 33: 0.76, 34: 0.70, 35: 0.63, 36: 0.55, 37: 0.47,
    38: 0.39, 39: 0.32, 40: 0.25,
}

PITCHER_AGING_CURVE = {
    20: 0.60, 21: 0.70, 22: 0.78, 23: 0.85, 24: 0.91, 25: 0.96,
    26: 1.00, 27: 0.98, 28: 0.95, 29: 0.91, 30: 0.86, 31: 0.81,
    32: 0.75, 33: 0.68, 34: 0.61, 35: 0.53, 36: 0.45, 37: 0.37,
    38: 0.30, 39: 0.23, 40: 0.17,
}

# Confidence band widths (std dev multiplier per year into the future)
# Year 1 is fairly predictable, gets progressively wider
BASE_CONFIDENCE_WIDTHS = [0.08, 0.14, 0.20, 0.26, 0.32, 0.38, 0.44, 0.50]


@dataclass
class TrajectoryPoint:
    """A single point on the projected career trajectory."""

    season: int
    projected_value: float  # 0-100 scale
    upper_bound: float  # 80% confidence upper
    lower_bound: float  # 80% confidence lower
    age: int


@dataclass
class CareerTrajectory:
    """Full career trajectory projection for a player."""

    player_id: int
    current_value: float
    trajectory: list[TrajectoryPoint]
    peak_season: int  # projected best remaining season
    peak_value: float
    career_war_remaining: float  # sum of projected values (proxy for total remaining value)
    trajectory_grade: str  # "Rising", "Peak", "Plateau", "Declining", "Late Career"


def project_career_trajectory(
    player_id: int,
    current_age: int,
    current_value: float,
    player_type: str = "batter",
    improvement_score: float = 0.0,
    consistency_score: float = 50.0,
    dynasty_value: float = 50.0,
    projection_years: int = 6,
    current_season: int = 2025,
) -> CareerTrajectory:
    """Project a player's multi-season value trajectory.

    Args:
        player_id: Player identifier.
        current_age: Player's current age.
        current_value: Current AI value score or dynasty value (0-100).
        player_type: "batter" or "pitcher".
        improvement_score: From improvement model (-100 to 100).
        consistency_score: From consistency model (0-100).
        dynasty_value: Current dynasty value score (0-100).
        projection_years: Number of future seasons to project.
        current_season: Current year for labeling.

    Returns:
        CareerTrajectory with year-by-year projections and confidence bands.
    """
    aging_curve = BATTER_AGING_CURVE if player_type == "batter" else PITCHER_AGING_CURVE
    peak_age = 27 if player_type == "batter" else 26

    # Estimate the player's peak value from current performance + age position
    current_age_factor = _get_age_factor(current_age, aging_curve)
    if current_age_factor > 0:
        estimated_peak_value = min(100, current_value / current_age_factor)
    else:
        estimated_peak_value = current_value

    # Adjust peak estimate based on improvement trajectory
    # Improving players may not have reached their true peak yet
    improvement_adjustment = _improvement_adjustment(improvement_score, current_age, peak_age)
    estimated_peak_value = min(100, estimated_peak_value * (1 + improvement_adjustment))

    # Consistency affects confidence band width (inconsistent = wider bands)
    consistency_factor = max(0.5, consistency_score / 100)  # 0.5 to 1.0

    trajectory_points = []
    peak_proj_value = 0.0
    peak_proj_season = current_season + 1

    for year_offset in range(1, projection_years + 1):
        future_age = current_age + year_offset
        future_season = current_season + year_offset

        # Base projection from aging curve
        future_age_factor = _get_age_factor(future_age, aging_curve)
        projected_value = estimated_peak_value * future_age_factor

        # Apply improvement momentum (decays over time)
        if improvement_score > 0 and future_age <= peak_age + 2:
            momentum = improvement_score / 100 * max(0, 1 - year_offset * 0.25)
            projected_value *= (1 + momentum * 0.15)

        projected_value = max(0, min(100, projected_value))

        # Confidence bands
        band_idx = min(year_offset - 1, len(BASE_CONFIDENCE_WIDTHS) - 1)
        base_width = BASE_CONFIDENCE_WIDTHS[band_idx]

        # Wider bands for inconsistent players, narrower for consistent ones
        adjusted_width = base_width / consistency_factor

        # Wider bands for older players (more injury/retirement risk)
        if future_age > 32:
            adjusted_width *= 1.0 + (future_age - 32) * 0.1

        band = projected_value * adjusted_width
        upper = min(100, projected_value + band)
        lower = max(0, projected_value - band)

        point = TrajectoryPoint(
            season=future_season,
            projected_value=round(projected_value, 1),
            upper_bound=round(upper, 1),
            lower_bound=round(lower, 1),
            age=future_age,
        )
        trajectory_points.append(point)

        if projected_value > peak_proj_value:
            peak_proj_value = projected_value
            peak_proj_season = future_season

    # Total remaining value (sum of projected values, normalized)
    career_value_remaining = sum(p.projected_value for p in trajectory_points)

    # Grade the trajectory
    grade = _grade_trajectory(
        current_age, peak_age, improvement_score, trajectory_points, current_value
    )

    return CareerTrajectory(
        player_id=player_id,
        current_value=round(current_value, 1),
        trajectory=trajectory_points,
        peak_season=peak_proj_season,
        peak_value=round(peak_proj_value, 1),
        career_war_remaining=round(career_value_remaining, 1),
        trajectory_grade=grade,
    )


def _get_age_factor(age: int, aging_curve: dict[int, float]) -> float:
    """Get aging curve factor for a given age, with interpolation."""
    if age in aging_curve:
        return aging_curve[age]

    # Extrapolate for ages outside the curve
    ages = sorted(aging_curve.keys())
    if age < ages[0]:
        return aging_curve[ages[0]] * 0.9  # Young and unproven
    if age > ages[-1]:
        return max(0.05, aging_curve[ages[-1]] * 0.5)  # Very old

    # Linear interpolation
    for i in range(len(ages) - 1):
        if ages[i] <= age <= ages[i + 1]:
            t = (age - ages[i]) / (ages[i + 1] - ages[i])
            return aging_curve[ages[i]] * (1 - t) + aging_curve[ages[i + 1]] * t

    return 0.5  # Fallback


def _improvement_adjustment(
    improvement_score: float, current_age: int, peak_age: int
) -> float:
    """Calculate peak value adjustment based on improvement trajectory.

    Improving young players may exceed their current-performance-based
    peak estimate. Declining players may fall short.
    """
    if current_age > peak_age + 3:
        # Post-peak: improvement is unlikely to raise the ceiling
        return max(-0.15, improvement_score / 1000)

    if improvement_score > 0:
        # Pre-peak or near-peak with improvement: boost ceiling
        age_trust = max(0.3, 1.0 - (current_age - 22) * 0.1)
        return min(0.25, (improvement_score / 100) * 0.2 * age_trust)
    else:
        # Declining: reduce ceiling
        return max(-0.20, (improvement_score / 100) * 0.15)


def _grade_trajectory(
    current_age: int,
    peak_age: int,
    improvement_score: float,
    trajectory: list[TrajectoryPoint],
    current_value: float,
) -> str:
    """Assign a trajectory grade label."""
    if not trajectory:
        return "Unknown"

    first_future = trajectory[0].projected_value
    years_from_peak = current_age - peak_age

    if years_from_peak < -2 and improvement_score > 20:
        return "Rising"
    elif years_from_peak < -1:
        return "Rising"
    elif abs(years_from_peak) <= 1:
        if improvement_score > 10:
            return "Peak"
        elif improvement_score < -10:
            return "Declining"
        return "Peak"
    elif years_from_peak <= 4:
        if first_future >= current_value * 0.9:
            return "Plateau"
        return "Declining"
    else:
        return "Late Career"


def batch_project_trajectories(
    players: list[dict],
    current_season: int = 2025,
    projection_years: int = 6,
) -> list[CareerTrajectory]:
    """Project trajectories for a batch of players.

    Args:
        players: List of dicts with keys: player_id, age, current_value,
                 player_type, improvement_score, consistency_score, dynasty_value.
        current_season: Current year.
        projection_years: Years to project forward.

    Returns:
        List of CareerTrajectory objects.
    """
    results = []
    for p in players:
        try:
            trajectory = project_career_trajectory(
                player_id=p["player_id"],
                current_age=p.get("age", 28),
                current_value=p.get("current_value", 50),
                player_type=p.get("player_type", "batter"),
                improvement_score=p.get("improvement_score", 0),
                consistency_score=p.get("consistency_score", 50),
                dynasty_value=p.get("dynasty_value", 50),
                projection_years=projection_years,
                current_season=current_season,
            )
            results.append(trajectory)
        except Exception as e:
            logger.warning(f"Failed to project trajectory for player {p.get('player_id')}: {e}")
            continue

    logger.info(f"Projected trajectories for {len(results)} players")
    return results

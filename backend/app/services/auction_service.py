"""Auction valuation engine — converts projected stats to dollar values.

Uses the Standings Gain Points (SGP) method:
1. Project each player's stats (from Marcel)
2. Calculate how much each stat unit improves standings (SGP)
3. Sum SGP contributions across categories → raw value
4. Scale to league's auction budget → dollar value
5. Surplus = dollar value - expected cost
"""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Default 12-team mixed league SGP denominators
# (how many units of a stat it takes to gain one spot in standings)
# These are calibrated from historical league data
DEFAULT_SGP = {
    # Batting categories
    "hr": 8.5,
    "rbi": 25.0,
    "r": 25.0,
    "sb": 8.0,
    "avg": 0.004,
    "obp": 0.005,
    "slg": 0.007,
    "ops": 0.010,
    # Pitching categories
    "w": 3.0,
    "sv": 7.0,
    "so": 30.0,
    "era": -0.18,  # Negative because lower is better
    "whip": -0.015,
}

# Default stat categories for standard 5x5 roto
DEFAULT_BATTING_CATEGORIES = ["hr", "rbi", "r", "sb", "avg"]
DEFAULT_PITCHING_CATEGORIES = ["w", "sv", "so", "era", "whip"]

# Typical budget splits
DEFAULT_BUDGET = 260
HITTER_BUDGET_PCT = 0.65  # 65% of budget on hitters
PITCHER_BUDGET_PCT = 0.35

# Roster spots (standard 12-team)
DEFAULT_HITTER_ROSTER = 14  # C, 1B, 2B, SS, 3B, OF*3, UTIL, 5 bench
DEFAULT_PITCHER_ROSTER = 10  # SP*5, RP*3, 2 bench


def calculate_sgp_values(
    batter_projections: pd.DataFrame,
    pitcher_projections: pd.DataFrame,
    batting_categories: list[str] | None = None,
    pitching_categories: list[str] | None = None,
    sgp_denominators: dict[str, float] | None = None,
    auction_budget: float = DEFAULT_BUDGET,
    num_teams: int = 12,
    hitter_roster_spots: int = DEFAULT_HITTER_ROSTER,
    pitcher_roster_spots: int = DEFAULT_PITCHER_ROSTER,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Calculate auction dollar values for all players using SGP method.

    Args:
        batter_projections: Marcel projected batting stats (must include player_id).
        pitcher_projections: Marcel projected pitching stats (must include player_id).
        batting_categories: Stat categories for batters. Defaults to 5x5.
        pitching_categories: Stat categories for pitchers. Defaults to 5x5.
        sgp_denominators: Custom SGP values. Defaults to standard 12-team.
        auction_budget: Per-team auction budget.
        num_teams: Number of teams in the league.
        hitter_roster_spots: Rostered hitter spots per team.
        pitcher_roster_spots: Rostered pitcher spots per team.

    Returns:
        Tuple of (batter_values_df, pitcher_values_df) with auction_value column.
    """
    bat_cats = batting_categories or DEFAULT_BATTING_CATEGORIES
    pit_cats = pitching_categories or DEFAULT_PITCHING_CATEGORIES
    sgp = sgp_denominators or DEFAULT_SGP

    total_hitter_dollars = auction_budget * num_teams * HITTER_BUDGET_PCT
    total_pitcher_dollars = auction_budget * num_teams * PITCHER_BUDGET_PCT
    total_hitter_slots = hitter_roster_spots * num_teams
    total_pitcher_slots = pitcher_roster_spots * num_teams

    # Calculate batter SGP values
    batter_values = _calculate_category_sgp(batter_projections, bat_cats, sgp)
    batter_values = _scale_to_dollars(
        batter_values, total_hitter_dollars, total_hitter_slots
    )

    # Calculate pitcher SGP values
    pitcher_values = _calculate_category_sgp(pitcher_projections, pit_cats, sgp)
    pitcher_values = _scale_to_dollars(
        pitcher_values, total_pitcher_dollars, total_pitcher_slots
    )

    logger.info(
        f"Calculated auction values: {len(batter_values)} batters, {len(pitcher_values)} pitchers"
    )
    return batter_values, pitcher_values


def calculate_surplus_value(
    player_values: pd.DataFrame,
    expected_costs: dict[int, float] | None = None,
) -> pd.DataFrame:
    """Calculate surplus value (projected value minus expected cost).

    Args:
        player_values: DataFrame with player_id and auction_value columns.
        expected_costs: Dict mapping player_id -> expected auction cost.
                       If None, estimates from ADP.

    Returns:
        DataFrame with added surplus_value column.
    """
    df = player_values.copy()

    if expected_costs:
        df["expected_cost"] = df["player_id"].map(expected_costs).fillna(1.0)
    else:
        # Estimate cost from value ranking (top players cost more than their value)
        df = df.sort_values("auction_value", ascending=False).reset_index(drop=True)
        df["expected_cost"] = df["auction_value"] * _cost_multiplier(df.index, len(df))

    df["surplus_value"] = df["auction_value"] - df["expected_cost"]
    return df


def calculate_dynasty_value(
    player_values: pd.DataFrame,
    player_ages: dict[int, int],
    years_of_control: dict[int, int] | None = None,
    keeper_cost_inflation: float = 5.0,
) -> pd.DataFrame:
    """Calculate dynasty-adjusted values factoring in multi-year outlook.

    Args:
        player_values: DataFrame with player_id and auction_value.
        player_ages: Dict mapping player_id -> current age.
        years_of_control: Dict mapping player_id -> years of team control remaining.
        keeper_cost_inflation: Annual cost increase for keepers.

    Returns:
        DataFrame with dynasty_value (0-100) and keep_cut_horizon columns.
    """
    df = player_values.copy()

    dynasty_scores = []
    keep_cut_horizons = []

    for _, row in df.iterrows():
        pid = row["player_id"]
        age = player_ages.get(pid, 30)
        yoc = (years_of_control or {}).get(pid, max(0, 38 - age))  # Estimate if unknown
        annual_value = row.get("auction_value", 0)
        current_cost = row.get("expected_cost", 1)

        # Multi-year value with aging discount
        total_future_value = 0.0
        keep_cut = 0
        for year in range(yoc):
            future_age = age + year
            # Decline rate: 2% per year after peak, accelerating after 32
            if future_age <= 27:
                age_factor = 1.0 + 0.01 * (27 - future_age)  # Slight growth pre-peak
            elif future_age <= 32:
                age_factor = 1.0 - 0.02 * (future_age - 27)
            else:
                age_factor = max(0.3, 1.0 - 0.02 * 5 - 0.04 * (future_age - 32))

            projected_year_value = annual_value * age_factor
            keeper_cost = current_cost + (keeper_cost_inflation * year)

            # Discount future value by uncertainty (further out = less certain)
            uncertainty_discount = 0.9 ** year
            discounted_value = projected_year_value * uncertainty_discount

            total_future_value += max(0, discounted_value)

            # Track when cost exceeds value
            if keeper_cost < projected_year_value and keep_cut == year:
                keep_cut = year + 1

        dynasty_scores.append(total_future_value)
        keep_cut_horizons.append(keep_cut)

    df["dynasty_raw"] = dynasty_scores
    df["keep_cut_horizon"] = keep_cut_horizons

    # Normalize dynasty_raw to 0-100 scale
    max_val = df["dynasty_raw"].max()
    if max_val > 0:
        df["dynasty_value"] = (df["dynasty_raw"] / max_val * 100).round(1)
    else:
        df["dynasty_value"] = 0.0

    df = df.drop(columns=["dynasty_raw"])

    logger.info(f"Calculated dynasty values for {len(df)} players")
    return df


def _calculate_category_sgp(
    projections: pd.DataFrame,
    categories: list[str],
    sgp_denominators: dict[str, float],
) -> pd.DataFrame:
    """Calculate raw SGP value for each player across all categories."""
    df = projections.copy()
    df["sgp_total"] = 0.0

    for cat in categories:
        if cat not in df.columns or cat not in sgp_denominators:
            continue
        sgp_denom = sgp_denominators[cat]
        if sgp_denom == 0:
            continue

        # For negative SGP stats (ERA, WHIP), lower is better
        # The replacement level is roughly the value at the Nth ranked player
        col_values = df[cat].fillna(0)

        if sgp_denom < 0:
            # Lower is better: value = (replacement - player) / |sgp|
            replacement = col_values.quantile(0.75)
            df[f"sgp_{cat}"] = (replacement - col_values) / abs(sgp_denom)
        else:
            # Higher is better: value = (player - replacement) / sgp
            replacement = col_values.quantile(0.25)
            df[f"sgp_{cat}"] = (col_values - replacement) / sgp_denom

        df["sgp_total"] += df[f"sgp_{cat}"]

    return df


def _scale_to_dollars(
    sgp_df: pd.DataFrame,
    total_dollars: float,
    total_roster_slots: int,
) -> pd.DataFrame:
    """Scale SGP values to auction dollar amounts."""
    df = sgp_df.copy()

    # Only price the top N players (roster slots)
    df = df.sort_values("sgp_total", ascending=False).reset_index(drop=True)

    # Replacement level is the last rostered player
    if len(df) > total_roster_slots:
        replacement_sgp = df.iloc[total_roster_slots]["sgp_total"]
    else:
        replacement_sgp = 0

    # Value above replacement
    df["var"] = df["sgp_total"] - replacement_sgp
    df["var"] = df["var"].clip(lower=0)

    # Convert to dollars
    total_var = df["var"].sum()
    # Reserve $1 per roster slot as minimum bid
    distributable = total_dollars - total_roster_slots
    if total_var > 0:
        df["auction_value"] = ((df["var"] / total_var) * distributable + 1).round(1)
    else:
        df["auction_value"] = 1.0

    # Players below replacement get $1
    df.loc[df["var"] <= 0, "auction_value"] = 1.0

    return df


def _cost_multiplier(ranks: pd.Index, total: int) -> pd.Series:
    """Estimate cost multiplier by rank (top players are overpaid relative to value)."""
    pct = ranks / max(total, 1)
    # Top players get bid up ~20% over value, mid-tier at value, low-tier cheaper
    return 1.2 - 0.4 * pct

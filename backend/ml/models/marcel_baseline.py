"""Marcel projection system — the baseline that every ML model must beat.

Marcel (named after Marcel the Monkey) is Tom Tango's intentionally simple
projection system:
1. Weighted 3-year average (5/4/3 weighting, most recent heaviest)
2. Regression toward league mean proportional to playing time
3. Age adjustment (+/- 0.006 per year from peak)

Reference: https://www.tangotiger.net/marcel/
"""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Weights for 3-year average (most recent = highest)
YEAR_WEIGHTS = {0: 5, 1: 4, 2: 3}  # 0 = most recent season

# Regression constants (PA/IP of league-average performance to blend in)
BATTER_REGRESSION_PA = 1200
PITCHER_REGRESSION_OUTS = 134  # ~44.7 IP

# Peak ages
BATTER_PEAK_AGE = 27
PITCHER_PEAK_AGE = 26

# Age adjustment per year from peak
AGE_ADJUSTMENT = 0.006

# Stats to project for batters
BATTER_RATE_STATS = [
    "avg", "obp", "slg", "iso", "woba", "babip", "k_pct", "bb_pct",
    "barrel_pct", "hard_hit_pct",
]
BATTER_COUNTING_STATS = ["hr", "rbi", "r", "sb"]

# Stats to project for pitchers
PITCHER_RATE_STATS = [
    "era", "whip", "fip", "k_pct", "bb_pct", "k_bb_pct", "babip",
    "barrel_pct_against", "hard_hit_pct_against", "hr_fb_pct",
]

# League averages (approximate, updated for modern game)
LEAGUE_AVG_BATTING = {
    "avg": 0.248, "obp": 0.315, "slg": 0.399, "iso": 0.151,
    "woba": 0.312, "babip": 0.296, "k_pct": 0.225, "bb_pct": 0.083,
    "barrel_pct": 0.068, "hard_hit_pct": 0.370,
}
LEAGUE_AVG_PITCHING = {
    "era": 4.15, "whip": 1.28, "fip": 4.10, "k_pct": 0.225,
    "bb_pct": 0.083, "k_bb_pct": 0.142, "babip": 0.296,
    "barrel_pct_against": 0.068, "hard_hit_pct_against": 0.370,
    "hr_fb_pct": 0.132,
}


def project_batter(seasons: list[dict], age: int) -> dict:
    """Generate Marcel projections for a batter.

    Args:
        seasons: List of season dicts, ordered most recent first. Each dict should
                 contain batting stat columns plus 'pa' for plate appearances.
        age: Player's age for the projected season.

    Returns:
        Dict of projected stats.
    """
    if not seasons:
        return {}

    projections = {}

    # Step 1: Weighted 3-year average for rate stats
    for stat in BATTER_RATE_STATS:
        weighted_sum = 0.0
        weight_total = 0.0

        for i, season in enumerate(seasons[:3]):
            if i not in YEAR_WEIGHTS:
                break
            val = season.get(stat)
            pa = season.get("pa", 0) or 0
            if val is not None and pa > 0:
                weight = YEAR_WEIGHTS[i] * pa
                weighted_sum += val * weight
                weight_total += weight

        if weight_total > 0:
            weighted_avg = weighted_sum / weight_total

            # Step 2: Regress toward league mean
            total_pa = sum((s.get("pa", 0) or 0) for s in seasons[:3])
            league_avg = LEAGUE_AVG_BATTING.get(stat, weighted_avg)
            reliability = total_pa / (total_pa + BATTER_REGRESSION_PA)
            regressed = (reliability * weighted_avg) + ((1 - reliability) * league_avg)

            # Step 3: Age adjustment
            years_from_peak = age - BATTER_PEAK_AGE
            age_adj = 1.0 - (AGE_ADJUSTMENT * years_from_peak)
            projected = regressed * age_adj

            projections[stat] = round(projected, 4)

    # Project counting stats (scale by projected PA)
    projected_pa = _project_playing_time_batter(seasons, age)
    projections["pa"] = projected_pa

    for stat in BATTER_COUNTING_STATS:
        rate = _counting_to_rate(seasons, stat, "pa")
        if rate is not None and not np.isnan(rate) and projected_pa > 0:
            projections[stat] = round(rate * projected_pa)

    return projections


def project_pitcher(seasons: list[dict], age: int) -> dict:
    """Generate Marcel projections for a pitcher.

    Args:
        seasons: List of season dicts, ordered most recent first. Each dict should
                 contain pitching stat columns plus 'ip' for innings pitched.
        age: Player's age for the projected season.

    Returns:
        Dict of projected stats.
    """
    if not seasons:
        return {}

    projections = {}

    for stat in PITCHER_RATE_STATS:
        weighted_sum = 0.0
        weight_total = 0.0

        for i, season in enumerate(seasons[:3]):
            if i not in YEAR_WEIGHTS:
                break
            val = season.get(stat)
            ip = season.get("ip", 0) or 0
            outs = ip * 3
            if val is not None and outs > 0:
                weight = YEAR_WEIGHTS[i] * outs
                weighted_sum += val * weight
                weight_total += weight

        if weight_total > 0:
            weighted_avg = weighted_sum / weight_total

            total_outs = sum(((s.get("ip", 0) or 0) * 3) for s in seasons[:3])
            league_avg = LEAGUE_AVG_PITCHING.get(stat, weighted_avg)
            reliability = total_outs / (total_outs + PITCHER_REGRESSION_OUTS)
            regressed = (reliability * weighted_avg) + ((1 - reliability) * league_avg)

            years_from_peak = age - PITCHER_PEAK_AGE
            # For ERA/WHIP/FIP, aging makes them worse (higher), so invert the adjustment
            if stat in ("era", "whip", "fip", "babip", "hr_fb_pct", "barrel_pct_against",
                        "hard_hit_pct_against", "bb_pct"):
                age_adj = 1.0 + (AGE_ADJUSTMENT * years_from_peak)
            else:
                age_adj = 1.0 - (AGE_ADJUSTMENT * years_from_peak)

            projected = regressed * age_adj
            projections[stat] = round(projected, 4)

    projected_ip = _project_playing_time_pitcher(seasons, age)
    projections["ip"] = projected_ip

    # Project strikeouts and wins
    k_per_ip = _counting_to_rate(seasons, "so", "ip")
    if k_per_ip is not None and not np.isnan(k_per_ip) and not np.isnan(projected_ip):
        projections["so"] = round(k_per_ip * projected_ip)

    w_per_ip = _counting_to_rate(seasons, "w", "ip")
    if w_per_ip is not None and not np.isnan(w_per_ip) and not np.isnan(projected_ip):
        projections["w"] = round(w_per_ip * projected_ip)

    sv_per_g = _counting_to_rate(seasons, "sv", "g")
    if sv_per_g is not None and not np.isnan(sv_per_g):
        projected_g = _project_games_pitcher(seasons)
        if projected_g and not np.isnan(projected_g):
            projections["sv"] = round(sv_per_g * projected_g)

    return projections


def project_all_batters(batting_df: pd.DataFrame, player_ages: dict[int, int]) -> pd.DataFrame:
    """Generate Marcel projections for all batters.

    Args:
        batting_df: DataFrame with batting seasons (must include player_id, season columns).
        player_ages: Dict mapping player_id -> age for projected season.

    Returns:
        DataFrame with one row per player, containing Marcel projected stats.
    """
    results = []
    for player_id, group in batting_df.groupby("player_id"):
        age = player_ages.get(player_id)
        if age is None:
            continue
        # Sort most recent first
        seasons = group.sort_values("season", ascending=False).to_dict("records")
        proj = project_batter(seasons, age)
        if proj:
            proj["player_id"] = player_id
            results.append(proj)

    logger.info(f"Generated Marcel projections for {len(results)} batters")
    return pd.DataFrame(results)


def project_all_pitchers(pitching_df: pd.DataFrame, player_ages: dict[int, int]) -> pd.DataFrame:
    """Generate Marcel projections for all pitchers.

    Args:
        pitching_df: DataFrame with pitching seasons (must include player_id, season columns).
        player_ages: Dict mapping player_id -> age for projected season.

    Returns:
        DataFrame with one row per player, containing Marcel projected stats.
    """
    results = []
    for player_id, group in pitching_df.groupby("player_id"):
        age = player_ages.get(player_id)
        if age is None:
            continue
        seasons = group.sort_values("season", ascending=False).to_dict("records")
        proj = project_pitcher(seasons, age)
        if proj:
            proj["player_id"] = player_id
            results.append(proj)

    logger.info(f"Generated Marcel projections for {len(results)} pitchers")
    return pd.DataFrame(results)


def _project_playing_time_batter(seasons: list[dict], age: int) -> int:
    """Project PA for next season using weighted average with aging adjustment."""
    if not seasons:
        return 0
    weighted_pa = 0.0
    weight_total = 0.0
    for i, s in enumerate(seasons[:3]):
        if i not in YEAR_WEIGHTS:
            break
        pa = s.get("pa", 0) or 0
        weighted_pa += pa * YEAR_WEIGHTS[i]
        weight_total += YEAR_WEIGHTS[i]
    if weight_total == 0:
        return 0
    base_pa = weighted_pa / weight_total
    # Slight decline in playing time with age
    years_from_peak = age - BATTER_PEAK_AGE
    if years_from_peak > 0:
        base_pa *= max(0.5, 1.0 - 0.02 * years_from_peak)
    return round(base_pa)


def _project_playing_time_pitcher(seasons: list[dict], age: int) -> float:
    """Project IP for next season."""
    if not seasons:
        return 0.0
    weighted_ip = 0.0
    weight_total = 0.0
    for i, s in enumerate(seasons[:3]):
        if i not in YEAR_WEIGHTS:
            break
        ip = s.get("ip", 0) or 0
        weighted_ip += ip * YEAR_WEIGHTS[i]
        weight_total += YEAR_WEIGHTS[i]
    if weight_total == 0:
        return 0.0
    base_ip = weighted_ip / weight_total
    years_from_peak = age - PITCHER_PEAK_AGE
    if years_from_peak > 0:
        base_ip *= max(0.5, 1.0 - 0.02 * years_from_peak)
    return round(base_ip, 1)


def _project_games_pitcher(seasons: list[dict]) -> int:
    """Project games for next season (for saves projection)."""
    if not seasons:
        return 0
    weighted_g = 0.0
    weight_total = 0.0
    for i, s in enumerate(seasons[:3]):
        if i not in YEAR_WEIGHTS:
            break
        g = s.get("g", 0) or 0
        weighted_g += g * YEAR_WEIGHTS[i]
        weight_total += YEAR_WEIGHTS[i]
    return round(weighted_g / weight_total) if weight_total else 0


def _counting_to_rate(seasons: list[dict], counting_stat: str, denom_stat: str) -> float | None:
    """Convert a counting stat to a per-unit rate across weighted seasons."""
    weighted_rate = 0.0
    weight_total = 0.0
    for i, s in enumerate(seasons[:3]):
        if i not in YEAR_WEIGHTS:
            break
        count = _safe_numeric(s.get(counting_stat, 0))
        denom = _safe_numeric(s.get(denom_stat, 0))
        if denom > 0 and not np.isnan(count):
            rate = count / denom
            weight = YEAR_WEIGHTS[i] * denom
            weighted_rate += rate * weight
            weight_total += weight
    return weighted_rate / weight_total if weight_total > 0 else None


def _safe_numeric(val) -> float:
    """Convert a value to float, treating None/NaN as 0."""
    if val is None:
        return 0.0
    try:
        f = float(val)
        return 0.0 if np.isnan(f) else f
    except (ValueError, TypeError):
        return 0.0

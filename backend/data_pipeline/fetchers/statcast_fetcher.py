"""Fetches pitch-level Statcast data from Baseball Savant via pybaseball.

Statcast data is fetched in 7-day chunks to stay under Baseball Savant's
~30,000 row per request limit, then aggregated to per-player-per-season summaries.
"""

import logging
from datetime import date, timedelta

import pandas as pd
import pybaseball

logger = logging.getLogger(__name__)

# Statcast only available from 2015, but quality data starts ~2019
CHUNK_DAYS = 7


def fetch_statcast_range(start_dt: date, end_dt: date) -> pd.DataFrame:
    """Fetch raw Statcast data in weekly chunks for a date range.

    Args:
        start_dt: Start date (inclusive).
        end_dt: End date (inclusive).

    Returns:
        Combined DataFrame of all pitch-level Statcast data.
    """
    chunks = []
    current = start_dt
    total_chunks = ((end_dt - start_dt).days // CHUNK_DAYS) + 1
    chunk_num = 0

    while current <= end_dt:
        chunk_end = min(current + timedelta(days=CHUNK_DAYS - 1), end_dt)
        chunk_num += 1
        logger.info(
            f"Fetching Statcast chunk {chunk_num}/{total_chunks}: "
            f"{current.isoformat()} to {chunk_end.isoformat()}"
        )
        try:
            chunk = pybaseball.statcast(
                start_dt=current.isoformat(), end_dt=chunk_end.isoformat()
            )
            if chunk is not None and len(chunk) > 0:
                chunks.append(chunk)
        except Exception:
            logger.exception(f"Error fetching Statcast {current} to {chunk_end}")
        current = chunk_end + timedelta(days=1)

    if not chunks:
        return pd.DataFrame()

    combined = pd.concat(chunks, ignore_index=True)
    logger.info(f"Fetched {len(combined)} total Statcast rows")
    return combined


def fetch_statcast_season(season: int) -> pd.DataFrame:
    """Fetch full-season Statcast data.

    Args:
        season: The MLB season year.

    Returns:
        Raw pitch-level DataFrame for the entire season.
    """
    start = date(season, 3, 20)  # Spring training / opening day window
    end = date(season, 11, 5)  # Post-season end window
    return fetch_statcast_range(start, end)


def aggregate_batter_statcast(raw: pd.DataFrame, season: int) -> pd.DataFrame:
    """Aggregate pitch-level Statcast to per-batter-per-season summaries.

    Args:
        raw: Raw Statcast pitch-level DataFrame.
        season: Season year for labeling.

    Returns:
        DataFrame with one row per batter, aggregated Statcast metrics.
    """
    # Filter to batted ball events only
    batted = raw[raw["type"] == "X"].copy()
    if batted.empty:
        return pd.DataFrame()

    agg = batted.groupby("batter").agg(
        avg_exit_velocity=("launch_speed", "mean"),
        max_exit_velocity=("launch_speed", "max"),
        avg_launch_angle=("launch_angle", "mean"),
        total_batted_balls=("launch_speed", "count"),
    ).reset_index()

    # Barrel calculation: EV >= 98 mph and launch angle in sweet spot
    batted["is_barrel"] = (batted["launch_speed"] >= 98) & (
        batted["launch_angle"].between(26, 30)
        | ((batted["launch_speed"] >= 100) & batted["launch_angle"].between(24, 33))
        | ((batted["launch_speed"] >= 102) & batted["launch_angle"].between(22, 35))
        | ((batted["launch_speed"] >= 104) & batted["launch_angle"].between(20, 37))
        | ((batted["launch_speed"] >= 106) & batted["launch_angle"].between(18, 39))
    )
    barrel_rates = batted.groupby("batter").agg(
        barrels=("is_barrel", "sum"),
    ).reset_index()

    # Hard hit: EV >= 95 mph
    batted["is_hard_hit"] = batted["launch_speed"] >= 95
    hard_hit_rates = batted.groupby("batter").agg(
        hard_hits=("is_hard_hit", "sum"),
    ).reset_index()

    # Sweet spot: launch angle 8-32 degrees
    batted["is_sweet_spot"] = batted["launch_angle"].between(8, 32)
    sweet_spot_rates = batted.groupby("batter").agg(
        sweet_spots=("is_sweet_spot", "sum"),
    ).reset_index()

    # Merge all
    agg = agg.merge(barrel_rates, on="batter", how="left")
    agg = agg.merge(hard_hit_rates, on="batter", how="left")
    agg = agg.merge(sweet_spot_rates, on="batter", how="left")

    # Calculate percentages
    agg["barrel_pct"] = agg["barrels"] / agg["total_batted_balls"]
    agg["hard_hit_pct"] = agg["hard_hits"] / agg["total_batted_balls"]
    agg["sweet_spot_pct"] = agg["sweet_spots"] / agg["total_batted_balls"]

    # Expected stats from Statcast (if available in the data)
    for col in ["estimated_ba_using_speedangle", "estimated_slg_using_speedangle",
                "estimated_woba_using_speedangle"]:
        if col in batted.columns:
            xstat = batted.groupby("batter")[col].mean().reset_index()
            col_map = {
                "estimated_ba_using_speedangle": "xba",
                "estimated_slg_using_speedangle": "xslg",
                "estimated_woba_using_speedangle": "xwoba",
            }
            xstat = xstat.rename(columns={col: col_map[col]})
            agg = agg.merge(xstat, on="batter", how="left")

    agg["season"] = season
    agg = agg.rename(columns={"batter": "mlbam_id"})

    return agg


def aggregate_pitcher_statcast(raw: pd.DataFrame, season: int) -> pd.DataFrame:
    """Aggregate pitch-level Statcast to per-pitcher-per-season summaries.

    Args:
        raw: Raw Statcast pitch-level DataFrame.
        season: Season year for labeling.

    Returns:
        DataFrame with one row per pitcher, aggregated Statcast metrics.
    """
    batted = raw[raw["type"] == "X"].copy()
    if batted.empty:
        return pd.DataFrame()

    agg = batted.groupby("pitcher").agg(
        avg_exit_velocity=("launch_speed", "mean"),
        max_exit_velocity=("launch_speed", "max"),
        avg_launch_angle=("launch_angle", "mean"),
        total_batted_balls=("launch_speed", "count"),
    ).reset_index()

    # Barrel rate against
    batted["is_barrel"] = (batted["launch_speed"] >= 98) & (
        batted["launch_angle"].between(26, 30)
    )
    barrel_rates = batted.groupby("pitcher").agg(barrels=("is_barrel", "sum")).reset_index()

    # Hard hit rate against
    batted["is_hard_hit"] = batted["launch_speed"] >= 95
    hard_hit_rates = batted.groupby("pitcher").agg(hard_hits=("is_hard_hit", "sum")).reset_index()

    agg = agg.merge(barrel_rates, on="pitcher", how="left")
    agg = agg.merge(hard_hit_rates, on="pitcher", how="left")
    agg["barrel_pct"] = agg["barrels"] / agg["total_batted_balls"]
    agg["hard_hit_pct"] = agg["hard_hits"] / agg["total_batted_balls"]

    # Spin rate (from all pitches, not just batted balls)
    spin = raw.groupby("pitcher").agg(
        avg_spin_rate=("release_spin_rate", "mean"),
        avg_fastball_velo=("release_speed", "mean"),
    ).reset_index()
    agg = agg.merge(spin, on="pitcher", how="left")

    # Expected ERA if available
    if "estimated_woba_using_speedangle" in batted.columns:
        xwoba = batted.groupby("pitcher")["estimated_woba_using_speedangle"].mean().reset_index()
        xwoba = xwoba.rename(columns={"estimated_woba_using_speedangle": "xwoba"})
        agg = agg.merge(xwoba, on="pitcher", how="left")

    agg["season"] = season
    agg["player_type"] = "pitcher"
    agg = agg.rename(columns={"pitcher": "mlbam_id"})

    return agg

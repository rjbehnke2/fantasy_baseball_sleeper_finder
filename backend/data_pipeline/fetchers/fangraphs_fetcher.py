"""Fetches season-level batting and pitching stats from FanGraphs via pybaseball."""

import logging

import pandas as pd
import pybaseball

logger = logging.getLogger(__name__)


def enable_cache() -> None:
    pybaseball.cache.enable()


def fetch_batting_stats(start_season: int, end_season: int, qual: int = 50) -> pd.DataFrame:
    """Fetch FanGraphs batting stats for a range of seasons.

    Uses fg_batting_data (FanGraphs API) with fallback to batting_stats (legacy scraper).

    Args:
        start_season: First season to fetch.
        end_season: Last season to fetch (inclusive).
        qual: Minimum PA to qualify. Default 50 to capture part-time players.

    Returns:
        DataFrame with one row per player per season.
    """
    logger.info(f"Fetching batting stats {start_season}-{end_season} (qual={qual})")
    try:
        df = pybaseball.fg_batting_data(
            start_season, end_season, qual=qual, split_seasons=True
        )
        logger.info(f"Fetched {len(df)} batting season rows via FanGraphs API")
    except Exception as e:
        logger.warning(f"FanGraphs API failed ({e}), trying legacy scraper...")
        df = pybaseball.batting_stats(start_season, end_season, qual=qual, ind=1)
        logger.info(f"Fetched {len(df)} batting season rows via legacy scraper")
    return df


def fetch_pitching_stats(start_season: int, end_season: int, qual: int = 20) -> pd.DataFrame:
    """Fetch FanGraphs pitching stats for a range of seasons.

    Uses fg_pitching_data (FanGraphs API) with fallback to pitching_stats (legacy scraper).

    Args:
        start_season: First season to fetch.
        end_season: Last season to fetch (inclusive).
        qual: Minimum IP to qualify. Default 20 to capture relievers.

    Returns:
        DataFrame with one row per player per season.
    """
    logger.info(f"Fetching pitching stats {start_season}-{end_season} (qual={qual})")
    try:
        df = pybaseball.fg_pitching_data(
            start_season, end_season, qual=qual, split_seasons=True
        )
        logger.info(f"Fetched {len(df)} pitching season rows via FanGraphs API")
    except Exception as e:
        logger.warning(f"FanGraphs API failed ({e}), trying legacy scraper...")
        df = pybaseball.pitching_stats(start_season, end_season, qual=qual, ind=1)
        logger.info(f"Fetched {len(df)} pitching season rows via legacy scraper")
    return df

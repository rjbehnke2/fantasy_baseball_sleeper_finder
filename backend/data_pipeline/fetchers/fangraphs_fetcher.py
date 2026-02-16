"""Fetches season-level batting and pitching stats from FanGraphs.

Uses the FanGraphs JSON API (/api/leaders) directly, bypassing pybaseball's
broken legacy HTML scraper. Falls back to pybaseball functions if the direct
API also fails.
"""

import logging
from typing import Any

import pandas as pd
import requests

logger = logging.getLogger(__name__)

FANGRAPHS_API_URL = "https://www.fangraphs.com/api/leaders"

# FanGraphs API stat type codes for comprehensive stat coverage
# type=c means custom columns; the comma-separated numbers are column IDs
# This requests the same comprehensive set pybaseball would request
_BATTING_STAT_TYPES = (
    "c,-1,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,"
    "34,35,36,37,38,39,40,41,42,43,44,45,50,51,52,53,54,55,56,57,58,59,60,"
    "61,62,79,80,81,174,175,199,200,201,202,203,204,205,206,207,208,209,210,"
    "211,212"
)

_PITCHING_STAT_TYPES = (
    "c,-1,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,"
    "34,35,36,37,38,39,40,41,42,43,44,45,50,51,52,53,54,55,56,57,58,59,60,"
    "61,62,117,118,119,120,121,217,218,219,220"
)


def enable_cache() -> None:
    """Enable pybaseball cache (used for Chadwick register)."""
    import pybaseball
    pybaseball.cache.enable()


def fetch_batting_stats(start_season: int, end_season: int, qual: int = 50) -> pd.DataFrame:
    """Fetch FanGraphs batting stats for a range of seasons.

    Tries the direct FanGraphs JSON API first, then pybaseball as fallback.

    Returns:
        DataFrame with one row per player per season.
    """
    logger.info(f"Fetching batting stats {start_season}-{end_season} (qual={qual})")

    # Try direct API first
    try:
        df = _fetch_from_api("bat", start_season, end_season, qual)
        logger.info(f"Fetched {len(df)} batting season rows via FanGraphs API")
        return df
    except Exception as e:
        logger.warning(f"Direct FanGraphs API failed ({e}), trying pybaseball...")

    # Fallback to pybaseball
    import pybaseball
    try:
        df = pybaseball.fg_batting_data(start_season, end_season, qual=qual, split_seasons=True)
        logger.info(f"Fetched {len(df)} batting season rows via pybaseball fg_batting_data")
        return df
    except Exception as e2:
        logger.warning(f"fg_batting_data failed ({e2}), trying legacy batting_stats...")

    df = pybaseball.batting_stats(start_season, end_season, qual=qual, ind=1)
    logger.info(f"Fetched {len(df)} batting season rows via legacy scraper")
    return df


def fetch_pitching_stats(start_season: int, end_season: int, qual: int = 20) -> pd.DataFrame:
    """Fetch FanGraphs pitching stats for a range of seasons.

    Tries the direct FanGraphs JSON API first, then pybaseball as fallback.

    Returns:
        DataFrame with one row per player per season.
    """
    logger.info(f"Fetching pitching stats {start_season}-{end_season} (qual={qual})")

    # Try direct API first
    try:
        df = _fetch_from_api("pit", start_season, end_season, qual)
        logger.info(f"Fetched {len(df)} pitching season rows via FanGraphs API")
        return df
    except Exception as e:
        logger.warning(f"Direct FanGraphs API failed ({e}), trying pybaseball...")

    import pybaseball
    try:
        df = pybaseball.fg_pitching_data(start_season, end_season, qual=qual, split_seasons=True)
        logger.info(f"Fetched {len(df)} pitching season rows via pybaseball fg_pitching_data")
        return df
    except Exception as e2:
        logger.warning(f"fg_pitching_data failed ({e2}), trying legacy pitching_stats...")

    df = pybaseball.pitching_stats(start_season, end_season, qual=qual, ind=1)
    logger.info(f"Fetched {len(df)} pitching season rows via legacy scraper")
    return df


def _fetch_from_api(
    stats: str,
    start_season: int,
    end_season: int,
    qual: int,
) -> pd.DataFrame:
    """Fetch data directly from the FanGraphs JSON API.

    Args:
        stats: 'bat' for batting, 'pit' for pitching.
        start_season: First season.
        end_season: Last season.
        qual: Minimum PA (batting) or IP (pitching).

    Returns:
        DataFrame with FanGraphs column names.
    """
    stat_types = _BATTING_STAT_TYPES if stats == "bat" else _PITCHING_STAT_TYPES

    params: dict[str, Any] = {
        "pos": "all",
        "stats": stats,
        "lg": "all",
        "qual": qual,
        "type": stat_types,
        "season": end_season,
        "month": 0,
        "season1": start_season,
        "ind": 1,  # Individual seasons
        "team": "",
        "rost": 0,
        "age": "",
        "filter": "",
        "players": "",
        "startdate": "",
        "enddate": "",
        "page": "1_1000000",
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; fantasy-baseball-sleeper-finder)",
        "Accept": "application/json",
    }

    resp = requests.get(FANGRAPHS_API_URL, params=params, headers=headers, timeout=60)
    resp.raise_for_status()

    data = resp.json()

    # The API may return {"data": [...]} or just a list
    if isinstance(data, dict) and "data" in data:
        rows = data["data"]
    elif isinstance(data, list):
        rows = data
    else:
        raise ValueError(f"Unexpected API response format: {type(data)}")

    if not rows:
        raise ValueError("FanGraphs API returned no data")

    df = pd.DataFrame(rows)

    # Normalize column names to match what pybaseball returns
    df = _normalize_api_columns(df)

    logger.info(f"API returned {len(df)} rows with {len(df.columns)} columns")
    return df


def _normalize_api_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize FanGraphs API JSON column names to match pybaseball conventions.

    The API returns camelCase or varying names; pybaseball uses Title Case.
    We map common variations to the names our cleaning module expects.
    """
    # The FanGraphs API column names vary but commonly use these patterns.
    # Our cleaning module uses {k: v for k, v in MAP.items() if k in df.columns}
    # so we just need to match the keys in BATTING_COLUMN_MAP / PITCHING_COLUMN_MAP.
    rename_map = {
        # Common API -> pybaseball name mappings
        "playerid": "IDfg",
        "PlayerName": "Name",
        "Name": "Name",
        "TeamName": "Team",
        "Team": "Team",
        "Season": "Season",
        # Batting
        "PA": "PA",
        "AB": "AB",
        "H": "H",
        "HR": "HR",
        "RBI": "RBI",
        "R": "R",
        "SB": "SB",
        "CS": "CS",
        "AVG": "AVG",
        "OBP": "OBP",
        "SLG": "SLG",
        "OPS": "OPS",
        "ISO": "ISO",
        "BABIP": "BABIP",
        "wOBA": "wOBA",
        "xwOBA": "xwOBA",
        "wRC+": "wRC+",
        "WAR": "WAR",
        "K%": "K%",
        "BB%": "BB%",
        "Barrel%": "Barrel%",
        "HardHit%": "HardHit%",
        "EV": "EV",
        "LA": "LA",
        "Spd": "Spd",
        "GB%": "GB%",
        "FB%": "FB%",
        "LD%": "LD%",
        "xBA": "xBA",
        "xSLG": "xSLG",
        # Pitching
        "W": "W",
        "L": "L",
        "SV": "SV",
        "HLD": "HLD",
        "IP": "IP",
        "GS": "GS",
        "G": "G",
        "SO": "SO",
        "BB": "BB",
        "ERA": "ERA",
        "WHIP": "WHIP",
        "FIP": "FIP",
        "xFIP": "xFIP",
        "SIERA": "SIERA",
        "K-BB%": "K-BB%",
        "SwStr%": "SwStr%",
        "CSW%": "CSW%",
        "HR/FB": "HR/FB",
        "LOB%": "LOB%",
        "Stuff+": "Stuff+",
        "xERA": "xERA",
    }

    # Only rename columns that exist in the dataframe
    actual_renames = {k: v for k, v in rename_map.items() if k in df.columns and k != v}
    if actual_renames:
        df = df.rename(columns=actual_renames)

    return df

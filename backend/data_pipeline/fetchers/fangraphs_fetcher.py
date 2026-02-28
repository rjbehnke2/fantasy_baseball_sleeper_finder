"""Fetches season-level batting and pitching stats from FanGraphs.

Tries multiple FanGraphs API endpoints (they change periodically), then
falls back to pybaseball as a last resort. The cleaning module downstream
handles column name normalization, so we just need to deliver a DataFrame
with recognizable FanGraphs column names.
"""

import logging
from typing import Any

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# Known FanGraphs API endpoints (they've changed over the years)
_API_URLS = [
    "https://www.fangraphs.com/api/leaders",
    "https://www.fangraphs.com/api/leaders/major-league/data",
]

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": "https://www.fangraphs.com/leaders/major-league",
}


def enable_cache() -> None:
    """Enable pybaseball cache (used for Chadwick register)."""
    import pybaseball
    pybaseball.cache.enable()


def fetch_batting_stats(start_season: int, end_season: int, qual: int = 50) -> pd.DataFrame:
    """Fetch FanGraphs batting stats for a range of seasons.

    Returns:
        DataFrame with one row per player per season.
    """
    logger.info(f"Fetching batting stats {start_season}-{end_season} (qual={qual})")

    # Try direct API with multiple URL patterns
    for url in _API_URLS:
        try:
            df = _fetch_from_api(url, "bat", start_season, end_season, qual)
            logger.info(f"Fetched {len(df)} batting rows via {url}")
            return df
        except Exception as e:
            logger.warning(f"API {url} failed for batting: {e}")

    # Fallback to pybaseball
    import pybaseball
    for fn_name, fn, kwargs in [
        ("fg_batting_data", pybaseball.fg_batting_data,
         {"qual": qual, "split_seasons": True}),
        ("batting_stats", pybaseball.batting_stats,
         {"qual": qual, "ind": 1}),
    ]:
        try:
            df = fn(start_season, end_season, **kwargs)
            logger.info(f"Fetched {len(df)} batting rows via pybaseball.{fn_name}")
            return df
        except Exception as e:
            logger.warning(f"pybaseball.{fn_name} failed: {e}")

    raise RuntimeError(
        "All FanGraphs data sources failed. FanGraphs may be down or blocking requests. "
        "Try again later or check https://www.fangraphs.com/leaders/major-league manually."
    )


def fetch_pitching_stats(start_season: int, end_season: int, qual: int = 20) -> pd.DataFrame:
    """Fetch FanGraphs pitching stats for a range of seasons.

    Returns:
        DataFrame with one row per player per season.
    """
    logger.info(f"Fetching pitching stats {start_season}-{end_season} (qual={qual})")

    for url in _API_URLS:
        try:
            df = _fetch_from_api(url, "pit", start_season, end_season, qual)
            logger.info(f"Fetched {len(df)} pitching rows via {url}")
            return df
        except Exception as e:
            logger.warning(f"API {url} failed for pitching: {e}")

    import pybaseball
    for fn_name, fn, kwargs in [
        ("fg_pitching_data", pybaseball.fg_pitching_data,
         {"qual": qual, "split_seasons": True}),
        ("pitching_stats", pybaseball.pitching_stats,
         {"qual": qual, "ind": 1}),
    ]:
        try:
            df = fn(start_season, end_season, **kwargs)
            logger.info(f"Fetched {len(df)} pitching rows via pybaseball.{fn_name}")
            return df
        except Exception as e:
            logger.warning(f"pybaseball.{fn_name} failed: {e}")

    raise RuntimeError(
        "All FanGraphs data sources failed. FanGraphs may be down or blocking requests. "
        "Try again later or check https://www.fangraphs.com/leaders/major-league manually."
    )


def _fetch_from_api(
    base_url: str,
    stats: str,
    start_season: int,
    end_season: int,
    qual: int,
) -> pd.DataFrame:
    """Fetch data directly from a FanGraphs JSON API endpoint.

    Args:
        base_url: The API endpoint URL.
        stats: 'bat' for batting, 'pit' for pitching.
        start_season: First season.
        end_season: Last season.
        qual: Minimum PA (batting) or IP (pitching).

    Returns:
        DataFrame with FanGraphs column names.
    """
    # Use type=8 (dashboard) which is a simple, well-supported stat type
    # that includes the core stats we need
    params: dict[str, Any] = {
        "pos": "all",
        "stats": stats,
        "lg": "all",
        "qual": qual,
        "type": 8,
        "season": end_season,
        "month": 0,
        "season1": start_season,
        "ind": 1,
        "team": "",
        "rost": 0,
        "age": "",
        "filter": "",
        "players": "",
        "startdate": "",
        "enddate": "",
        "page": "1_1000000",
    }

    resp = requests.get(base_url, params=params, headers=_HEADERS, timeout=60)
    resp.raise_for_status()

    # Check that response is actually JSON
    content_type = resp.headers.get("Content-Type", "")
    if "json" not in content_type and "javascript" not in content_type:
        # Log first 200 chars of response for debugging
        preview = resp.text[:200].replace("\n", " ")
        raise ValueError(
            f"Expected JSON but got Content-Type: {content_type}. "
            f"Response preview: {preview}"
        )

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

    # Normalize column names to match what our cleaning module expects
    df = _normalize_api_columns(df)

    logger.info(f"API returned {len(df)} rows with columns: {list(df.columns[:15])}...")
    return df


def _normalize_api_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize FanGraphs API JSON column names to match pybaseball conventions.

    The FanGraphs API returns keys that mostly match our BATTING_COLUMN_MAP /
    PITCHING_COLUMN_MAP already. The main difference is the player ID field.
    """
    rename_map = {
        "playerid": "IDfg",
        "PlayerName": "Name",
        "TeamName": "Team",
        "xMLBAMID": "xMLBAMID",
    }

    actual_renames = {k: v for k, v in rename_map.items() if k in df.columns}
    if actual_renames:
        df = df.rename(columns=actual_renames)

    return df

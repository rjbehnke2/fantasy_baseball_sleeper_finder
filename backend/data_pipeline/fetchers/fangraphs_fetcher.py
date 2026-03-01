"""Fetches season-level batting and pitching stats from multiple sources.

Tries multiple FanGraphs API endpoints first, then pybaseball FanGraphs
functions, and finally falls back to Baseball Reference via pybaseball.
The cleaning module downstream handles column name normalization.
"""

import logging
import time
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

# Baseball Reference batting columns -> FanGraphs-style column names
# (so the cleaning module's BATTING_COLUMN_MAP can pick them up)
_BBREF_BATTING_RENAME = {
    "Name": "Name",
    "Age": "Age",
    "Tm": "Team",
    "Year": "Season",
    "PA": "PA",
    "AB": "AB",
    "H": "H",
    "HR": "HR",
    "RBI": "RBI",
    "R": "R",
    "SB": "SB",
    "CS": "CS",
    "BA": "AVG",
    "OBP": "OBP",
    "SLG": "SLG",
    "OPS": "OPS",
    "BB": "BB_count",
    "SO": "SO_count",
    "BB%": "BB%",
    "SO%": "K%",
    "GDP": "GDP",
    "HBP": "HBP",
    "2B": "2B",
    "3B": "3B",
    "WAR": "WAR",
}

# Baseball Reference pitching columns -> FanGraphs-style column names
_BBREF_PITCHING_RENAME = {
    "Name": "Name",
    "Age": "Age",
    "Tm": "Team",
    "Year": "Season",
    "W": "W",
    "L": "L",
    "SV": "SV",
    "IP": "IP",
    "GS": "GS",
    "G": "G",
    "SO": "SO",
    "BB": "BB",
    "H": "H",
    "HR": "HR",
    "ERA": "ERA",
    "WHIP": "WHIP",
    "SO/W": "SO_W",
    "WAR": "WAR",
    "SO9": "K/9",
    "BB9": "BB/9",
    "HR9": "HR/9",
}


def enable_cache() -> None:
    """Enable pybaseball cache (used for Chadwick register)."""
    import pybaseball
    pybaseball.cache.enable()


def fetch_batting_stats(start_season: int, end_season: int, qual: int = 50) -> pd.DataFrame:
    """Fetch batting stats for a range of seasons.

    Tries FanGraphs API, then pybaseball FanGraphs functions, then
    Baseball Reference as a final fallback.

    Returns:
        DataFrame with one row per player per season.
    """
    logger.info(f"Fetching batting stats {start_season}-{end_season} (qual={qual})")

    # Try direct FanGraphs API with multiple URL patterns
    for url in _API_URLS:
        try:
            df = _fetch_from_api(url, "bat", start_season, end_season, qual)
            logger.info(f"Fetched {len(df)} batting rows via {url}")
            return df
        except Exception as e:
            logger.warning(f"API {url} failed for batting: {e}")

    # Fallback to pybaseball FanGraphs functions
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

    # Final fallback: Baseball Reference
    logger.info("All FanGraphs sources failed. Trying Baseball Reference...")
    try:
        df = _fetch_bbref_batting(start_season, end_season)
        logger.info(f"Fetched {len(df)} batting rows via Baseball Reference")
        return df
    except Exception as e:
        logger.warning(f"Baseball Reference batting failed: {e}")

    raise RuntimeError(
        "All data sources failed (FanGraphs API, pybaseball, Baseball Reference). "
        "Sites may be down or blocking requests. Try again later."
    )


def fetch_pitching_stats(start_season: int, end_season: int, qual: int = 20) -> pd.DataFrame:
    """Fetch pitching stats for a range of seasons.

    Tries FanGraphs API, then pybaseball FanGraphs functions, then
    Baseball Reference as a final fallback.

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

    # Final fallback: Baseball Reference
    logger.info("All FanGraphs sources failed. Trying Baseball Reference...")
    try:
        df = _fetch_bbref_pitching(start_season, end_season)
        logger.info(f"Fetched {len(df)} pitching rows via Baseball Reference")
        return df
    except Exception as e:
        logger.warning(f"Baseball Reference pitching failed: {e}")

    raise RuntimeError(
        "All data sources failed (FanGraphs API, pybaseball, Baseball Reference). "
        "Sites may be down or blocking requests. Try again later."
    )


def _fetch_bbref_batting(start_season: int, end_season: int) -> pd.DataFrame:
    """Fetch batting stats from Baseball Reference, one season at a time.

    BBRef doesn't have advanced Statcast metrics (Barrel%, xwOBA, etc.),
    but provides solid core stats. The cleaning module handles missing columns.
    """
    import pybaseball

    frames = []
    for year in range(start_season, end_season + 1):
        logger.info(f"Fetching BBRef batting for {year}...")
        try:
            df = pybaseball.batting_stats_bref(year)
            df["Year"] = year
            frames.append(df)
            # Be polite to Baseball Reference — small delay between requests
            if year < end_season:
                time.sleep(2)
        except Exception as e:
            logger.warning(f"BBRef batting {year} failed: {e}")
            continue

    if not frames:
        raise RuntimeError("No batting data retrieved from Baseball Reference")

    combined = pd.concat(frames, ignore_index=True)

    # Rename BBRef columns to match FanGraphs-style names the cleaning module expects
    actual_renames = {k: v for k, v in _BBREF_BATTING_RENAME.items() if k in combined.columns}
    combined = combined.rename(columns=actual_renames)

    # BBRef uses player name directly, and doesn't have a FanGraphs ID.
    # We need to match via name. Add a placeholder IDfg so the pipeline
    # can attempt name-based matching downstream.
    if "IDfg" not in combined.columns:
        combined["IDfg"] = None

    # Compute ISO if not present: SLG - AVG
    if "ISO" not in combined.columns and "SLG" in combined.columns and "AVG" in combined.columns:
        combined["ISO"] = pd.to_numeric(combined["SLG"], errors="coerce") - pd.to_numeric(combined["AVG"], errors="coerce")

    # Compute BABIP if we have the counting stats: (H - HR) / (AB - SO - HR + SF)
    # BBRef may not always have SF, so skip if not available
    if "BABIP" not in combined.columns:
        try:
            h = pd.to_numeric(combined.get("H"), errors="coerce")
            hr = pd.to_numeric(combined.get("HR"), errors="coerce")
            ab = pd.to_numeric(combined.get("AB"), errors="coerce")
            so = pd.to_numeric(combined.get("SO_count"), errors="coerce")
            denom = ab - so - hr
            combined["BABIP"] = (h - hr) / denom.replace(0, pd.NA)
        except Exception:
            pass

    logger.info(f"BBRef batting: {len(combined)} rows, columns: {list(combined.columns[:15])}...")
    return combined


def _fetch_bbref_pitching(start_season: int, end_season: int) -> pd.DataFrame:
    """Fetch pitching stats from Baseball Reference, one season at a time."""
    import pybaseball

    frames = []
    for year in range(start_season, end_season + 1):
        logger.info(f"Fetching BBRef pitching for {year}...")
        try:
            df = pybaseball.pitching_stats_bref(year)
            df["Year"] = year
            frames.append(df)
            if year < end_season:
                time.sleep(2)
        except Exception as e:
            logger.warning(f"BBRef pitching {year} failed: {e}")
            continue

    if not frames:
        raise RuntimeError("No pitching data retrieved from Baseball Reference")

    combined = pd.concat(frames, ignore_index=True)

    actual_renames = {k: v for k, v in _BBREF_PITCHING_RENAME.items() if k in combined.columns}
    combined = combined.rename(columns=actual_renames)

    if "IDfg" not in combined.columns:
        combined["IDfg"] = None

    # Compute K% and BB% from counting stats if not present
    # BBRef provides SO and BB as counting stats, and sometimes batters faced (BF)
    if "K%" not in combined.columns and "SO" in combined.columns:
        bf = pd.to_numeric(combined.get("BF"), errors="coerce")
        if bf is not None and bf.notna().any():
            combined["K%"] = pd.to_numeric(combined["SO"], errors="coerce") / bf
            combined["BB%"] = pd.to_numeric(combined.get("BB", 0), errors="coerce") / bf

    logger.info(f"BBRef pitching: {len(combined)} rows, columns: {list(combined.columns[:15])}...")
    return combined


def _fetch_from_api(
    base_url: str,
    stats: str,
    start_season: int,
    end_season: int,
    qual: int,
) -> pd.DataFrame:
    """Fetch data directly from a FanGraphs JSON API endpoint."""
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

    content_type = resp.headers.get("Content-Type", "")
    if "json" not in content_type and "javascript" not in content_type:
        preview = resp.text[:200].replace("\n", " ")
        raise ValueError(
            f"Expected JSON but got Content-Type: {content_type}. "
            f"Response preview: {preview}"
        )

    data = resp.json()

    if isinstance(data, dict) and "data" in data:
        rows = data["data"]
    elif isinstance(data, list):
        rows = data
    else:
        raise ValueError(f"Unexpected API response format: {type(data)}")

    if not rows:
        raise ValueError("FanGraphs API returned no data")

    df = pd.DataFrame(rows)
    df = _normalize_api_columns(df)

    logger.info(f"API returned {len(df)} rows with columns: {list(df.columns[:15])}...")
    return df


def _normalize_api_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize FanGraphs API JSON column names to match pybaseball conventions."""
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

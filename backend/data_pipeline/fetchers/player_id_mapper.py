"""Cross-references player IDs across FanGraphs, Baseball Reference, and MLBAM systems.

This is a critical integration module — pybaseball uses MLBAM IDs for Statcast,
FanGraphs IDs for season stats, and Baseball Reference has its own IDs. All must
be mapped to a canonical player record.
"""

import logging

import pandas as pd
import pybaseball

logger = logging.getLogger(__name__)


def build_player_id_map() -> pd.DataFrame:
    """Build a comprehensive player ID mapping table.

    Uses pybaseball's built-in Chadwick register to get cross-references
    between MLBAM, FanGraphs, and Baseball Reference IDs.

    Returns:
        DataFrame with columns: mlbam_id, fangraphs_id, bbref_id, full_name, birth_date.
    """
    logger.info("Building player ID map from Chadwick register...")
    register = pybaseball.chadwick_register()

    # Filter to players with at least an MLBAM ID (modern players)
    register = register[register["key_mlbam"].notna()].copy()

    # Build the mapping table
    # Note: Chadwick register no longer includes birth date columns.
    # We use mlb_played_first/last as proxies for debut year.
    id_map = pd.DataFrame({
        "mlbam_id": register["key_mlbam"].astype(int),
        "fangraphs_id": register["key_fangraphs"].astype("Int64").astype(str).replace("<NA>", None),
        "bbref_id": register["key_bbref"],
        "full_name": register["name_first"].str.strip() + " " + register["name_last"].str.strip(),
        "mlb_played_first": register.get("mlb_played_first"),
        "mlb_played_last": register.get("mlb_played_last"),
    })

    # Drop exact duplicates
    id_map = id_map.drop_duplicates(subset=["mlbam_id"])

    logger.info(f"Built ID map with {len(id_map)} players")
    return id_map


def lookup_mlbam_from_fangraphs(fangraphs_id: str, id_map: pd.DataFrame) -> int | None:
    """Look up the MLBAM ID for a given FanGraphs ID."""
    match = id_map[id_map["fangraphs_id"] == str(fangraphs_id)]
    if len(match) > 0:
        return int(match.iloc[0]["mlbam_id"])
    return None


def lookup_fangraphs_from_mlbam(mlbam_id: int, id_map: pd.DataFrame) -> str | None:
    """Look up the FanGraphs ID for a given MLBAM ID."""
    match = id_map[id_map["mlbam_id"] == mlbam_id]
    if len(match) > 0:
        val = match.iloc[0]["fangraphs_id"]
        return str(val) if val is not None else None
    return None

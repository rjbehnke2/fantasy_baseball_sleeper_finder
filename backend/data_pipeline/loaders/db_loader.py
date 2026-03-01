"""Loads cleaned data into PostgreSQL via SQLAlchemy."""

import logging

import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import BattingSeason, PitchingSeason, Player, StatcastAggregate

logger = logging.getLogger(__name__)


async def upsert_players_from_id_map(session: AsyncSession, id_map: pd.DataFrame) -> int:
    """Insert or update players from the player ID mapping table.

    Args:
        session: Async database session.
        id_map: DataFrame with mlbam_id, fangraphs_id, bbref_id, full_name columns.

    Returns:
        Number of players upserted.
    """
    count = 0
    for _, row in id_map.iterrows():
        fg_id = row.get("fangraphs_id")
        # Treat -1 and NaN as no FanGraphs ID
        if pd.isna(fg_id) or str(fg_id) in ("-1", "<NA>", "None", "nan"):
            fg_id = None
        else:
            fg_id = str(fg_id)

        bb_id = str(row["bbref_id"]) if pd.notna(row.get("bbref_id")) else None

        stmt = insert(Player).values(
            mlbam_id=int(row["mlbam_id"]),
            fangraphs_id=fg_id,
            bbref_id=bb_id,
            full_name=str(row["full_name"]),
        ).on_conflict_do_update(
            index_elements=["mlbam_id"],
            set_={
                "fangraphs_id": fg_id,
                "bbref_id": bb_id,
                "full_name": str(row["full_name"]),
            },
        )
        await session.execute(stmt)
        count += 1
        if count % 500 == 0:
            await session.flush()
            logger.info(f"Upserted {count} players...")

    await session.commit()
    logger.info(f"Upserted {count} total players")
    return count


async def load_batting_seasons(session: AsyncSession, df: pd.DataFrame) -> int:
    """Load cleaned batting stats into the database.

    Looks up player_id from fangraphs_id first, then falls back to
    name-based matching for data sources without FanGraphs IDs (e.g.
    Baseball Reference).

    Args:
        session: Async database session.
        df: Cleaned batting stats DataFrame (from cleaning.clean_batting_stats).

    Returns:
        Number of rows loaded.
    """
    count = 0
    fg_to_pid, name_to_pid = await _build_player_lookups(session)

    for _, row in df.iterrows():
        player_id = _resolve_player_id(row, fg_to_pid, name_to_pid)
        if player_id is None:
            continue

        values = {"player_id": player_id}
        for col in BattingSeason.__table__.columns:
            if col.name in ("id", "player_id"):
                continue
            if col.name in row.index and pd.notna(row[col.name]):
                values[col.name] = row[col.name]

        stmt = insert(BattingSeason).values(**values).on_conflict_do_update(
            constraint="uq_batting_player_season",
            set_={k: v for k, v in values.items() if k != "player_id"},
        )
        await session.execute(stmt)
        count += 1
        if count % 500 == 0:
            await session.flush()

    await session.commit()
    logger.info(f"Loaded {count} batting season rows")
    return count


async def load_pitching_seasons(session: AsyncSession, df: pd.DataFrame) -> int:
    """Load cleaned pitching stats into the database.

    Args:
        session: Async database session.
        df: Cleaned pitching stats DataFrame.

    Returns:
        Number of rows loaded.
    """
    count = 0
    fg_to_pid, name_to_pid = await _build_player_lookups(session)

    for _, row in df.iterrows():
        player_id = _resolve_player_id(row, fg_to_pid, name_to_pid)
        if player_id is None:
            continue

        values = {"player_id": player_id}
        for col in PitchingSeason.__table__.columns:
            if col.name in ("id", "player_id"):
                continue
            if col.name in row.index and pd.notna(row[col.name]):
                values[col.name] = row[col.name]

        stmt = insert(PitchingSeason).values(**values).on_conflict_do_update(
            constraint="uq_pitching_player_season",
            set_={k: v for k, v in values.items() if k != "player_id"},
        )
        await session.execute(stmt)
        count += 1
        if count % 500 == 0:
            await session.flush()

    await session.commit()
    logger.info(f"Loaded {count} pitching season rows")
    return count


async def _build_player_lookups(
    session: AsyncSession,
) -> tuple[dict[str, int], dict[str, int]]:
    """Build player lookup dicts: fangraphs_id->player_id and name->player_id."""
    result = await session.execute(
        select(Player.id, Player.fangraphs_id, Player.full_name)
    )
    fg_to_pid: dict[str, int] = {}
    name_to_pid: dict[str, int] = {}
    for row in result:
        if row.fangraphs_id:
            fg_to_pid[row.fangraphs_id] = row.id
        if row.full_name:
            # Normalize name for matching: lowercase, strip whitespace
            name_to_pid[row.full_name.strip().lower()] = row.id
    return fg_to_pid, name_to_pid


def _resolve_player_id(
    row: pd.Series,
    fg_to_pid: dict[str, int],
    name_to_pid: dict[str, int],
) -> int | None:
    """Resolve a player_id from a stats row, trying fangraphs_id first, then name."""
    # Try fangraphs_id first
    fg_id = row.get("fangraphs_id")
    if pd.notna(fg_id) and str(fg_id) not in ("", "None", "nan", "<NA>"):
        player_id = fg_to_pid.get(str(fg_id))
        if player_id is not None:
            return player_id

    # Fallback to name-based matching
    name = row.get("full_name")
    if pd.notna(name) and str(name).strip():
        player_id = name_to_pid.get(str(name).strip().lower())
        if player_id is not None:
            return player_id

    return None


async def load_statcast_aggregates(
    session: AsyncSession, df: pd.DataFrame, player_type: str = "batter"
) -> int:
    """Load aggregated Statcast data into the database.

    Args:
        session: Async database session.
        df: Aggregated Statcast DataFrame (from statcast_fetcher.aggregate_*).
        player_type: 'batter' or 'pitcher'.

    Returns:
        Number of rows loaded.
    """
    count = 0
    result = await session.execute(select(Player.id, Player.mlbam_id))
    mlbam_to_pid = {row.mlbam_id: row.id for row in result if row.mlbam_id}

    for _, row in df.iterrows():
        mlbam_id = int(row.get("mlbam_id", 0))
        player_id = mlbam_to_pid.get(mlbam_id)
        if player_id is None:
            continue

        values = {"player_id": player_id, "player_type": player_type}
        for col in StatcastAggregate.__table__.columns:
            if col.name in ("id", "player_id", "player_type"):
                continue
            if col.name in row.index and pd.notna(row[col.name]):
                values[col.name] = row[col.name]

        stmt = insert(StatcastAggregate).values(**values).on_conflict_do_update(
            constraint="uq_statcast_player_season",
            set_={k: v for k, v in values.items() if k != "player_id"},
        )
        await session.execute(stmt)
        count += 1
        if count % 500 == 0:
            await session.flush()

    await session.commit()
    logger.info(f"Loaded {count} {player_type} Statcast aggregate rows")
    return count

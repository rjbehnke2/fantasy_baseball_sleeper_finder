"""Business logic for player queries."""

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models import BattingSeason, PitchingSeason, Player, Projection

logger = logging.getLogger(__name__)


async def get_players(
    session: AsyncSession,
    page: int = 1,
    per_page: int = 50,
    search: str | None = None,
    position: str | None = None,
    team: str | None = None,
    sort_by: str = "full_name",
    sort_order: str = "asc",
) -> tuple[list[Player], int]:
    """Get paginated list of players with optional filters.

    Returns:
        Tuple of (players, total_count).
    """
    query = select(Player)
    count_query = select(func.count(Player.id))

    # Apply filters
    if search:
        query = query.where(Player.full_name.ilike(f"%{search}%"))
        count_query = count_query.where(Player.full_name.ilike(f"%{search}%"))
    if position:
        query = query.where(Player.position == position)
        count_query = count_query.where(Player.position == position)
    if team:
        query = query.where(Player.team == team)
        count_query = count_query.where(Player.team == team)

    # Get total count
    total = await session.scalar(count_query)

    # Apply sorting
    sort_col = getattr(Player, sort_by, Player.full_name)
    if sort_order == "desc":
        query = query.order_by(sort_col.desc())
    else:
        query = query.order_by(sort_col.asc())

    # Paginate
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await session.execute(query)
    players = list(result.scalars().all())

    return players, total or 0


async def get_player_detail(session: AsyncSession, player_id: int) -> Player | None:
    """Get full player detail with relationships loaded."""
    query = (
        select(Player)
        .where(Player.id == player_id)
        .options(
            selectinload(Player.batting_seasons),
            selectinload(Player.pitching_seasons),
            selectinload(Player.projections),
        )
    )
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def get_latest_projection(session: AsyncSession, player_id: int) -> Projection | None:
    """Get the most recent projection for a player."""
    query = (
        select(Projection)
        .where(Projection.player_id == player_id)
        .order_by(Projection.run_date.desc())
        .limit(1)
    )
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def get_players_with_projections(
    session: AsyncSession,
    sort_by: str = "ai_value_score",
    sort_order: str = "desc",
    position: str | None = None,
    limit: int = 300,
) -> list[dict]:
    """Get players joined with their latest projections for rankings.

    Returns:
        List of dicts with player + projection data.
    """
    # Subquery for latest projection per player
    latest_proj = (
        select(
            Projection.player_id,
            func.max(Projection.run_date).label("max_date"),
        )
        .group_by(Projection.player_id)
        .subquery()
    )

    query = (
        select(Player, Projection)
        .outerjoin(
            latest_proj,
            Player.id == latest_proj.c.player_id,
        )
        .outerjoin(
            Projection,
            (Projection.player_id == latest_proj.c.player_id)
            & (Projection.run_date == latest_proj.c.max_date),
        )
    )

    if position:
        query = query.where(Player.position == position)

    # Sort by projection column if available
    proj_sort_cols = {
        "ai_value_score", "sleeper_score", "bust_score", "consistency_score",
        "improvement_score", "auction_value", "dynasty_value", "surplus_value",
    }
    if sort_by in proj_sort_cols:
        sort_col = getattr(Projection, sort_by)
        if sort_order == "desc":
            query = query.order_by(sort_col.desc().nullslast())
        else:
            query = query.order_by(sort_col.asc().nullsfirst())
    else:
        sort_col = getattr(Player, sort_by, Player.full_name)
        if sort_order == "desc":
            query = query.order_by(sort_col.desc())
        else:
            query = query.order_by(sort_col.asc())

    query = query.limit(limit)
    result = await session.execute(query)

    players_with_projections = []
    for player, projection in result:
        players_with_projections.append({
            "player": player,
            "projection": projection,
        })

    return players_with_projections

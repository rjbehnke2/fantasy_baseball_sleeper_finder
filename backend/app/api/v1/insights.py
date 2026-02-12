"""Daily AI insights digest endpoint.

Provides a summary of the most interesting findings from the latest model run:
risers, fallers, top sleepers, bust warnings, and notable trend changes.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.models.player import Player
from backend.app.models.projections import Projection

router = APIRouter(prefix="/insights", tags=["insights"])


class InsightPlayer(BaseModel):
    player_id: int
    full_name: str
    team: str | None = None
    position: str | None = None
    score: float | None = None
    reason: str = ""


class DailyDigest(BaseModel):
    top_sleepers: list[InsightPlayer]
    bust_warnings: list[InsightPlayer]
    dynasty_risers: list[InsightPlayer]
    improvement_leaders: list[InsightPlayer]
    generated_date: str


@router.get("/daily", response_model=DailyDigest)
async def get_daily_digest(
    limit: int = 5,
    db: AsyncSession = Depends(get_db),
):
    """Get the daily AI insights digest.

    Summarizes the most actionable findings from the latest model run.
    """
    from datetime import date

    # Subquery: latest projection per player
    latest_proj = (
        select(
            Projection.player_id,
            func.max(Projection.run_date).label("max_date"),
        )
        .group_by(Projection.player_id)
        .subquery()
    )

    # Join to get full projection data
    stmt = (
        select(Player, Projection)
        .join(Projection, Projection.player_id == Player.id)
        .join(
            latest_proj,
            (Projection.player_id == latest_proj.c.player_id)
            & (Projection.run_date == latest_proj.c.max_date),
        )
    )

    result = await db.execute(stmt)
    rows = result.all()

    if not rows:
        return DailyDigest(
            top_sleepers=[],
            bust_warnings=[],
            dynasty_risers=[],
            improvement_leaders=[],
            generated_date=date.today().isoformat(),
        )

    # Build player-projection pairs
    players_projs = [(p, proj) for p, proj in rows]

    # Top sleepers by sleeper_score
    by_sleeper = sorted(
        players_projs,
        key=lambda x: x[1].sleeper_score or 0,
        reverse=True,
    )[:limit]
    top_sleepers = [
        InsightPlayer(
            player_id=p.id,
            full_name=p.full_name,
            team=p.team,
            position=p.position,
            score=proj.sleeper_score,
            reason=f"Sleeper score {proj.sleeper_score:.0f} — underlying quality exceeds surface stats",
        )
        for p, proj in by_sleeper
        if proj.sleeper_score and proj.sleeper_score > 50
    ]

    # Bust warnings by bust_score
    by_bust = sorted(
        players_projs,
        key=lambda x: x[1].bust_score or 0,
        reverse=True,
    )[:limit]
    bust_warnings = [
        InsightPlayer(
            player_id=p.id,
            full_name=p.full_name,
            team=p.team,
            position=p.position,
            score=proj.bust_score,
            reason=f"Bust score {proj.bust_score:.0f} — regression risk from unsustainable metrics",
        )
        for p, proj in by_bust
        if proj.bust_score and proj.bust_score > 50
    ]

    # Dynasty risers by dynasty_value
    by_dynasty = sorted(
        players_projs,
        key=lambda x: x[1].dynasty_value or 0,
        reverse=True,
    )[:limit]
    dynasty_risers = [
        InsightPlayer(
            player_id=p.id,
            full_name=p.full_name,
            team=p.team,
            position=p.position,
            score=proj.dynasty_value,
            reason=f"Dynasty value {proj.dynasty_value:.0f}/100 — strong long-term outlook",
        )
        for p, proj in by_dynasty
    ]

    # Improvement leaders
    by_improvement = sorted(
        players_projs,
        key=lambda x: x[1].improvement_score or 0,
        reverse=True,
    )[:limit]
    improvement_leaders = [
        InsightPlayer(
            player_id=p.id,
            full_name=p.full_name,
            team=p.team,
            position=p.position,
            score=proj.improvement_score,
            reason=f"Improvement score +{proj.improvement_score:.0f} — sustained skills development",
        )
        for p, proj in by_improvement
        if proj.improvement_score and proj.improvement_score > 20
    ]

    return DailyDigest(
        top_sleepers=top_sleepers,
        bust_warnings=bust_warnings,
        dynasty_risers=dynasty_risers,
        improvement_leaders=improvement_leaders,
        generated_date=date.today().isoformat(),
    )

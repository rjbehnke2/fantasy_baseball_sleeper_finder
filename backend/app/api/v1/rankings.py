"""AI rankings endpoints."""

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.schemas.player import PlayerSummary
from backend.app.schemas.rankings import RankedPlayer, RankingsResponse
from backend.app.services.player_service import get_players_with_projections

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rankings", tags=["rankings"])


@router.get("", response_model=RankingsResponse)
async def get_rankings(
    position: str | None = None,
    sort_by: str = Query("ai_value_score", description="Score to rank by"),
    limit: int = Query(300, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """Get AI-powered player rankings with value breakdowns."""
    logger.info(f"GET /rankings sort_by={sort_by} limit={limit} position={position}")
    results = await get_players_with_projections(
        db, sort_by=sort_by, sort_order="desc", position=position, limit=limit
    )
    logger.info(f"  → query returned {len(results)} results")

    rankings = []
    for rank, item in enumerate(results, 1):
        player = item["player"]
        proj = item["projection"]
        summary = PlayerSummary(
            id=player.id,
            full_name=player.full_name,
            team=player.team,
            position=player.position,
            age=player.age,
            ai_value_score=proj.ai_value_score if proj else None,
            sleeper_score=proj.sleeper_score if proj else None,
            bust_score=proj.bust_score if proj else None,
            consistency_score=proj.consistency_score if proj else None,
            improvement_score=proj.improvement_score if proj else None,
            auction_value=proj.auction_value if proj else None,
            surplus_value=proj.surplus_value if proj else None,
            dynasty_value=proj.dynasty_value if proj else None,
        )
        rankings.append(RankedPlayer(
            rank=rank,
            player=summary,
            value_breakdown=proj.shap_explanations if proj else None,
        ))

    response = RankingsResponse(
        rankings=rankings,
        total=len(rankings),
        ranking_type=sort_by,
    )
    logger.info(f"  → returning {len(rankings)} ranked players")
    return response


@router.get("/sleepers", response_model=RankingsResponse)
async def get_sleepers(
    position: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Get top sleeper candidates ranked by sleeper score."""
    return await _get_ranked_by(db, "sleeper_score", position, limit, "sleepers")


@router.get("/busts", response_model=RankingsResponse)
async def get_busts(
    position: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Get top bust risks ranked by bust score."""
    return await _get_ranked_by(db, "bust_score", position, limit, "busts")


@router.get("/dynasty", response_model=RankingsResponse)
async def get_dynasty_rankings(
    position: str | None = None,
    limit: int = Query(300, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """Get dynasty-specific rankings weighted toward long-term value."""
    return await _get_ranked_by(db, "dynasty_value", position, limit, "dynasty")


@router.get("/auction-values", response_model=RankingsResponse)
async def get_auction_values(
    position: str | None = None,
    limit: int = Query(300, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """Get players sorted by projected auction dollar value."""
    return await _get_ranked_by(db, "auction_value", position, limit, "auction")


async def _get_ranked_by(
    db: AsyncSession,
    score_field: str,
    position: str | None,
    limit: int,
    ranking_type: str,
) -> RankingsResponse:
    """Helper to build rankings by any projection score."""
    logger.info(f"GET /rankings/{ranking_type} sort_by={score_field} limit={limit}")
    results = await get_players_with_projections(
        db, sort_by=score_field, sort_order="desc", position=position, limit=limit
    )
    logger.info(f"  → query returned {len(results)} results")

    rankings = []
    for rank, item in enumerate(results, 1):
        player = item["player"]
        proj = item["projection"]
        summary = PlayerSummary(
            id=player.id,
            full_name=player.full_name,
            team=player.team,
            position=player.position,
            age=player.age,
            ai_value_score=proj.ai_value_score if proj else None,
            sleeper_score=proj.sleeper_score if proj else None,
            bust_score=proj.bust_score if proj else None,
            consistency_score=proj.consistency_score if proj else None,
            improvement_score=proj.improvement_score if proj else None,
            auction_value=proj.auction_value if proj else None,
            surplus_value=proj.surplus_value if proj else None,
            dynasty_value=proj.dynasty_value if proj else None,
        )
        rankings.append(RankedPlayer(rank=rank, player=summary))

    logger.info(f"  → returning {len(rankings)} ranked players for {ranking_type}")
    return RankingsResponse(rankings=rankings, total=len(rankings), ranking_type=ranking_type)

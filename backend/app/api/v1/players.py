"""Player lookup, search, detail, and scouting report endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.schemas.player import (
    BattingSeasonSchema,
    PitchingSeasonSchema,
    PlayerDetail,
    PlayerListResponse,
    PlayerSummary,
    ProjectionSchema,
)
from backend.app.schemas.scouting_report import (
    ScoutingReportListResponse,
    ScoutingReportResponse,
)
from backend.app.services.player_service import get_player_detail, get_players
from backend.app.services.scouting_report_service import (
    get_all_reports_for_player,
    get_report,
)

router = APIRouter(prefix="/players", tags=["players"])


@router.get("", response_model=PlayerListResponse)
async def list_players(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    search: str | None = None,
    position: str | None = None,
    team: str | None = None,
    sort_by: str = "full_name",
    sort_order: str = "asc",
    db: AsyncSession = Depends(get_db),
):
    """List players with pagination and filtering."""
    players, total = await get_players(
        db,
        page=page,
        per_page=per_page,
        search=search,
        position=position,
        team=team,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    summaries = [
        PlayerSummary(
            id=p.id,
            full_name=p.full_name,
            team=p.team,
            position=p.position,
            age=p.age,
        )
        for p in players
    ]

    return PlayerListResponse(
        players=summaries,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{player_id}", response_model=PlayerDetail)
async def get_player(
    player_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get full player detail with stats and projections."""
    player = await get_player_detail(db, player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    # Get latest projection
    projection = None
    if player.projections:
        latest = max(player.projections, key=lambda p: p.run_date)
        projection = ProjectionSchema.model_validate(latest)

    # Sort seasons by year descending
    batting = sorted(player.batting_seasons, key=lambda s: s.season, reverse=True)
    pitching = sorted(player.pitching_seasons, key=lambda s: s.season, reverse=True)

    return PlayerDetail(
        id=player.id,
        full_name=player.full_name,
        team=player.team,
        position=player.position,
        age=player.age,
        birth_date=player.birth_date,
        mlb_debut_date=player.mlb_debut_date,
        status=player.status,
        prospect_rank=player.prospect_rank,
        batting_seasons=[BattingSeasonSchema.model_validate(s) for s in batting],
        pitching_seasons=[PitchingSeasonSchema.model_validate(s) for s in pitching],
        projection=projection,
    )


@router.get("/{player_id}/trajectory")
async def get_player_trajectory(
    player_id: int,
    projection_years: int = Query(6, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
):
    """Get multi-season career trajectory projection for a player."""
    from datetime import date

    from backend.ml.models.trajectory_model import project_career_trajectory

    player = await get_player_detail(db, player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    age = player.age or 28
    player_type = "pitcher" if player.pitching_seasons else "batter"

    # Get latest projection for scores
    current_value = 50.0
    improvement = 0.0
    consistency = 50.0
    dynasty = 50.0

    if player.projections:
        latest = max(player.projections, key=lambda p: p.run_date)
        current_value = latest.ai_value_score or latest.dynasty_value or 50.0
        improvement = latest.improvement_score or 0.0
        consistency = latest.consistency_score or 50.0
        dynasty = latest.dynasty_value or 50.0

    trajectory = project_career_trajectory(
        player_id=player_id,
        current_age=age,
        current_value=current_value,
        player_type=player_type,
        improvement_score=improvement,
        consistency_score=consistency,
        dynasty_value=dynasty,
        projection_years=projection_years,
        current_season=date.today().year,
    )

    return {
        "player_id": trajectory.player_id,
        "current_value": trajectory.current_value,
        "peak_season": trajectory.peak_season,
        "peak_value": trajectory.peak_value,
        "career_value_remaining": trajectory.career_war_remaining,
        "trajectory_grade": trajectory.trajectory_grade,
        "trajectory": [
            {
                "season": p.season,
                "projected_value": p.projected_value,
                "upper_bound": p.upper_bound,
                "lower_bound": p.lower_bound,
                "age": p.age,
            }
            for p in trajectory.trajectory
        ],
    }


@router.get("/{player_id}/scouting-report", response_model=ScoutingReportResponse)
async def get_scouting_report(
    player_id: int,
    report_type: str = Query("full", description="Report type: full, sleeper_spotlight, bust_warning, dynasty_outlook"),
    db: AsyncSession = Depends(get_db),
):
    """Get the LLM-generated scouting report for a player.

    Returns a cached report if available. If no report exists, returns 404
    with a message to generate one via POST.
    """
    report = await get_report(db, player_id, report_type)
    if not report:
        raise HTTPException(
            status_code=404,
            detail=f"No {report_type} scouting report available for this player. "
                   "Reports are generated in batch or can be requested on demand.",
        )
    return ScoutingReportResponse.model_validate(report)


@router.get("/{player_id}/scouting-reports", response_model=ScoutingReportListResponse)
async def list_scouting_reports(
    player_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get all scouting report types for a player."""
    reports = await get_all_reports_for_player(db, player_id)
    return ScoutingReportListResponse(
        reports=[ScoutingReportResponse.model_validate(r) for r in reports],
        total=len(reports),
    )

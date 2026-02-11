"""League settings CRUD endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.models.league_settings import LeagueSettings
from backend.app.schemas.league import LeagueSettingsCreate, LeagueSettingsResponse

router = APIRouter(prefix="/league-settings", tags=["league-settings"])


@router.post("", response_model=LeagueSettingsResponse, status_code=201)
async def create_league_settings(
    data: LeagueSettingsCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new league configuration."""
    settings = LeagueSettings(**data.model_dump())
    db.add(settings)
    await db.commit()
    await db.refresh(settings)
    return LeagueSettingsResponse.model_validate(settings)


@router.get("/{settings_id}", response_model=LeagueSettingsResponse)
async def get_league_settings(
    settings_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a league configuration by ID."""
    result = await db.execute(select(LeagueSettings).where(LeagueSettings.id == settings_id))
    settings = result.scalar_one_or_none()
    if not settings:
        raise HTTPException(status_code=404, detail="League settings not found")
    return LeagueSettingsResponse.model_validate(settings)

"""Aggregates all v1 API routers."""

from fastapi import APIRouter

from backend.app.api.v1.insights import router as insights_router
from backend.app.api.v1.league import router as league_router
from backend.app.api.v1.players import router as players_router
from backend.app.api.v1.rankings import router as rankings_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(players_router)
v1_router.include_router(rankings_router)
v1_router.include_router(league_router)
v1_router.include_router(insights_router)

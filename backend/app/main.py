"""FastAPI application factory."""

import logging
import math
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.app.api.v1.router import v1_router
from backend.app.config import settings

logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)


def _sanitize_for_json(obj: Any) -> Any:
    """Recursively replace NaN/Infinity floats with None for valid JSON."""
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj


class NaNSafeJSONResponse(JSONResponse):
    """JSONResponse that converts NaN/Infinity to null before serialization."""

    def render(self, content: Any) -> bytes:
        content = _sanitize_for_json(content)
        return super().render(content)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Fantasy Baseball Sleeper Finder API starting up")
    logger.info(f"Environment: {settings.app_env}")

    # Start APScheduler for nightly/weekly jobs (production only)
    if settings.app_env == "production":
        try:
            from backend.data_pipeline.orchestrator import start_scheduler, stop_scheduler
            start_scheduler()
        except Exception as e:
            logger.warning(f"Scheduler failed to start: {e}")

    yield

    if settings.app_env == "production":
        try:
            from backend.data_pipeline.orchestrator import stop_scheduler
            stop_scheduler()
        except Exception:
            pass
    logger.info("API shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Fantasy Baseball Sleeper Finder",
        description="AI-powered dynasty auction fantasy baseball player evaluations",
        version="0.1.0",
        lifespan=lifespan,
        default_response_class=NaNSafeJSONResponse,
    )

    # CORS for frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request/response logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        logger.info(f"→ {request.method} {request.url.path}")
        try:
            response = await call_next(request)
            logger.info(f"← {request.method} {request.url.path} → {response.status_code}")
            return response
        except Exception as exc:
            logger.exception(f"✗ {request.method} {request.url.path} → unhandled: {exc}")
            raise

    app.include_router(v1_router)

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": "0.1.0"}

    @app.get("/api/v1/debug/check")
    async def debug_check():
        """Diagnostic endpoint — test DB connectivity, count data, sample a ranking."""
        from sqlalchemy import func, select, text
        from backend.app.db.session import async_session_factory
        from backend.app.models import Player, Projection

        diag: dict[str, Any] = {"status": "ok"}
        try:
            async with async_session_factory() as session:
                diag["player_count"] = await session.scalar(
                    select(func.count(Player.id))
                )
                diag["projection_count"] = await session.scalar(
                    select(func.count(Projection.id))
                )
                # Sample a player with a projection
                row = (
                    await session.execute(
                        select(
                            Player.id,
                            Player.full_name,
                            Projection.ai_value_score,
                            Projection.sleeper_score,
                            Projection.bust_score,
                        )
                        .join(Projection, Player.id == Projection.player_id)
                        .order_by(Projection.ai_value_score.desc().nullslast())
                        .limit(1)
                    )
                ).first()
                if row:
                    diag["sample_player"] = {
                        "id": row[0],
                        "name": row[1],
                        "ai_value_score": row[2],
                        "sleeper_score": row[3],
                        "bust_score": row[4],
                    }
                else:
                    diag["sample_player"] = None

                # Check for NaN values in projection scores
                nan_check = await session.scalar(
                    text(
                        "SELECT count(*) FROM projections "
                        "WHERE ai_value_score = 'NaN'::float "
                        "OR sleeper_score = 'NaN'::float "
                        "OR bust_score = 'NaN'::float"
                    )
                )
                diag["nan_projection_count"] = nan_check
        except Exception as exc:
            diag["status"] = "error"
            diag["error"] = str(exc)

        return diag

    return app


app = create_app()

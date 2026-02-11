"""FastAPI application factory."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.v1.router import v1_router
from backend.app.config import settings

logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)


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
    )

    # CORS for frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(v1_router)

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": "0.1.0"}

    return app


app = create_app()

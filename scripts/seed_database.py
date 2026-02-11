"""One-time historical data backfill script.

Usage:
    python -m scripts.seed_database

This script:
1. Builds the player ID mapping table
2. Fetches FanGraphs batting/pitching stats (2015-present)
3. Cleans and loads everything into PostgreSQL
"""

import asyncio
import logging
import sys
from datetime import date

from backend.app.config import settings
from backend.app.db.base import Base
from backend.app.db.session import engine, async_session_factory
from backend.app.models import *  # noqa: F401, F403
from backend.data_pipeline.fetchers import fangraphs_fetcher, player_id_mapper
from backend.data_pipeline.loaders.db_loader import (
    load_batting_seasons,
    load_pitching_seasons,
    upsert_players_from_id_map,
)
from backend.data_pipeline.transformers.cleaning import (
    clean_batting_stats,
    clean_pitching_stats,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

CURRENT_YEAR = date.today().year


async def main():
    logger.info("=== Fantasy Baseball Sleeper Finder: Database Seed ===")
    logger.info(f"Database: {settings.database_url}")
    logger.info(f"Backfill range: {settings.backfill_start_year}-{CURRENT_YEAR}")

    # Create tables
    logger.info("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Tables created")

    # Enable pybaseball cache
    fangraphs_fetcher.enable_cache()

    # Step 1: Build player ID map
    logger.info("Step 1: Building player ID map...")
    id_map = player_id_mapper.build_player_id_map()
    async with async_session_factory() as session:
        count = await upsert_players_from_id_map(session, id_map)
    logger.info(f"Step 1 complete: {count} players in database")

    # Step 2: Fetch and load batting stats
    logger.info("Step 2: Fetching batting stats from FanGraphs...")
    raw_batting = fangraphs_fetcher.fetch_batting_stats(
        settings.backfill_start_year, CURRENT_YEAR
    )
    cleaned_batting = clean_batting_stats(raw_batting)
    async with async_session_factory() as session:
        bat_count = await load_batting_seasons(session, cleaned_batting)
    logger.info(f"Step 2 complete: {bat_count} batting season rows loaded")

    # Step 3: Fetch and load pitching stats
    logger.info("Step 3: Fetching pitching stats from FanGraphs...")
    raw_pitching = fangraphs_fetcher.fetch_pitching_stats(
        settings.backfill_start_year, CURRENT_YEAR
    )
    cleaned_pitching = clean_pitching_stats(raw_pitching)
    async with async_session_factory() as session:
        pit_count = await load_pitching_seasons(session, cleaned_pitching)
    logger.info(f"Step 3 complete: {pit_count} pitching season rows loaded")

    logger.info("=== Seed complete ===")
    logger.info(f"  Players: {count}")
    logger.info(f"  Batting seasons: {bat_count}")
    logger.info(f"  Pitching seasons: {pit_count}")


if __name__ == "__main__":
    asyncio.run(main())

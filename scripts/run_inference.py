"""Run ML inference pipeline to generate player projections.

Usage:
    python -m scripts.run_inference

This script:
1. Loads batting/pitching season data from PostgreSQL
2. Estimates player ages via MLB Stats API
3. Runs Marcel baseline projections
4. Calculates auction and dynasty values (SGP method)
5. Engineers features and runs ML model predictions
6. Computes composite AI Value Scores
7. Saves all projections to the database
"""

import asyncio
import logging
import math
from datetime import date, datetime

import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from backend.app.config import settings
from backend.app.db.base import Base
from backend.app.db.session import engine, async_session_factory
from backend.app.models import (
    BattingSeason,
    PitchingSeason,
    Player,
    Projection,
)
from backend.app.services.auction_service import (
    calculate_dynasty_value,
    calculate_sgp_values,
    calculate_surplus_value,
)
from backend.data_pipeline.transformers.feature_engineering import (
    engineer_batting_features,
    engineer_pitching_features,
)
from backend.ml.inference.predictor import Predictor
from backend.ml.models.marcel_baseline import project_all_batters, project_all_pitchers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

MODEL_VERSION = "v1.0-initial"


async def main():
    logger.info("=== Fantasy Baseball Sleeper Finder: Inference Pipeline ===")

    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Step 1: Load raw season data from database
    logger.info("Step 1: Loading season data from database...")
    batting_df, pitching_df, players_df = await _load_season_data()
    logger.info(
        f"Loaded {len(batting_df)} batting rows, {len(pitching_df)} pitching rows, "
        f"{len(players_df)} players"
    )

    if batting_df.empty and pitching_df.empty:
        logger.error("No season data found. Run seed_database.py first.")
        return

    # Step 2: Estimate player ages
    logger.info("Step 2: Estimating player ages...")
    player_ages = _estimate_ages(batting_df, pitching_df, players_df)
    logger.info(f"Estimated ages for {len(player_ages)} players")

    # Step 3: Marcel baseline projections
    logger.info("Step 3: Generating Marcel baseline projections...")
    batter_marcel = project_all_batters(batting_df, player_ages)
    pitcher_marcel = project_all_pitchers(pitching_df, player_ages)
    logger.info(
        f"Marcel projections: {len(batter_marcel)} batters, {len(pitcher_marcel)} pitchers"
    )

    # Step 4: Auction & dynasty values
    logger.info("Step 4: Calculating auction and dynasty values...")
    batter_values, pitcher_values = calculate_sgp_values(batter_marcel, pitcher_marcel)
    batter_values = calculate_surplus_value(batter_values)
    pitcher_values = calculate_surplus_value(pitcher_values)
    batter_values = calculate_dynasty_value(batter_values, player_ages)
    pitcher_values = calculate_dynasty_value(pitcher_values, player_ages)
    logger.info(
        f"Auction values: {len(batter_values)} batters, {len(pitcher_values)} pitchers"
    )

    # Step 5: Feature engineering
    logger.info("Step 5: Engineering features...")
    batter_features = engineer_batting_features(batting_df, player_ages)
    pitcher_features = engineer_pitching_features(pitching_df, player_ages)
    logger.info(
        f"Features: {len(batter_features)} batters ({len(batter_features.columns)} cols), "
        f"{len(pitcher_features)} pitchers ({len(pitcher_features.columns)} cols)"
    )

    # Step 6: Run ML inference (gracefully handles missing model artifacts)
    logger.info("Step 6: Running ML inference pipeline...")
    predictor = Predictor()
    predictor.load_models()

    scores = predictor.predict_all(
        batter_features=batter_features,
        pitcher_features=pitcher_features,
        batting_seasons=batting_df,
        pitching_seasons=pitching_df,
        player_ages=player_ages,
        batter_auction_values=batter_values,
        pitcher_auction_values=pitcher_values,
    )
    logger.info(f"Generated scores for {len(scores)} players")

    # Step 7: Build Marcel projections dict for storage
    logger.info("Step 7: Preparing Marcel projections for storage...")
    marcel_map = {}
    if not batter_marcel.empty:
        for _, row in batter_marcel.iterrows():
            pid = row["player_id"]
            marcel_map[pid] = {
                k: v for k, v in row.to_dict().items()
                if k != "player_id" and pd.notna(v)
            }
    if not pitcher_marcel.empty:
        for _, row in pitcher_marcel.iterrows():
            pid = row["player_id"]
            marcel_map[pid] = {
                k: v for k, v in row.to_dict().items()
                if k != "player_id" and pd.notna(v)
            }

    # Step 8: Save projections to database
    logger.info("Step 8: Saving projections to database...")
    count = await _save_projections(scores, marcel_map)
    logger.info(f"Saved {count} projections")

    logger.info("=== Inference complete ===")
    logger.info(f"  Total projections: {count}")
    if not scores.empty:
        top = scores.nlargest(5, "ai_value_score")
        logger.info("  Top 5 by AI Value Score:")
        for _, row in top.iterrows():
            logger.info(
                f"    Player {int(row['player_id'])}: "
                f"AI={row.get('ai_value_score', 0):.1f} "
                f"Sleeper={row.get('sleeper_score', 0):.1f} "
                f"Bust={row.get('bust_score', 0):.1f} "
                f"Auction=${row.get('auction_value', 0):.1f}"
            )


async def _load_season_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load all season data and players from the database."""
    async with async_session_factory() as session:
        # Load players
        result = await session.execute(
            select(Player.id, Player.full_name, Player.birth_date, Player.position, Player.team)
        )
        players_rows = result.all()
        players_df = pd.DataFrame(
            players_rows, columns=["player_id", "full_name", "birth_date", "position", "team"]
        )

        # Load batting seasons
        bat_cols = [c for c in BattingSeason.__table__.columns]
        result = await session.execute(select(*bat_cols))
        bat_rows = result.all()
        batting_df = pd.DataFrame(bat_rows, columns=[c.name for c in bat_cols])

        # Load pitching seasons
        pit_cols = [c for c in PitchingSeason.__table__.columns]
        result = await session.execute(select(*pit_cols))
        pit_rows = result.all()
        pitching_df = pd.DataFrame(pit_rows, columns=[c.name for c in pit_cols])

    return batting_df, pitching_df, players_df


def _estimate_ages(
    batting_df: pd.DataFrame,
    pitching_df: pd.DataFrame,
    players_df: pd.DataFrame,
) -> dict[int, int]:
    """Estimate player ages from available data.

    Uses birth_date if available, otherwise estimates from career data.
    """
    today = date.today()
    ages: dict[int, int] = {}

    # First, use birth_date from player records if available
    for _, row in players_df.iterrows():
        pid = row["player_id"]
        bd = row.get("birth_date")
        if pd.notna(bd) and bd is not None:
            try:
                if isinstance(bd, str):
                    bd = datetime.strptime(bd, "%Y-%m-%d").date()
                age = today.year - bd.year - (
                    (today.month, today.day) < (bd.month, bd.day)
                )
                ages[pid] = age
            except (ValueError, TypeError):
                pass

    # For players without birth_date, estimate from career data
    # Assumption: average MLB debut age is ~24, so approximate age from
    # first season in our data
    all_player_ids = set()
    if not batting_df.empty:
        all_player_ids.update(batting_df["player_id"].unique())
    if not pitching_df.empty:
        all_player_ids.update(pitching_df["player_id"].unique())

    for pid in all_player_ids:
        if pid in ages:
            continue

        # Find earliest season for this player
        earliest_season = None
        if not batting_df.empty:
            bat_seasons = batting_df.loc[batting_df["player_id"] == pid, "season"]
            if len(bat_seasons) > 0:
                earliest_season = bat_seasons.min()
        if not pitching_df.empty:
            pit_seasons = pitching_df.loc[pitching_df["player_id"] == pid, "season"]
            if len(pit_seasons) > 0:
                s = pit_seasons.min()
                if earliest_season is None or s < earliest_season:
                    earliest_season = s

        if earliest_season is not None:
            # Estimate: assume they were ~24 in their first tracked season
            estimated_debut_age = 24
            years_since_first = today.year - int(earliest_season)
            ages[pid] = estimated_debut_age + years_since_first
        else:
            ages[pid] = 28  # Default fallback

    return ages


async def _save_projections(scores: pd.DataFrame, marcel_map: dict) -> int:
    """Save projection scores to the database."""
    if scores.empty:
        return 0

    count = 0
    async with async_session_factory() as session:
        for _, row in scores.iterrows():
            pid = int(row["player_id"])

            # Build the projection values
            values = {
                "player_id": pid,
                "model_version": MODEL_VERSION,
                "sleeper_score": _safe_float(row.get("sleeper_score")),
                "bust_score": _safe_float(row.get("bust_score")),
                "regression_direction": _safe_float(row.get("regression_direction")),
                "regression_magnitude": _safe_float(row.get("regression_magnitude")),
                "consistency_score": _safe_float(row.get("consistency_score")),
                "improvement_score": _safe_float(row.get("improvement_score")),
                "ai_value_score": _safe_float(row.get("ai_value_score")),
                "confidence": _safe_float(row.get("confidence")),
                "auction_value": _safe_float(row.get("auction_value")),
                "dynasty_value": _safe_float(row.get("dynasty_value")),
                "surplus_value": _safe_float(row.get("surplus_value")),
                "shap_explanations": _sanitize_jsonb(row.get("shap_explanations")),
                "stat_consistency_breakdown": _sanitize_jsonb(row.get("stat_consistency_breakdown")),
                "stat_improvement_breakdown": _sanitize_jsonb(row.get("stat_improvement_breakdown")),
                "marcel_projections": _sanitize_jsonb(marcel_map.get(pid)),
            }

            # Handle value_components from AI value score
            vc = row.get("value_components")
            if isinstance(vc, dict):
                values["shap_explanations"] = values.get("shap_explanations") or {}
                if isinstance(values["shap_explanations"], dict):
                    values["shap_explanations"]["value_components"] = _sanitize_jsonb(vc)

            stmt = insert(Projection).values(**values)
            await session.execute(stmt)
            count += 1
            if count % 500 == 0:
                await session.flush()
                logger.info(f"Saved {count} projections...")

        await session.commit()

    return count


def _safe_float(val) -> float | None:
    """Convert a value to float safely, returning None for NaN/None."""
    if val is None:
        return None
    try:
        f = float(val)
        return None if math.isnan(f) else round(f, 4)
    except (ValueError, TypeError):
        return None


def _sanitize_jsonb(val):
    """Recursively sanitize a value for JSONB storage.

    Replaces NaN/Infinity with None, converts numpy types to Python types,
    and returns None for non-dict/list/scalar values.
    """
    if val is None:
        return None

    # Handle pandas NaN-like values
    if isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            return None
        return val

    # Handle numpy scalar types
    try:
        import numpy as np
        if isinstance(val, (np.integer,)):
            return int(val)
        if isinstance(val, (np.floating,)):
            f = float(val)
            return None if math.isnan(f) or math.isinf(f) else f
        if isinstance(val, np.bool_):
            return bool(val)
        if isinstance(val, np.ndarray):
            return _sanitize_jsonb(val.tolist())
    except ImportError:
        pass

    # Recurse into dicts
    if isinstance(val, dict):
        return {k: _sanitize_jsonb(v) for k, v in val.items()}

    # Recurse into lists
    if isinstance(val, list):
        return [_sanitize_jsonb(v) for v in val]

    # Strings, ints, bools pass through
    if isinstance(val, (str, int, bool)):
        return val

    # Fallback: try converting to a Python primitive
    try:
        return str(val)
    except Exception:
        return None


if __name__ == "__main__":
    asyncio.run(main())

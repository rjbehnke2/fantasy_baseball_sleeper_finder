"""End-to-end training orchestration.

Trains all ML models (sleeper, bust, regression) using historical data,
runs cross-validation, and saves model artifacts.

Usage:
    python -m backend.ml.training.train_pipeline
"""

import asyncio
import logging
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import select

from backend.data_pipeline.transformers.feature_engineering import (
    engineer_batting_features,
    engineer_pitching_features,
)
from backend.ml.inference.predictor import save_model
from backend.ml.models.bust_model import build_bust_labels, train_bust_model
from backend.ml.models.regression_model import (
    build_regression_targets,
    train_regression_model,
)
from backend.ml.models.sleeper_model import build_sleeper_labels, train_sleeper_model

logger = logging.getLogger(__name__)

ARTIFACTS_DIR = Path(__file__).parent.parent / "artifacts"


def train_all_models(
    batting_df: pd.DataFrame,
    pitching_df: pd.DataFrame,
    player_ages: dict[int, int],
    train_seasons: list[int] | None = None,
    target_season: int | None = None,
    artifacts_dir: Path | None = None,
) -> dict:
    """Train all ML models from historical season data.

    Args:
        batting_df: Multi-season batting data with player_id, season columns.
        pitching_df: Multi-season pitching data with player_id, season columns.
        player_ages: Dict mapping player_id -> current age.
        train_seasons: Seasons to use for features (e.g., [2019, 2020, 2021, 2022, 2023]).
        target_season: Season to use as target/validation (e.g., 2024).
        artifacts_dir: Where to save model artifacts.

    Returns:
        Dict of model training results with CV scores.
    """
    out_dir = artifacts_dir or ARTIFACTS_DIR
    results = {}

    if train_seasons is None:
        all_seasons = sorted(batting_df["season"].unique())
        if len(all_seasons) < 2:
            logger.error("Need at least 2 seasons of data to train")
            return results
        target_season = all_seasons[-1]
        train_seasons = all_seasons[:-1]

    logger.info(
        f"Training models: features from {train_seasons}, target season {target_season}"
    )

    # Split data into feature seasons and target season
    bat_train = batting_df[batting_df["season"].isin(train_seasons)]
    bat_target = batting_df[batting_df["season"] == target_season]
    pit_train = pitching_df[pitching_df["season"].isin(train_seasons)]
    pit_target = pitching_df[pitching_df["season"] == target_season]

    # Engineer features from training seasons
    bat_features = engineer_batting_features(bat_train, player_ages)
    pit_features = engineer_pitching_features(pit_train, player_ages)

    # --- Train batter models ---
    if not bat_features.empty and not bat_target.empty:
        # Sleeper model
        try:
            sleeper_labels = build_sleeper_labels(bat_features, bat_target)
            if sleeper_labels.sum() > 5:
                sleeper_result = train_sleeper_model(bat_features, sleeper_labels, "batter")
                save_model(sleeper_result, "sleeper_batter", out_dir)
                results["sleeper_batter"] = sleeper_result["cv_scores"]
            else:
                logger.warning("Insufficient sleeper labels for batters")
        except Exception as e:
            logger.error(f"Failed to train batter sleeper model: {e}")

        # Bust model
        try:
            bust_labels = build_bust_labels(bat_features, bat_target)
            if bust_labels.sum() > 5:
                bust_result = train_bust_model(bat_features, bust_labels, "batter")
                save_model(bust_result, "bust_batter", out_dir)
                results["bust_batter"] = bust_result["cv_scores"]
            else:
                logger.warning("Insufficient bust labels for batters")
        except Exception as e:
            logger.error(f"Failed to train batter bust model: {e}")

        # Regression model
        try:
            # Get most recent full season stats for current and next
            latest_train_season = max(train_seasons)
            bat_current = batting_df[batting_df["season"] == latest_train_season]
            reg_targets = build_regression_targets(
                bat_features, bat_current, bat_target, "batter"
            )
            reg_result = train_regression_model(bat_features, reg_targets, "batter")
            save_model(reg_result, "regression_batter", out_dir)
            results["regression_batter"] = reg_result["cv_scores"]
        except Exception as e:
            logger.error(f"Failed to train batter regression model: {e}")

    # --- Train pitcher models ---
    if not pit_features.empty and not pit_target.empty:
        try:
            sleeper_labels = build_sleeper_labels(
                pit_features, pit_target, cost_column="adp", value_column="war"
            )
            if sleeper_labels.sum() > 5:
                sleeper_result = train_sleeper_model(pit_features, sleeper_labels, "pitcher")
                save_model(sleeper_result, "sleeper_pitcher", out_dir)
                results["sleeper_pitcher"] = sleeper_result["cv_scores"]
        except Exception as e:
            logger.error(f"Failed to train pitcher sleeper model: {e}")

        try:
            bust_labels = build_bust_labels(
                pit_features, pit_target, cost_column="adp", value_column="war"
            )
            if bust_labels.sum() > 5:
                bust_result = train_bust_model(pit_features, bust_labels, "pitcher")
                save_model(bust_result, "bust_pitcher", out_dir)
                results["bust_pitcher"] = bust_result["cv_scores"]
        except Exception as e:
            logger.error(f"Failed to train pitcher bust model: {e}")

        try:
            latest_train_season = max(train_seasons)
            pit_current = pitching_df[pitching_df["season"] == latest_train_season]
            reg_targets = build_regression_targets(
                pit_features, pit_current, pit_target, "pitcher"
            )
            reg_result = train_regression_model(pit_features, reg_targets, "pitcher")
            save_model(reg_result, "regression_pitcher", out_dir)
            results["regression_pitcher"] = reg_result["cv_scores"]
        except Exception as e:
            logger.error(f"Failed to train pitcher regression model: {e}")

    logger.info(f"Training complete. Results: {results}")
    return results


async def main():
    """Load data from the database and train all models."""
    from backend.app.db.base import Base
    from backend.app.db.session import engine, async_session_factory
    from backend.app.models import BattingSeason, PitchingSeason, Player

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    logger.info("=== Fantasy Baseball Sleeper Finder: Training Pipeline ===")

    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Load season data from database
    logger.info("Loading season data from database...")
    async with async_session_factory() as session:
        # Batting seasons
        bat_cols = [c for c in BattingSeason.__table__.columns]
        result = await session.execute(select(*bat_cols))
        batting_df = pd.DataFrame(result.all(), columns=[c.name for c in bat_cols])

        # Pitching seasons
        pit_cols = [c for c in PitchingSeason.__table__.columns]
        result = await session.execute(select(*pit_cols))
        pitching_df = pd.DataFrame(result.all(), columns=[c.name for c in pit_cols])

        # Players (for age estimation)
        result = await session.execute(
            select(Player.id, Player.birth_date)
        )
        players_rows = result.all()

    logger.info(
        f"Loaded {len(batting_df)} batting rows, {len(pitching_df)} pitching rows"
    )

    if batting_df.empty and pitching_df.empty:
        logger.error("No season data found. Run seed_database.py first.")
        return

    # Estimate player ages
    logger.info("Estimating player ages...")
    today = date.today()
    player_ages: dict[int, int] = {}

    for pid, bd in players_rows:
        if pd.notna(bd) and bd is not None:
            try:
                if isinstance(bd, str):
                    bd = datetime.strptime(bd, "%Y-%m-%d").date()
                player_ages[pid] = today.year - bd.year - (
                    (today.month, today.day) < (bd.month, bd.day)
                )
            except (ValueError, TypeError):
                pass

    # Fallback for players without birth_date
    all_player_ids = set()
    if not batting_df.empty:
        all_player_ids.update(batting_df["player_id"].unique())
    if not pitching_df.empty:
        all_player_ids.update(pitching_df["player_id"].unique())

    for pid in all_player_ids:
        if pid in player_ages:
            continue
        earliest = None
        if not batting_df.empty:
            s = batting_df.loc[batting_df["player_id"] == pid, "season"]
            if len(s) > 0:
                earliest = s.min()
        if not pitching_df.empty:
            s = pitching_df.loc[pitching_df["player_id"] == pid, "season"]
            if len(s) > 0:
                val = s.min()
                if earliest is None or val < earliest:
                    earliest = val
        if earliest is not None:
            player_ages[pid] = 24 + (today.year - int(earliest))
        else:
            player_ages[pid] = 28

    logger.info(f"Estimated ages for {len(player_ages)} players")

    # Train all models
    results = train_all_models(batting_df, pitching_df, player_ages)

    if results:
        logger.info("=== Training Summary ===")
        for model_name, cv_scores in results.items():
            logger.info(f"  {model_name}: {cv_scores}")
        logger.info(
            f"Model artifacts saved to {ARTIFACTS_DIR}. "
            "Re-run inference to use trained models: python -m scripts.run_inference"
        )
    else:
        logger.error(
            "No models were trained. Check that you have at least 2 seasons of data."
        )


if __name__ == "__main__":
    asyncio.run(main())

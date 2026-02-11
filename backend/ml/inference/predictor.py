"""Unified inference pipeline — loads models and generates all predictions.

Orchestrates the full prediction flow: features → model scores → consistency →
improvement → value score → SHAP explanations.
"""

import logging
from pathlib import Path

import joblib
import pandas as pd

from backend.ml.inference.explainer import explain_predictions
from backend.ml.models.bust_model import predict_bust_scores
from backend.ml.models.consistency_model import (
    calculate_batter_consistency,
    calculate_pitcher_consistency,
)
from backend.ml.models.improvement_model import (
    calculate_batter_improvement,
    calculate_pitcher_improvement,
)
from backend.ml.models.regression_model import predict_regression
from backend.ml.models.sleeper_model import predict_sleeper_scores
from backend.ml.models.value_model import calculate_ai_value_scores

logger = logging.getLogger(__name__)

ARTIFACTS_DIR = Path(__file__).parent.parent / "artifacts"


class Predictor:
    """Loads trained models and generates all scores for players."""

    def __init__(self, artifacts_dir: Path | None = None):
        self.artifacts_dir = artifacts_dir or ARTIFACTS_DIR
        self.models = {}

    def load_models(self) -> None:
        """Load all serialized model artifacts from disk."""
        model_files = {
            "sleeper_batter": "sleeper_batter.joblib",
            "sleeper_pitcher": "sleeper_pitcher.joblib",
            "bust_batter": "bust_batter.joblib",
            "bust_pitcher": "bust_pitcher.joblib",
            "regression_batter": "regression_batter.joblib",
            "regression_pitcher": "regression_pitcher.joblib",
        }

        for name, filename in model_files.items():
            path = self.artifacts_dir / filename
            if path.exists():
                self.models[name] = joblib.load(path)
                logger.info(f"Loaded model: {name}")
            else:
                logger.warning(f"Model artifact not found: {path}")

    def predict_all(
        self,
        batter_features: pd.DataFrame,
        pitcher_features: pd.DataFrame,
        batting_seasons: pd.DataFrame,
        pitching_seasons: pd.DataFrame,
        player_ages: dict[int, int],
        batter_auction_values: pd.DataFrame | None = None,
        pitcher_auction_values: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        """Run the full inference pipeline for all players.

        Args:
            batter_features: Engineered batter feature matrix.
            pitcher_features: Engineered pitcher feature matrix.
            batting_seasons: Raw batting season data (for consistency/improvement).
            pitching_seasons: Raw pitching season data (for consistency/improvement).
            player_ages: Dict mapping player_id -> age.
            batter_auction_values: DataFrame with player_id, auction_value.
            pitcher_auction_values: DataFrame with player_id, auction_value.

        Returns:
            DataFrame with all scores for all players.
        """
        all_scores = []

        # --- Batter predictions ---
        if not batter_features.empty:
            batter_scores = self._predict_player_type(
                batter_features, batting_seasons, player_ages,
                batter_auction_values, "batter",
            )
            all_scores.append(batter_scores)

        # --- Pitcher predictions ---
        if not pitcher_features.empty:
            pitcher_scores = self._predict_player_type(
                pitcher_features, pitching_seasons, player_ages,
                pitcher_auction_values, "pitcher",
            )
            all_scores.append(pitcher_scores)

        if not all_scores:
            return pd.DataFrame()

        combined = pd.concat(all_scores, ignore_index=True)
        logger.info(f"Generated predictions for {len(combined)} total players")
        return combined

    def _predict_player_type(
        self,
        features: pd.DataFrame,
        season_data: pd.DataFrame,
        player_ages: dict[int, int],
        auction_values: pd.DataFrame | None,
        player_type: str,
    ) -> pd.DataFrame:
        """Generate all scores for one player type (batter or pitcher)."""
        scores = features[["player_id"]].copy()

        # Sleeper scores
        sleeper_key = f"sleeper_{player_type}"
        if sleeper_key in self.models:
            sleeper_preds = predict_sleeper_scores(self.models[sleeper_key], features)
            scores = scores.merge(sleeper_preds, on="player_id", how="left")

            # SHAP explanations for sleeper model
            shap_results = explain_predictions(self.models[sleeper_key], features, top_n=3)
            shap_map = {r["player_id"]: r["shap_features"] for r in shap_results}
            scores["sleeper_shap"] = scores["player_id"].map(shap_map)
        else:
            scores["sleeper_score"] = 50.0
            scores["sleeper_shap"] = None

        # Bust scores
        bust_key = f"bust_{player_type}"
        if bust_key in self.models:
            bust_preds = predict_bust_scores(self.models[bust_key], features)
            scores = scores.merge(bust_preds, on="player_id", how="left")

            shap_results = explain_predictions(self.models[bust_key], features, top_n=3)
            shap_map = {r["player_id"]: r["shap_features"] for r in shap_results}
            scores["bust_shap"] = scores["player_id"].map(shap_map)
        else:
            scores["bust_score"] = 50.0
            scores["bust_shap"] = None

        # Regression predictions
        reg_key = f"regression_{player_type}"
        if reg_key in self.models:
            reg_preds = predict_regression(self.models[reg_key], features)
            scores = scores.merge(reg_preds, on="player_id", how="left")
        else:
            scores["regression_direction"] = 0.0
            scores["regression_magnitude"] = 0.0

        # Consistency scores (statistical, not ML)
        if player_type == "batter":
            consistency = calculate_batter_consistency(season_data)
        else:
            consistency = calculate_pitcher_consistency(season_data)
        if not consistency.empty:
            scores = scores.merge(
                consistency[["player_id", "consistency_score", "stat_consistency_breakdown"]],
                on="player_id", how="left",
            )
        if "consistency_score" not in scores.columns:
            scores["consistency_score"] = None
            scores["stat_consistency_breakdown"] = None

        # Improvement scores (statistical, not ML)
        if player_type == "batter":
            improvement = calculate_batter_improvement(season_data, player_ages)
        else:
            improvement = calculate_pitcher_improvement(season_data, player_ages)
        if not improvement.empty:
            scores = scores.merge(
                improvement[["player_id", "improvement_score", "stat_improvement_breakdown"]],
                on="player_id", how="left",
            )
        if "improvement_score" not in scores.columns:
            scores["improvement_score"] = None
            scores["stat_improvement_breakdown"] = None

        # Merge auction values if provided
        if auction_values is not None and not auction_values.empty:
            auction_cols = ["player_id", "auction_value"]
            if "dynasty_value" in auction_values.columns:
                auction_cols.append("dynasty_value")
            if "surplus_value" in auction_values.columns:
                auction_cols.append("surplus_value")
            scores = scores.merge(
                auction_values[auction_cols], on="player_id", how="left",
            )

        # Fill defaults
        for col in ["auction_value", "dynasty_value", "surplus_value"]:
            if col not in scores.columns:
                scores[col] = 0.0

        # Composite AI Value Score
        player_types = {pid: player_type for pid in scores["player_id"]}
        value_scores = calculate_ai_value_scores(scores, player_ages, player_types)
        scores = scores.merge(
            value_scores[["player_id", "ai_value_score", "value_components"]],
            on="player_id", how="left",
        )

        # Combine SHAP explanations
        scores["shap_explanations"] = scores.apply(
            lambda r: {
                "sleeper": r.get("sleeper_shap") or [],
                "bust": r.get("bust_shap") or [],
            },
            axis=1,
        )
        scores = scores.drop(columns=["sleeper_shap", "bust_shap"], errors="ignore")

        scores["player_type"] = player_type
        return scores


def save_model(model_result: dict, name: str, artifacts_dir: Path | None = None) -> Path:
    """Save a trained model to disk.

    Args:
        model_result: Dict from model training (must include 'model' or 'lgb_model'+'xgb_model').
        name: Model name (e.g., "sleeper_batter").
        artifacts_dir: Directory to save to.

    Returns:
        Path to saved artifact.
    """
    out_dir = artifacts_dir or ARTIFACTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.joblib"
    joblib.dump(model_result, path)
    logger.info(f"Saved model artifact: {path}")
    return path

"""Sleeper detection model — LightGBM + XGBoost ensemble.

Identifies players whose underlying quality (Statcast, expected stats) significantly
exceeds their surface stats or auction cost. In dynasty context, also flags young
players whose long-term trajectory is underpriced.

Training target: binary classification. "Sleeper" = player whose auction cost was
in the bottom 60% but finished in the top 40% by fantasy value.
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import TimeSeriesSplit

logger = logging.getLogger(__name__)

FEATURE_COLUMNS = [
    # Differential features (most important)
    "woba_minus_xwoba", "ba_minus_xba", "slg_minus_xslg", "babip_minus_league",
    # Trend features
    "barrel_pct_yoy_delta", "hard_hit_pct_yoy_delta", "k_pct_yoy_delta",
    "bb_pct_yoy_delta", "avg_exit_velocity_yoy_delta",
    "barrel_pct_3yr_trend", "k_pct_3yr_trend", "bb_pct_3yr_trend",
    # Statcast quality
    "latest_barrel_pct", "latest_hard_hit_pct", "latest_avg_exit_velocity",
    "latest_xwoba", "latest_sprint_speed",
    # Plate discipline
    "latest_k_pct", "latest_bb_pct",
    # Value/context
    "latest_woba", "latest_iso", "latest_war",
    # Age/trajectory
    "age", "years_from_peak", "age_bucket", "pre_peak",
    # Playing time
    "pa_yoy_delta", "pa_latest",
    "seasons_available",
]

PITCHER_FEATURE_COLUMNS = [
    "era_minus_fip", "era_minus_xera", "fip_minus_xfip",
    "babip_minus_league", "lob_pct_minus_league", "hr_fb_pct_minus_league",
    "k_pct_yoy_delta", "bb_pct_yoy_delta", "k_bb_pct_yoy_delta",
    "swstr_pct_yoy_delta", "csw_pct_yoy_delta",
    "k_pct_3yr_trend", "bb_pct_3yr_trend", "k_bb_pct_3yr_trend",
    "latest_k_pct", "latest_bb_pct", "latest_k_bb_pct",
    "latest_swstr_pct", "latest_csw_pct",
    "latest_era", "latest_fip", "latest_siera", "latest_xera",
    "latest_whip", "latest_war", "latest_stuff_plus",
    "latest_barrel_pct_against", "latest_hard_hit_pct_against",
    "age", "years_from_peak", "age_bucket", "pre_peak",
    "is_starter", "ip_latest", "ip_yoy_delta",
    "seasons_available",
]


def build_sleeper_labels(
    features_df: pd.DataFrame,
    next_season_values: pd.DataFrame,
    cost_column: str = "adp",
    value_column: str = "war",
) -> pd.Series:
    """Construct binary sleeper labels from historical data.

    A sleeper = player whose pre-season cost was in the bottom 60% of rostered
    players but who finished in the top 40% by fantasy value.

    Args:
        features_df: Feature matrix with player_id column.
        next_season_values: DataFrame with player_id and actual next-season performance.
        cost_column: Column representing pre-season cost/ADP.
        value_column: Column representing actual production.

    Returns:
        Binary Series aligned to features_df index.
    """
    merged = features_df[["player_id"]].merge(
        next_season_values[["player_id", cost_column, value_column]],
        on="player_id",
        how="left",
    )

    cost_rank_pct = merged[cost_column].rank(pct=True, ascending=True)
    value_rank_pct = merged[value_column].rank(pct=True, ascending=False)

    # Bottom 60% by cost AND top 40% by value
    labels = ((cost_rank_pct <= 0.60) & (value_rank_pct <= 0.40)).astype(int)
    return labels


def train_sleeper_model(
    features_df: pd.DataFrame,
    labels: pd.Series,
    player_type: str = "batter",
) -> dict:
    """Train a LightGBM + XGBoost ensemble for sleeper detection.

    Args:
        features_df: Feature matrix.
        labels: Binary sleeper labels.
        player_type: "batter" or "pitcher" — determines feature set.

    Returns:
        Dict with 'model', 'feature_columns', 'cv_scores'.
    """
    import lightgbm as lgb
    import xgboost as xgb
    from sklearn.ensemble import VotingClassifier
    from sklearn.metrics import f1_score, precision_score, recall_score

    feature_cols = FEATURE_COLUMNS if player_type == "batter" else PITCHER_FEATURE_COLUMNS
    available_cols = [c for c in feature_cols if c in features_df.columns]

    X = features_df[available_cols].fillna(0).values
    y = labels.values

    # Class weight to handle imbalance (~5-10% sleepers)
    pos_weight = max(1.0, (y == 0).sum() / max((y == 1).sum(), 1))

    lgb_model = lgb.LGBMClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        num_leaves=31,
        scale_pos_weight=pos_weight,
        min_child_samples=10,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbose=-1,
    )

    xgb_model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        scale_pos_weight=pos_weight,
        min_child_weight=5,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        eval_metric="logloss",
        verbosity=0,
    )

    ensemble = VotingClassifier(
        estimators=[("lgb", lgb_model), ("xgb", xgb_model)],
        voting="soft",
    )

    # Time-series cross-validation
    tscv = TimeSeriesSplit(n_splits=3)
    cv_scores = {"f1": [], "precision": [], "recall": []}

    for train_idx, val_idx in tscv.split(X):
        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]

        ensemble.fit(X_train, y_train)
        preds = ensemble.predict(X_val)

        cv_scores["f1"].append(f1_score(y_val, preds, zero_division=0))
        cv_scores["precision"].append(precision_score(y_val, preds, zero_division=0))
        cv_scores["recall"].append(recall_score(y_val, preds, zero_division=0))

    # Final model: train on all data with calibration
    ensemble.fit(X, y)
    calibrated = CalibratedClassifierCV(ensemble, cv=3, method="isotonic")
    calibrated.fit(X, y)

    avg_scores = {k: round(np.mean(v), 4) for k, v in cv_scores.items()}
    logger.info(f"Sleeper model ({player_type}) CV scores: {avg_scores}")

    return {
        "model": calibrated,
        "feature_columns": available_cols,
        "cv_scores": avg_scores,
    }


def predict_sleeper_scores(
    model_result: dict,
    features_df: pd.DataFrame,
) -> pd.DataFrame:
    """Generate sleeper scores (0-100) for all players.

    Args:
        model_result: Dict from train_sleeper_model.
        features_df: Feature matrix with player_id column.

    Returns:
        DataFrame with player_id and sleeper_score (0-100).
    """
    feature_cols = model_result["feature_columns"]
    model = model_result["model"]

    X = features_df[feature_cols].fillna(0).values
    probas = model.predict_proba(X)[:, 1]

    result = pd.DataFrame({
        "player_id": features_df["player_id"].values,
        "sleeper_score": (probas * 100).round(1),
    })
    return result

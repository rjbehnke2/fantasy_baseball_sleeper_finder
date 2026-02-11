"""Bust detection model — LightGBM + XGBoost ensemble.

Flags players whose surface stats are propped up by unsustainable luck, making
them likely to disappoint relative to their auction cost. In dynasty, also flags
aging players whose decline is being underpriced.

Training target: binary classification. "Bust" = player whose auction cost was
in the top 30% but finished outside the top 60% by fantasy value.
"""

import logging

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import TimeSeriesSplit

logger = logging.getLogger(__name__)

BATTER_FEATURE_COLUMNS = [
    # Luck indicators (most important for bust detection)
    "woba_minus_xwoba", "ba_minus_xba", "slg_minus_xslg", "babip_minus_league",
    # Decline signals
    "barrel_pct_yoy_delta", "hard_hit_pct_yoy_delta", "k_pct_yoy_delta",
    "bb_pct_yoy_delta", "avg_exit_velocity_yoy_delta",
    "barrel_pct_3yr_trend", "k_pct_3yr_trend",
    # Current quality
    "latest_barrel_pct", "latest_hard_hit_pct", "latest_avg_exit_velocity",
    "latest_xwoba", "latest_woba", "latest_babip",
    "latest_k_pct", "latest_bb_pct",
    "latest_war",
    # Age (older = higher bust risk)
    "age", "years_from_peak", "age_bucket",
    # Playing time stability
    "pa_yoy_delta", "pa_latest",
    "seasons_available",
]

PITCHER_FEATURE_COLUMNS = [
    # Luck indicators
    "era_minus_fip", "era_minus_xera", "fip_minus_xfip",
    "babip_minus_league", "lob_pct_minus_league", "hr_fb_pct_minus_league",
    # Decline signals
    "k_pct_yoy_delta", "bb_pct_yoy_delta", "k_bb_pct_yoy_delta",
    "swstr_pct_yoy_delta", "csw_pct_yoy_delta",
    "k_pct_3yr_trend", "bb_pct_3yr_trend",
    # Current quality
    "latest_k_pct", "latest_bb_pct", "latest_k_bb_pct",
    "latest_era", "latest_fip", "latest_siera", "latest_xera",
    "latest_whip", "latest_war",
    "latest_barrel_pct_against", "latest_hard_hit_pct_against",
    "latest_lob_pct", "latest_hr_fb_pct",
    # Age
    "age", "years_from_peak", "age_bucket",
    # Role stability
    "is_starter", "ip_latest", "ip_yoy_delta",
    "seasons_available",
]


def build_bust_labels(
    features_df: pd.DataFrame,
    next_season_values: pd.DataFrame,
    cost_column: str = "adp",
    value_column: str = "war",
) -> pd.Series:
    """Construct binary bust labels from historical data.

    A bust = player whose pre-season cost was in the top 30% but finished
    outside the top 60% by fantasy value (or had a major injury season).

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

    cost_rank_pct = merged[cost_column].rank(pct=True, ascending=False)
    value_rank_pct = merged[value_column].rank(pct=True, ascending=False)

    # Top 30% by cost AND finished outside top 60% by value
    labels = ((cost_rank_pct <= 0.30) & (value_rank_pct > 0.60)).astype(int)
    return labels


def train_bust_model(
    features_df: pd.DataFrame,
    labels: pd.Series,
    player_type: str = "batter",
) -> dict:
    """Train a LightGBM + XGBoost ensemble for bust detection.

    Args:
        features_df: Feature matrix.
        labels: Binary bust labels.
        player_type: "batter" or "pitcher".

    Returns:
        Dict with 'model', 'feature_columns', 'cv_scores'.
    """
    import lightgbm as lgb
    import xgboost as xgb
    from sklearn.ensemble import VotingClassifier
    from sklearn.metrics import f1_score, precision_score, recall_score

    feature_cols = (
        BATTER_FEATURE_COLUMNS if player_type == "batter" else PITCHER_FEATURE_COLUMNS
    )
    available_cols = [c for c in feature_cols if c in features_df.columns]

    X = features_df[available_cols].fillna(0).values
    y = labels.values

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

    ensemble.fit(X, y)
    calibrated = CalibratedClassifierCV(ensemble, cv=3, method="isotonic")
    calibrated.fit(X, y)

    avg_scores = {k: round(np.mean(v), 4) for k, v in cv_scores.items()}
    logger.info(f"Bust model ({player_type}) CV scores: {avg_scores}")

    return {
        "model": calibrated,
        "feature_columns": available_cols,
        "cv_scores": avg_scores,
    }


def predict_bust_scores(
    model_result: dict,
    features_df: pd.DataFrame,
) -> pd.DataFrame:
    """Generate bust scores (0-100) for all players.

    Args:
        model_result: Dict from train_bust_model.
        features_df: Feature matrix with player_id column.

    Returns:
        DataFrame with player_id and bust_score (0-100).
    """
    feature_cols = model_result["feature_columns"]
    model = model_result["model"]

    X = features_df[feature_cols].fillna(0).values
    probas = model.predict_proba(X)[:, 1]

    return pd.DataFrame({
        "player_id": features_df["player_id"].values,
        "bust_score": (probas * 100).round(1),
    })

"""Regression direction model — XGBoost + LightGBM regressor ensemble.

Predicts whether a player will improve or decline, and by how much.

Training target: regression. Target = next_season_woba - current_season_woba (batters)
or current_season_fip - next_season_fip (pitchers, inverted for unified "improvement").
"""

import logging

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

logger = logging.getLogger(__name__)

BATTER_FEATURE_COLUMNS = [
    "woba_minus_xwoba", "ba_minus_xba", "slg_minus_xslg", "babip_minus_league",
    "barrel_pct_yoy_delta", "hard_hit_pct_yoy_delta", "k_pct_yoy_delta",
    "bb_pct_yoy_delta", "avg_exit_velocity_yoy_delta",
    "barrel_pct_3yr_trend", "k_pct_3yr_trend", "bb_pct_3yr_trend",
    "woba_3yr_trend", "xwoba_3yr_trend", "iso_3yr_trend",
    "latest_barrel_pct", "latest_hard_hit_pct", "latest_avg_exit_velocity",
    "latest_xwoba", "latest_woba", "latest_babip",
    "latest_k_pct", "latest_bb_pct",
    "latest_iso", "latest_war",
    "age", "years_from_peak", "age_bucket", "pre_peak",
    "pa_yoy_delta", "pa_latest",
    "seasons_available",
]

PITCHER_FEATURE_COLUMNS = [
    "era_minus_fip", "era_minus_xera", "fip_minus_xfip",
    "babip_minus_league", "lob_pct_minus_league", "hr_fb_pct_minus_league",
    "k_pct_yoy_delta", "bb_pct_yoy_delta", "k_bb_pct_yoy_delta",
    "swstr_pct_yoy_delta", "csw_pct_yoy_delta",
    "k_pct_3yr_trend", "bb_pct_3yr_trend", "k_bb_pct_3yr_trend",
    "era_3yr_trend", "fip_3yr_trend", "siera_3yr_trend",
    "latest_k_pct", "latest_bb_pct", "latest_k_bb_pct",
    "latest_swstr_pct", "latest_csw_pct",
    "latest_era", "latest_fip", "latest_siera", "latest_xera",
    "latest_whip", "latest_war",
    "latest_barrel_pct_against", "latest_hard_hit_pct_against",
    "latest_lob_pct", "latest_hr_fb_pct", "latest_stuff_plus",
    "age", "years_from_peak", "age_bucket", "pre_peak",
    "is_starter", "ip_latest", "ip_yoy_delta",
    "seasons_available",
]


def build_regression_targets(
    features_df: pd.DataFrame,
    current_season_stats: pd.DataFrame,
    next_season_stats: pd.DataFrame,
    player_type: str = "batter",
) -> pd.Series:
    """Build regression targets from consecutive season data.

    For batters: next_woba - current_woba (positive = improved)
    For pitchers: current_fip - next_fip (positive = improved, since lower FIP is better)

    Args:
        features_df: Feature matrix with player_id column.
        current_season_stats: Stats for the feature season.
        next_season_stats: Stats for the target season.
        player_type: "batter" or "pitcher".

    Returns:
        Float series of regression targets aligned to features_df.
    """
    if player_type == "batter":
        current_stat = "woba"
        next_stat = "woba"
        invert = False
    else:
        current_stat = "fip"
        next_stat = "fip"
        invert = True

    merged = features_df[["player_id"]].merge(
        current_season_stats[["player_id", current_stat]].rename(
            columns={current_stat: "current_val"}
        ),
        on="player_id",
        how="left",
    ).merge(
        next_season_stats[["player_id", next_stat]].rename(
            columns={next_stat: "next_val"}
        ),
        on="player_id",
        how="left",
    )

    if invert:
        targets = merged["current_val"] - merged["next_val"]
    else:
        targets = merged["next_val"] - merged["current_val"]

    return targets


def train_regression_model(
    features_df: pd.DataFrame,
    targets: pd.Series,
    player_type: str = "batter",
) -> dict:
    """Train an XGBoost + LightGBM ensemble for regression direction prediction.

    Args:
        features_df: Feature matrix.
        targets: Continuous regression targets.
        player_type: "batter" or "pitcher".

    Returns:
        Dict with 'lgb_model', 'xgb_model', 'feature_columns', 'cv_scores'.
    """
    import lightgbm as lgb
    import xgboost as xgb
    from sklearn.metrics import mean_absolute_error

    feature_cols = (
        BATTER_FEATURE_COLUMNS if player_type == "batter" else PITCHER_FEATURE_COLUMNS
    )
    available_cols = [c for c in feature_cols if c in features_df.columns]

    # Drop rows with missing targets
    mask = targets.notna()
    X = features_df.loc[mask, available_cols].fillna(0).values
    y = targets[mask].values

    if len(y) < 20:
        logger.warning(f"Insufficient data for regression model ({len(y)} rows)")
        return {"lgb_model": None, "xgb_model": None, "feature_columns": available_cols,
                "cv_scores": {}}

    lgb_model = lgb.LGBMRegressor(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        num_leaves=31,
        min_child_samples=10,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbose=-1,
    )

    xgb_model = xgb.XGBRegressor(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        min_child_weight=5,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbosity=0,
    )

    tscv = TimeSeriesSplit(n_splits=3)
    cv_scores = {"mae": [], "directional_accuracy": []}

    for train_idx, val_idx in tscv.split(X):
        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]

        lgb_model.fit(X_train, y_train)
        xgb_model.fit(X_train, y_train)

        preds = (lgb_model.predict(X_val) + xgb_model.predict(X_val)) / 2

        cv_scores["mae"].append(mean_absolute_error(y_val, preds))
        # Directional accuracy: did we correctly predict improve vs. decline?
        if len(y_val) > 0:
            direction_correct = np.mean(np.sign(preds) == np.sign(y_val))
            cv_scores["directional_accuracy"].append(direction_correct)

    # Train final models on all data
    lgb_model.fit(X, y)
    xgb_model.fit(X, y)

    avg_scores = {k: round(np.mean(v), 4) for k, v in cv_scores.items() if v}
    logger.info(f"Regression model ({player_type}) CV scores: {avg_scores}")

    return {
        "lgb_model": lgb_model,
        "xgb_model": xgb_model,
        "feature_columns": available_cols,
        "cv_scores": avg_scores,
    }


def predict_regression(
    model_result: dict,
    features_df: pd.DataFrame,
) -> pd.DataFrame:
    """Generate regression predictions for all players.

    Args:
        model_result: Dict from train_regression_model.
        features_df: Feature matrix with player_id column.

    Returns:
        DataFrame with player_id, regression_direction (signed float),
        regression_magnitude (absolute value).
    """
    feature_cols = model_result["feature_columns"]
    lgb_model = model_result["lgb_model"]
    xgb_model = model_result["xgb_model"]

    if lgb_model is None or xgb_model is None:
        return pd.DataFrame({
            "player_id": features_df["player_id"].values,
            "regression_direction": 0.0,
            "regression_magnitude": 0.0,
        })

    X = features_df[feature_cols].fillna(0).values
    lgb_preds = lgb_model.predict(X)
    xgb_preds = xgb_model.predict(X)
    ensemble_preds = (lgb_preds + xgb_preds) / 2

    return pd.DataFrame({
        "player_id": features_df["player_id"].values,
        "regression_direction": np.round(ensemble_preds, 4),
        "regression_magnitude": np.round(np.abs(ensemble_preds), 4),
    })

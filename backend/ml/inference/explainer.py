"""SHAP-based model explainability.

Generates per-player feature explanations showing which features drove each
model's prediction. Provides top-N most influential features for each score.
"""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def explain_predictions(
    model_result: dict,
    features_df: pd.DataFrame,
    top_n: int = 5,
) -> list[dict]:
    """Generate SHAP explanations for model predictions.

    Args:
        model_result: Dict with 'model' and 'feature_columns' from training.
        features_df: Feature matrix with player_id column.
        top_n: Number of top features to include per player.

    Returns:
        List of dicts with player_id and shap_features list.
    """
    try:
        import shap
    except ImportError:
        logger.warning("SHAP not available, returning empty explanations")
        return [{"player_id": pid, "shap_features": []}
                for pid in features_df["player_id"]]

    feature_cols = model_result["feature_columns"]
    model = model_result["model"]

    X = features_df[feature_cols].fillna(0)

    try:
        # Use TreeExplainer for tree-based models, fallback to KernelExplainer
        base_model = _extract_base_model(model)
        if base_model is not None:
            explainer = shap.TreeExplainer(base_model)
            shap_values = explainer.shap_values(X)
        else:
            # Sample background data for KernelExplainer
            background = shap.sample(X, min(50, len(X)))
            explainer = shap.KernelExplainer(model.predict_proba, background)
            shap_values = explainer.shap_values(X)

        # For binary classification, take the positive-class SHAP values
        if isinstance(shap_values, list) and len(shap_values) > 1:
            shap_values = shap_values[1]

        if isinstance(shap_values, np.ndarray):
            shap_array = shap_values
        else:
            shap_array = np.array(shap_values)

    except Exception as e:
        logger.warning(f"SHAP explanation failed: {e}")
        return [{"player_id": pid, "shap_features": []}
                for pid in features_df["player_id"]]

    explanations = []
    for i, pid in enumerate(features_df["player_id"]):
        player_shap = shap_array[i] if i < len(shap_array) else np.zeros(len(feature_cols))

        # Get top N features by absolute SHAP value
        top_indices = np.argsort(np.abs(player_shap))[-top_n:][::-1]
        top_features = []
        for idx in top_indices:
            if idx < len(feature_cols):
                feat_name = feature_cols[idx]
                shap_val = float(player_shap[idx])
                feat_val = float(X.iloc[i, idx]) if i < len(X) else 0
                top_features.append({
                    "feature": feat_name,
                    "shap_value": round(shap_val, 4),
                    "feature_value": round(feat_val, 4),
                    "direction": "positive" if shap_val > 0 else "negative",
                })

        explanations.append({
            "player_id": pid,
            "shap_features": top_features,
        })

    logger.info(f"Generated SHAP explanations for {len(explanations)} players")
    return explanations


def _extract_base_model(model):
    """Extract a tree-based model from a calibrated/voting classifier for TreeExplainer."""
    # CalibratedClassifierCV wraps the actual estimator
    if hasattr(model, "estimator"):
        inner = model.estimator
    elif hasattr(model, "calibrated_classifiers_"):
        # Get the first calibrated classifier's base estimator
        inner = model.calibrated_classifiers_[0].estimator
    else:
        inner = model

    # VotingClassifier: try to extract one of the base estimators
    if hasattr(inner, "estimators_"):
        for est in inner.estimators_:
            if hasattr(est, "booster_") or hasattr(est, "get_booster"):
                return est
    # Direct tree model
    if hasattr(inner, "booster_") or hasattr(inner, "get_booster"):
        return inner
    return None

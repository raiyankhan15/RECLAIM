"""
ml/evaluate.py - Model Evaluation & Performance Metrics
Computes MAE, RMSE, and R2 scores, residuals, and extracts interpretable feature importances.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Computes MAE, RMSE, and R2."""
    mae = float(mean_absolute_error(y_true, y_pred))
    mse = float(mean_squared_error(y_true, y_pred))
    rmse = float(np.sqrt(mse))
    r2 = float(r2_score(y_true, y_pred))
    return {
        "MAE": round(mae, 3),
        "RMSE": round(rmse, 3),
        "R2": round(r2, 3)
    }

def compute_residuals(y_true: np.ndarray, y_pred: np.ndarray) -> pd.DataFrame:
    """Computes residuals and percentage errors for diagnostic plotting."""
    residuals = y_true - y_pred
    return pd.DataFrame({
        "actual": y_true,
        "predicted": y_pred,
        "residual": residuals,
        "abs_error": np.abs(residuals)
    })

def extract_feature_importance(
    model: Any,
    feature_names: List[str]
) -> pd.DataFrame:
    """
    Extracts feature importances (for tree-based models) or absolute standardized
    coefficients (for linear models).
    """
    importances = []

    # Check for tree-based feature_importances_
    if hasattr(model, "feature_importances_"):
        raw_imp = model.feature_importances_
        for name, val in zip(feature_names, raw_imp):
            importances.append({"feature": name, "importance": float(val)})
    elif hasattr(model, "named_steps") and hasattr(model.named_steps.get("regressor", None), "feature_importances_"):
        raw_imp = model.named_steps["regressor"].feature_importances_
        for name, val in zip(feature_names, raw_imp):
            importances.append({"feature": name, "importance": float(val)})
    # Check for linear model coefficients
    elif hasattr(model, "coef_"):
        raw_coef = np.abs(model.coef_)
        total = np.sum(raw_coef) if np.sum(raw_coef) > 0 else 1.0
        normalized = raw_coef / total
        for name, val in zip(feature_names, normalized):
            importances.append({"feature": name, "importance": float(val)})
    elif hasattr(model, "named_steps") and hasattr(model.named_steps.get("regressor", None), "coef_"):
        raw_coef = np.abs(model.named_steps["regressor"].coef_)
        total = np.sum(raw_coef) if np.sum(raw_coef) > 0 else 1.0
        normalized = raw_coef / total
        for name, val in zip(feature_names, normalized):
            importances.append({"feature": name, "importance": float(val)})
    else:
        # Uniform fallback
        for name in feature_names:
            importances.append({"feature": name, "importance": 1.0 / len(feature_names)})

    df_imp = pd.DataFrame(importances)
    df_imp = df_imp.sort_values(by="importance", ascending=False).reset_index(drop=True)
    return df_imp


"""
ml/train.py - Supervised Regression Training Pipeline
Trains Linear Regression, Random Forest, and Gradient Boosting Regressors.
Performs leak-free evaluation, model comparison, feature importance analysis,
and joblib model persistence.
"""

import json
from datetime import datetime
from typing import Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np
import joblib

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor

from config import (
    FEATURE_COLS, TARGET_COL,
    LINEAR_MODEL_PATH, RF_MODEL_PATH, GBR_MODEL_PATH,
    MODEL_METADATA_PATH
)
from data.preprocessing import prepare_features, split_dataset
from ml.evaluate import compute_metrics, extract_feature_importance, compute_residuals

def get_model_definitions() -> Dict[str, Any]:
    """Returns uninstantiated or fresh model pipelines for training."""
    return {
        "Linear Regression": Pipeline([
            ("scaler", StandardScaler()),
            ("regressor", LinearRegression())
        ]),
        "Random Forest": RandomForestRegressor(
            n_estimators=120,
            max_depth=6,
            min_samples_split=4,
            min_samples_leaf=2,
            random_state=42
        ),
        "Gradient Boosting": GradientBoostingRegressor(
            n_estimators=120,
            learning_rate=0.08,
            max_depth=4,
            min_samples_split=4,
            random_state=42
        )
    }

def train_and_compare_models(
    df: pd.DataFrame,
    dataset_label: str = "Real Participant Records"
) -> Dict[str, Any]:
    """
    Full supervised training loop:
    1. Prepares leakage-free features
    2. Splits into train and test sets (group-aware when applicable)
    3. Trains Linear Regression, Random Forest, Gradient Boosting
    4. Evaluates MAE, RMSE, R2
    5. Persists models and writes metadata
    """
    if df is None or len(df) < 10:
        return {
            "success": False,
            "error": f"Insufficient records ({len(df) if df is not None else 0}). At least 10 records are required to train ML models."
        }

    try:
        X, y, groups = prepare_features(df)
        X_train, X_test, y_train, y_test = split_dataset(X, y, groups, test_size=0.2, random_state=42)

        models = get_model_definitions()
        results: Dict[str, Any] = {
            "dataset_label": dataset_label,
            "total_samples": len(df),
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "trained_at": datetime.now().isoformat(),
            "models": {},
            "best_model_name": None,
            "feature_names": FEATURE_COLS
        }

        best_rmse = float("inf")
        best_name = None

        # Train each model
        for name, model in models.items():
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            # Clip predictions to non-negative as CRC cannot be negative
            y_pred = np.clip(y_pred, 0.0, None)

            metrics = compute_metrics(y_test.values, y_pred)
            residuals_df = compute_residuals(y_test.values, y_pred)
            importances_df = extract_feature_importance(model, FEATURE_COLS)

            results["models"][name] = {
                "metrics": metrics,
                "feature_importance": importances_df.to_dict(orient="records"),
                "sample_predictions": residuals_df.head(10).to_dict(orient="records")
            }

            if metrics["RMSE"] < best_rmse:
                best_rmse = metrics["RMSE"]
                best_name = name

        results["best_model_name"] = best_name

        # Persist trained models to disk
        joblib.dump(models["Linear Regression"], LINEAR_MODEL_PATH)
        joblib.dump(models["Random Forest"], RF_MODEL_PATH)
        joblib.dump(models["Gradient Boosting"], GBR_MODEL_PATH)

        # Save metadata JSON
        with open(MODEL_METADATA_PATH, "w") as f:
            json.dump(results, f, indent=2)

        results["success"] = True
        return results

    except Exception as e:
        return {
            "success": False,
            "error": f"Model training failed: {str(e)}"
        }


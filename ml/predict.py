"""
ml/predict.py - Inference Engine for Context Recovery Cost (CRC)
Loads persisted models from joblib and delivers instant predictions,
multi-model comparisons, and cognitive resumption risk categorization.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
import joblib

from config import (
    FEATURE_COLS,
    LINEAR_MODEL_PATH, RF_MODEL_PATH, GBR_MODEL_PATH,
    MODEL_METADATA_PATH
)

def get_loaded_models() -> Dict[str, Any]:
    """Loads all available models from disk if they exist."""
    models = {}
    if LINEAR_MODEL_PATH.exists():
        try:
            models["Linear Regression"] = joblib.load(LINEAR_MODEL_PATH)
        except Exception:
            pass
    if RF_MODEL_PATH.exists():
        try:
            models["Random Forest"] = joblib.load(RF_MODEL_PATH)
        except Exception:
            pass
    if GBR_MODEL_PATH.exists():
        try:
            models["Gradient Boosting"] = joblib.load(GBR_MODEL_PATH)
        except Exception:
            pass
    return models

def get_model_metadata() -> Optional[Dict[str, Any]]:
    """Reads saved training metadata JSON."""
    if MODEL_METADATA_PATH.exists():
        try:
            with open(MODEL_METADATA_PATH, "r") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def categorize_overhead(predicted_seconds: float) -> Tuple[str, str, str]:
    """
    Categorizes predicted CRC into actionable operational risk tiers:
    Returns (Tier Name, CSS color, Description).
    """
    if predicted_seconds < 4.0:
        return "Minimal Resumption Lag", "#10B981", "Fast context recovery with minimal working memory disruption."
    elif predicted_seconds < 12.0:
        return "Moderate Overhead", "#F59E0B", "Noticeable mental recalibration required to resume original task goals."
    elif predicted_seconds < 25.0:
        return "High Cognitive Tax", "#EF4444", "Substantial goal-activation decay; significant latency before productive resumption."
    else:
        return "Severe Context Rupture", "#8B5CF6", "Complete working memory eviction; participant effectively re-starts mental problem representation."

def predict_crc(
    feature_dict: Dict[str, Any],
    selected_model_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes single-instance prediction across available models.
    """
    models = get_loaded_models()
    if not models:
        return {
            "success": False,
            "error": "No trained models found on disk. Please train models first using the Model Training page."
        }

    # Ensure switch density is calculated if missing
    if "switch_density" not in feature_dict or feature_dict["switch_density"] is None:
        approx_total_min = (
            float(feature_dict.get("baseline_duration", 30.0)) * 2 +
            float(feature_dict.get("interruption_duration", 30.0))
        ) / 60.0
        feature_dict["switch_density"] = float(feature_dict.get("switch_count", 2)) / max(0.05, approx_total_min)

    # Convert to DataFrame matching training feature columns
    try:
        input_row = {col: [float(feature_dict[col])] for col in FEATURE_COLS}
        input_df = pd.DataFrame(input_row)
    except KeyError as e:
        return {
            "success": False,
            "error": f"Missing input feature: {str(e)}"
        }

    metadata = get_model_metadata() or {}
    models_metadata = metadata.get("models", {})
    best_model_name = metadata.get("best_model_name", "Gradient Boosting")

    if not selected_model_name or selected_model_name not in models:
        selected_model_name = best_model_name if best_model_name in models else list(models.keys())[0]

    predictions_by_model = {}
    for name, model in models.items():
        try:
            pred = float(model.predict(input_df)[0])
            pred_clipped = max(0.0, round(pred, 2))
            rmse = models_metadata.get(name, {}).get("metrics", {}).get("RMSE", 2.5)
            ci_lower = max(0.0, round(pred_clipped - 1.96 * (rmse / 2.0), 2))
            ci_upper = round(pred_clipped + 1.96 * (rmse / 2.0), 2)
            predictions_by_model[name] = {
                "predicted_crc_seconds": pred_clipped,
                "ci_lower": ci_lower,
                "ci_upper": ci_upper,
                "rmse": rmse
            }
        except Exception as e:
            predictions_by_model[name] = {"error": str(e)}

    primary_pred = predictions_by_model.get(selected_model_name, {}).get("predicted_crc_seconds", 0.0)
    tier_name, tier_color, tier_desc = categorize_overhead(primary_pred)

    # Relative overhead compared to baseline
    baseline_time = float(feature_dict.get("baseline_duration", 30.0))
    time_overhead_pct = round((primary_pred / max(0.1, baseline_time)) * 100.0, 1)

    return {
        "success": True,
        "selected_model": selected_model_name,
        "predicted_crc_seconds": primary_pred,
        "time_overhead_percentage": time_overhead_pct,
        "risk_tier": tier_name,
        "risk_color": tier_color,
        "risk_description": tier_desc,
        "all_model_predictions": predictions_by_model,
        "dataset_trained_on": metadata.get("dataset_label", "Unknown Dataset")
    }


"""
data/preprocessing.py - Data Preprocessing & Leakage-Free Feature Engineering
Guarantees strict separation between pre-recovery features and post-recovery outcomes.
Provides group-aware train/test splitting to prevent participant-level data leakage.
"""

import pandas as pd
import numpy as np
from typing import Tuple, List, Optional
from sklearn.model_selection import train_test_split, GroupShuffleSplit
from sklearn.preprocessing import StandardScaler
from config import FEATURE_COLS, TARGET_COL

# Strictly forbidden variables that occur post-recovery
FORBIDDEN_POST_RECOVERY_COLS = {
    "recovery_duration",
    "recovery_accuracy",
    "crc_ratio",
    "accuracy_diff"
}

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans raw experiment dataframe:
    - Drops duplicates by session_id
    - Validates positive durations and valid accuracy bounds
    - Handles missing values via median imputation
    """
    if df.empty:
        return df

    cleaned = df.drop_duplicates(subset=["session_id"]).copy()

    # Numeric columns
    num_cols = [
        "baseline_duration", "baseline_accuracy", "interruption_duration",
        "interruption_accuracy", "switch_count", "switch_density",
        "crc_excess_time", "complexity_level"
    ]
    for col in num_cols:
        if col in cleaned.columns:
            cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")
            cleaned[col] = cleaned[col].fillna(cleaned[col].median() if not cleaned[col].isna().all() else 0.0)

    # Filter invalid bounds
    if "baseline_duration" in cleaned.columns:
        cleaned = cleaned[cleaned["baseline_duration"] >= 0]
    if "interruption_duration" in cleaned.columns:
        cleaned = cleaned[cleaned["interruption_duration"] >= 0]
    if "crc_excess_time" in cleaned.columns:
        cleaned = cleaned[cleaned["crc_excess_time"] >= 0]

    return cleaned

def prepare_features(
    df: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
    """
    Extracts features X, target y, and participant groups from cleaned DataFrame.
    Validates that NO post-recovery variables leak into X.
    """
    # Verify leakage prevention
    leaked = set(FEATURE_COLS).intersection(FORBIDDEN_POST_RECOVERY_COLS)
    if leaked:
        raise ValueError(f"CRITICAL DATA LEAKAGE: Forbidden post-recovery features in input: {leaked}")

    cleaned = clean_data(df)
    if cleaned.empty:
        raise ValueError("Cannot prepare features from an empty dataset.")

    # Ensure all required features are present
    missing_cols = [c for c in FEATURE_COLS if c not in cleaned.columns]
    if missing_cols:
        raise ValueError(f"Missing required feature columns: {missing_cols}")

    X = cleaned[FEATURE_COLS].copy()
    y = cleaned[TARGET_COL].copy()
    groups = cleaned["participant_id"].copy() if "participant_id" in cleaned.columns else pd.Series(range(len(cleaned)))

    return X, y, groups

def split_dataset(
    X: pd.DataFrame,
    y: pd.Series,
    groups: pd.Series,
    test_size: float = 0.2,
    random_state: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """
    Performs train/test split.
    Uses GroupShuffleSplit when unique participants are sufficient (>= 5) to test generalizability
    to unseen participants without participant-identity data leakage.
    Otherwise falls back to standard train_test_split.
    """
    n_unique_groups = groups.nunique()
    if n_unique_groups >= 6 and len(X) >= 20:
        gss = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
        train_idx, test_idx = next(gss.split(X, y, groups))
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )

    return X_train, X_test, y_train, y_test


"""
config.py - Central Configuration for ContextIQ Platform
Defines directory paths, model constants, cognitive experiment configurations,
and operational definitions for Context Recovery Cost (CRC).
"""

import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
DATABASE_DIR = BASE_DIR / "database"
MODELS_DIR = BASE_DIR / "models"
DATA_DIR = BASE_DIR / "data"
ASSETS_DIR = BASE_DIR / "assets"

# Ensure directories exist
DATABASE_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

# Cache directories (to avoid macOS sandbox permission warnings)
os.environ.setdefault("MPLCONFIGDIR", "/tmp/contextiq_mpl")
Path("/tmp/contextiq_mpl").mkdir(parents=True, exist_ok=True)

# Database
DB_PATH = DATABASE_DIR / "contextiq.db"

# Model Artifacts
LINEAR_MODEL_PATH = MODELS_DIR / "linear_regression.joblib"
RF_MODEL_PATH = MODELS_DIR / "random_forest.joblib"
GBR_MODEL_PATH = MODELS_DIR / "gradient_boosting.joblib"
PREPROCESSOR_PATH = MODELS_DIR / "preprocessor.joblib"
MODEL_METADATA_PATH = MODELS_DIR / "model_metadata.json"

# Experimental Research Proposal Conditions
COND_CONTROL = "CONTROL"
COND_SINGLE = "SINGLE_SWITCH"
COND_REPEATED = "REPEATED_SWITCH"
COND_COMPLEX = "HIGH_COMPLEXITY"

CONDITIONS_LABELS = {
    COND_CONTROL: "Condition A: Control (Uninterrupted)",
    COND_SINGLE: "Condition B: Single Switch",
    COND_REPEATED: "Condition C: Repeated Switch",
    COND_COMPLEX: "Condition D: High Complexity"
}

# Task Complexity Levels
COMPLEXITY_LEVELS = {
    "Easy": {
        "level": 1,
        "label": "Level 1: Easy",
        "description": "Basic single/double-digit arithmetic & direct sequential logic",
        "num_questions": 4,
        "time_target_seconds": 25.0
    },
    "Medium": {
        "level": 2,
        "label": "Level 2: Medium",
        "description": "Multi-step arithmetic, order-of-operations & intermediate pattern deduction",
        "num_questions": 4,
        "time_target_seconds": 45.0
    },
    "Difficult": {
        "level": 3,
        "label": "Level 3: Difficult",
        "description": "Nested algebraic operations, modular arithmetic & dual-rule logic puzzles",
        "num_questions": 4,
        "time_target_seconds": 70.0
    }
}

# Operational Definition of Context Recovery Cost (CRC)
CRC_OPERATIONAL_DEFINITION = (
    "CRC excess-time proxy = max(0, recovery_task_duration - baseline_task_duration). "
    "Note: This is an interaction-latency behavioral proxy and does NOT represent direct neuroimaging "
    "or neurocognitive measurement."
)

# Feature Names for Machine Learning (Strictly Leakage-Free Pre-Recovery Features)
FEATURE_COLS = [
    "complexity_level",
    "baseline_duration",
    "baseline_accuracy",
    "interruption_duration",
    "interruption_accuracy",
    "switch_count",
    "switch_density"
]

TARGET_COL = "crc_excess_time"

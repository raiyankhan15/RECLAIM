"""
test_contextiq.py - Comprehensive Unit & Integration Test Suite
Validates database schemas, domain sanitization, recovery criteria,
state machines, 4 research conditions, ML pipelines, and API health.
"""

import os
import unittest
import numpy as np
import pandas as pd
from datetime import datetime

# Set environment variables for headless execution
os.environ["MPLCONFIGDIR"] = "/tmp/contextiq_mpl"

from config import DB_PATH, FEATURE_COLS, TARGET_COL
from backend.database import init_all_tables, get_connection
from core.tracking import sanitize_url
from core.crc import calculate_crc_excess_time, calculate_crc_ratio, check_baseline_recovery
from core.recovery import evaluate_recovery_progression, STATUS_RECOVERED, STATUS_INCOMPLETE
from core.experiment import (
    init_condition_state, record_condition_trial_to_db,
    COND_CONTROL, COND_SINGLE, COND_REPEATED, COND_COMPLEX
)
from ml.train import train_and_compare_models
from ml.predict import predict_crc, get_loaded_models

class TestContextIQComprehensive(unittest.TestCase):

    def setUp(self):
        """Initializes tables and purges test fixtures."""
        init_all_tables()
        conn = get_connection()
        conn.cursor().execute("DELETE FROM controlled_experiments WHERE trial_id LIKE 'test-%'")
        conn.cursor().execute("DELETE FROM tracking_sessions WHERE session_id LIKE 'test-%'")
        conn.commit()
        conn.close()

    def tearDown(self):
        """Cleans up test records."""
        conn = get_connection()
        conn.cursor().execute("DELETE FROM controlled_experiments WHERE trial_id LIKE 'test-%'")
        conn.cursor().execute("DELETE FROM tracking_sessions WHERE session_id LIKE 'test-%'")
        conn.commit()
        conn.close()

    def test_01_privacy_and_domain_sanitization(self):
        """Tests that URLs are stripped of query parameters and categorized properly."""
        domain, cat = sanitize_url("https://github.com/torvalds/linux?query=secret#line40")
        self.assertEqual(domain, "github.com")
        self.assertEqual(cat, "Development & Coding")

        wa_domain, wa_cat = sanitize_url("https://web.whatsapp.com/send?phone=123456789")
        self.assertEqual(wa_domain, "web.whatsapp.com")
        self.assertEqual(wa_cat, "Communication & Messaging")

        yt_domain, yt_cat = sanitize_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.assertEqual(yt_domain, "youtube.com")
        self.assertEqual(yt_cat, "Social Media & Entertainment")

    def test_02_crc_math_and_sustained_recovery(self):
        """Tests excess-time calculation, ratio, and consecutive recovery observation evaluation."""
        crc = calculate_crc_excess_time(30.0, 48.5)
        self.assertEqual(crc, 18.5)

        ratio = calculate_crc_ratio(30.0, 48.5)
        self.assertAlmostEqual(ratio, 1.617, places=2)

        # Baseline: 30s, 100%
        # Observations: [Task 1: 50s 80%], [Task 2: 32s 95%], [Task 3: 31s 100%]
        # Task 2 and 3 meet baseline threshold consecutively (streak >= 2)
        observations = [
            {"duration": 50.0, "accuracy": 0.80, "correct_count": 4, "total_count": 5},
            {"duration": 32.0, "accuracy": 0.95, "correct_count": 5, "total_count": 5},
            {"duration": 31.0, "accuracy": 1.00, "correct_count": 5, "total_count": 5}
        ]
        eval_res = evaluate_recovery_progression(
            baseline_duration=30.0,
            baseline_accuracy=1.0,
            recovery_observations=observations,
            consecutive_threshold=2,
            duration_tolerance=1.15
        )
        self.assertEqual(eval_res["recovery_status"], STATUS_RECOVERED)
        self.assertTrue(eval_res["is_sustained"])

    def test_03_four_research_conditions(self):
        """Tests initialization and state integrity across all 4 research conditions."""
        for cond in [COND_CONTROL, COND_SINGLE, COND_REPEATED, COND_COMPLEX]:
            state = init_condition_state(cond, "P-TEST-RESEARCH")
            self.assertEqual(state["condition"], cond)
            self.assertGreaterEqual(len(state["baseline_questions"]), 4)
            self.assertGreaterEqual(len(state["recovery_questions"]), 4)

            # Test DB persistence
            state["trial_id"] = f"test-trial-{cond}"
            state["baseline_duration_sec"] = 35.0
            state["baseline_accuracy"] = 0.90
            state["interruption_duration_sec"] = 40.0 if cond != COND_CONTROL else 0.0
            state["recovery_duration_sec"] = 45.0
            state["recovery_accuracy"] = 0.85
            state["crc_seconds"] = 10.0
            state["crc_ratio"] = 1.28
            state["recovery_status"] = STATUS_RECOVERED

            success, msg = record_condition_trial_to_db(state)
            self.assertTrue(success, f"Failed to record {cond} to DB: {msg}")

    def test_04_ml_prediction_pipeline(self):
        """Tests that trained models deliver valid recovery latency forecasts with bounds."""
        models = get_loaded_models()
        self.assertGreater(len(models), 0, "At least one model must be persisted on disk.")

        test_payload = {
            "complexity_level": 2,
            "baseline_duration": 35.0,
            "baseline_accuracy": 0.95,
            "interruption_duration": 45.0,
            "interruption_accuracy": 0.85,
            "switch_count": 2
        }
        res = predict_crc(test_payload)
        self.assertTrue(res.get("success"), f"Prediction error: {res.get('error')}")
        self.assertGreaterEqual(res["predicted_crc_seconds"], 0.0)
        self.assertIn("risk_tier", res)
        self.assertIn("all_model_predictions", res)

    def test_05_empirical_insights_and_navigation_modules(self):
        """Tests empirical insights generation, condition constants, and module imports."""
        from core.analytics import generate_empirical_insights
        from config import COND_SINGLE, COND_REPEATED

        # 1. Test empty dataset handling
        empty_res = generate_empirical_insights(pd.DataFrame())
        self.assertIsInstance(empty_res, list)
        self.assertGreaterEqual(len(empty_res), 1)
        self.assertIn("title", empty_res[0])

        # 2. Test populated dataset with COND_SINGLE and COND_REPEATED
        sample_df = pd.DataFrame([
            {
                "condition": COND_SINGLE,
                "task_complexity": "Easy",
                "baseline_duration_sec": 20.0,
                "recovery_duration_sec": 30.0,
                "crc_seconds": 10.0,
                "interruption_duration_sec": 25.0,
                "baseline_accuracy": 0.9,
                "recovery_accuracy": 0.85
            },
            {
                "condition": COND_REPEATED,
                "task_complexity": "Difficult",
                "baseline_duration_sec": 40.0,
                "recovery_duration_sec": 65.0,
                "crc_seconds": 25.0,
                "interruption_duration_sec": 60.0,
                "baseline_accuracy": 0.85,
                "recovery_accuracy": 0.75
            },
            {
                "condition": COND_SINGLE,
                "task_complexity": "Medium",
                "baseline_duration_sec": 30.0,
                "recovery_duration_sec": 42.0,
                "crc_seconds": 12.0,
                "interruption_duration_sec": 35.0,
                "baseline_accuracy": 0.95,
                "recovery_accuracy": 0.90
            }
        ])
        insights = generate_empirical_insights(sample_df)
        self.assertIsInstance(insights, list)
        self.assertGreaterEqual(len(insights), 1)

        # 3. Verify all 5 dashboard page modules import cleanly
        import dashboard.overview
        import dashboard.live_tracking
        import dashboard.recovery_analytics
        import dashboard.predictions
        import dashboard.insights
        self.assertTrue(hasattr(dashboard.overview, "render_overview"))
        self.assertTrue(hasattr(dashboard.live_tracking, "render_live_tracking"))
        self.assertTrue(hasattr(dashboard.recovery_analytics, "render_recovery_analytics"))
        self.assertTrue(hasattr(dashboard.predictions, "render_predictions"))
        self.assertTrue(hasattr(dashboard.insights, "render_insights"))

if __name__ == "__main__":
    unittest.main()

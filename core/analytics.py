"""
core/analytics.py - Data-Backed Empirical Analytics & Rule-Based Research Insights
Extracts statistical patterns, complexity interactions, condition benchmarks,
and fragmentation penalties directly from empirical and experimental records.
Operates completely standalone without requiring external third-party LLM API keys.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List
from config import COND_CONTROL, COND_SINGLE, COND_REPEATED, COND_COMPLEX, CONDITIONS_LABELS
from backend.database import get_connection

def get_complete_analytics_dataset() -> pd.DataFrame:
    """Fetches all controlled experiment trials from SQLite."""
    conn = get_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM controlled_experiments ORDER BY timestamp DESC", conn)
        return df
    finally:
        conn.close()

def generate_empirical_insights(df: pd.DataFrame) -> List[Dict[str, str]]:
    """
    Analyzes collected empirical data and generates structured, evidence-based research insights.
    Guaranteed to run locally without external network dependencies or unhandled exceptions.
    """
    if df is None or df.empty or len(df) < 3:
        return [
            {
                "title": "Awaiting Additional Empirical Records",
                "finding": "The local database currently contains fewer than 3 experiment trials for comparative statistics.",
                "recommendation": "As participants complete trials, statistical comparisons across condition fragmentation and cognitive load will automatically populate here."
            }
        ]

    insights: List[Dict[str, str]] = []

    # 1. Condition Comparison: Single vs Repeated Switch (Fragmentation Effect)
    if "condition" in df.columns and "crc_seconds" in df.columns:
        cond_stats = df.groupby("condition")["crc_seconds"].mean()
        if COND_SINGLE in cond_stats and COND_REPEATED in cond_stats:
            single_crc = cond_stats[COND_SINGLE]
            repeated_crc = cond_stats[COND_REPEATED]
            if not pd.isna(single_crc) and not pd.isna(repeated_crc) and single_crc > 0:
                diff_pct = ((repeated_crc - single_crc) / single_crc) * 100.0
                insights.append({
                    "title": "Compounded Resumption Penalty of Repeated Switches",
                    "finding": f"Repeated task switches ({CONDITIONS_LABELS.get(COND_REPEATED, 'Repeated Switch')}) demonstrated an average Context Recovery Cost of {repeated_crc:.1f}s compared to {single_crc:.1f}s for single interruptions (+{diff_pct:.1f}% resumption latency).",
                    "recommendation": "Frequent micro-interruptions compound cognitive resumption delay. Grouping communication checks into discrete sessions substantially preserves working memory continuity."
                })

    # 2. Cognitive Load & Complexity Multiplier
    if "task_complexity" in df.columns and "crc_seconds" in df.columns:
        comp_stats = df.groupby("task_complexity")["crc_seconds"].mean()
        if "Difficult" in comp_stats and "Easy" in comp_stats:
            diff_crc = comp_stats["Difficult"]
            easy_crc = comp_stats["Easy"]
            if not pd.isna(diff_crc) and not pd.isna(easy_crc) and easy_crc > 0:
                ratio = diff_crc / max(0.1, easy_crc)
                insights.append({
                    "title": "Cognitive Load & Mental State Tree Fragility",
                    "finding": f"High-complexity tasks exhibited {ratio:.2f}x higher Context Recovery Cost than basic tasks ({diff_crc:.1f}s vs {easy_crc:.1f}s excess delay).",
                    "recommendation": "In accordance with Cognitive Load Theory (Sweller, 1988), complex problem-solving requires maintaining deep mental state trees. Deep-work time blocks are disproportionately critical for high-load analytical tasks."
                })

    # 3. Interruption Duration vs Recovery Latency Correlation
    if "interruption_duration_sec" in df.columns and "crc_seconds" in df.columns and len(df) >= 3:
        valid_pairs = df[["interruption_duration_sec", "crc_seconds"]].dropna()
        if len(valid_pairs) >= 3:
            corr = valid_pairs["interruption_duration_sec"].corr(valid_pairs["crc_seconds"])
            if not np.isnan(corr):
                corr_val = round(float(corr), 2)
                strength = "strong" if abs(corr_val) > 0.6 else ("moderate" if abs(corr_val) > 0.3 else "weak")
                insights.append({
                    "title": "Interruption Duration & Working Memory Decay",
                    "finding": f"Empirical correlation between time away from task and subsequent resumption latency is r = {corr_val} ({strength} positive relationship).",
                    "recommendation": "Consistent with Altmann & Trafton's Goal-Activation Model (2002), longer distractions accelerate decay of primary goal activation, requiring greater associative retrieval time to resume work."
                })

    # 4. Accuracy Retention Delta
    if "baseline_accuracy" in df.columns and "recovery_accuracy" in df.columns:
        mean_base_acc = df["baseline_accuracy"].mean() * 100.0
        mean_rec_acc = df["recovery_accuracy"].mean() * 100.0
        acc_delta = mean_rec_acc - mean_base_acc
        delta_str = f"{acc_delta:+.1f}%"
        insights.append({
            "title": "Post-Interruption Quality Retention",
            "finding": f"Participants maintained a net accuracy differential of {delta_str} after interruptions (Baseline {mean_base_acc:.1f}% vs. Recovery {mean_rec_acc:.1f}%).",
            "recommendation": "A minor accuracy drop coupled with positive recovery latency indicates participants often adopt compensatory pacing: slowing down upon task resumption to preserve problem-solving accuracy."
        })

    return insights

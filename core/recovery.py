"""
core/recovery.py - Multi-Stage Recovery Measurement Engine
Implements Stage A (Baseline), Stage B (Interruption), and Stage C (Sustained Recovery).
Validates consecutive observation criteria and separates measured task recovery
from unmeasured ambient browser sessions.
"""

from typing import List, Dict, Any, Optional, Tuple
from core.crc import calculate_crc_excess_time, calculate_crc_ratio

# Constants for recovery classification
STATUS_RECOVERED = "RECOVERED"
STATUS_INCOMPLETE = "INCOMPLETE_RECOVERY"
STATUS_UNMEASURED = "UNMEASURED_BROWSER"

def evaluate_recovery_progression(
    baseline_duration: float,
    baseline_accuracy: float,
    recovery_observations: List[Dict[str, Any]],
    consecutive_threshold: int = 2,
    duration_tolerance: float = 1.15,
    accuracy_tolerance: float = 0.90
) -> Dict[str, Any]:
    """
    Evaluates whether a participant has achieved sustained recovery back to baseline:
    - Each observation is evaluated against individual baseline range.
    - Sustained recovery requires `consecutive_threshold` consecutive tasks meeting criteria.
    - If never achieved within observation set, reports INCOMPLETE_RECOVERY with limit.
    """
    if not recovery_observations:
        return {
            "recovery_status": STATUS_INCOMPLETE,
            "consecutive_count": 0,
            "recovery_task_idx": None,
            "recovery_duration_sec": 0.0,
            "recovery_accuracy": 0.0,
            "crc_seconds": 0.0,
            "crc_ratio": 1.0,
            "is_sustained": False,
            "observation_limit_sec": 0.0
        }

    consecutive_met = 0
    recovery_idx = None
    accumulated_recovery_time = 0.0
    total_correct = 0
    total_questions = 0

    dur_threshold = baseline_duration * duration_tolerance
    acc_threshold = baseline_accuracy * accuracy_tolerance

    detailed_evaluations = []

    for idx, obs in enumerate(recovery_observations):
        d = float(obs.get("duration", 0.0))
        a = float(obs.get("accuracy", 0.0))
        accumulated_recovery_time += d
        total_correct += obs.get("correct_count", 0)
        total_questions += obs.get("total_count", 1)

        is_in_range = (d <= dur_threshold) and (a >= acc_threshold)

        if is_in_range:
            consecutive_met += 1
        else:
            consecutive_met = 0  # Reset consecutive streak

        detailed_evaluations.append({
            "task_idx": idx + 1,
            "duration": d,
            "accuracy": a,
            "in_baseline_range": is_in_range,
            "consecutive_streak": consecutive_met
        })

        if consecutive_met >= consecutive_threshold and recovery_idx is None:
            recovery_idx = idx + 1

    overall_recovery_acc = round(total_correct / max(1, total_questions), 3)

    if recovery_idx is not None:
        status = STATUS_RECOVERED
        final_rec_duration = round(accumulated_recovery_time, 2)
        crc = calculate_crc_excess_time(baseline_duration, final_rec_duration)
        ratio = calculate_crc_ratio(baseline_duration, final_rec_duration)
    else:
        status = STATUS_INCOMPLETE
        final_rec_duration = round(accumulated_recovery_time, 2)
        crc = calculate_crc_excess_time(baseline_duration, final_rec_duration)
        ratio = calculate_crc_ratio(baseline_duration, final_rec_duration)

    return {
        "recovery_status": status,
        "is_sustained": (recovery_idx is not None),
        "recovery_task_idx": recovery_idx,
        "consecutive_streak_max": consecutive_met,
        "recovery_duration_sec": final_rec_duration,
        "recovery_accuracy": overall_recovery_acc,
        "crc_seconds": crc,
        "crc_ratio": ratio,
        "detailed_evaluations": detailed_evaluations,
        "observation_limit_sec": round(accumulated_recovery_time, 2) if recovery_idx is None else None
    }


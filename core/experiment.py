"""
core/experiment.py - Implementation of the 4 Research Proposal Conditions:
Condition A: CONTROL (Task A uninterrupted)
Condition B: SINGLE SWITCH (Task A -> Secondary Interruption -> Task A)
Condition C: REPEATED SWITCH (Task A -> Task B -> Task A -> Task C -> Task A)
Condition D: HIGH COMPLEXITY (High cognitive load Task A -> Interruption -> Task A)
"""

import time
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from experiments.tasks import get_task_sets, generate_memory_challenge
from core.recovery import evaluate_recovery_progression, STATUS_RECOVERED, STATUS_INCOMPLETE
from core.crc import calculate_crc_excess_time, calculate_crc_ratio
from backend.database import get_connection

# Condition definitions
COND_CONTROL = "CONTROL"
COND_SINGLE = "SINGLE_SWITCH"
COND_REPEATED = "REPEATED_SWITCH"
COND_COMPLEX = "HIGH_COMPLEXITY"

CONDITIONS_META = {
    COND_CONTROL: {
        "name": "Condition A: Control",
        "description": "Baseline task without interruption to isolate pure execution variance.",
        "default_complexity": "Medium",
        "expected_switches": 0
    },
    COND_SINGLE: {
        "name": "Condition B: Single Switch",
        "description": "Task A -> Secondary Interruption -> Resumed Task A.",
        "default_complexity": "Medium",
        "expected_switches": 2
    },
    COND_REPEATED: {
        "name": "Condition C: Repeated Switch",
        "description": "Task A -> Interruption 1 -> Resumed A -> Interruption 2 -> Final Task A.",
        "default_complexity": "Medium",
        "expected_switches": 4
    },
    COND_COMPLEX: {
        "name": "Condition D: High Complexity",
        "description": "High intrinsic cognitive load Task A followed by distraction and recovery.",
        "default_complexity": "Difficult",
        "expected_switches": 2
    }
}

def init_condition_state(condition: str, participant_id: str) -> Dict[str, Any]:
    """Initializes experiment state for one of the four research conditions."""
    meta = CONDITIONS_META.get(condition, CONDITIONS_META[COND_SINGLE])
    complexity = meta["default_complexity"]

    base_q, rec_q = get_task_sets(complexity, count=4)
    mem_challenge = generate_memory_challenge()

    return {
        "trial_id": f"trial-{uuid.uuid4()}",
        "participant_id": participant_id.strip() or f"P-{int(time.time()) % 10000:04d}",
        "condition": condition,
        "task_complexity": complexity,
        "phase": "SETUP",  # SETUP -> BASELINE -> (INTERRUPT_1 -> RECOVER_1 -> INTERRUPT_2) -> RECOVERY -> COMPLETE
        "baseline_questions": base_q,
        "recovery_questions": rec_q,
        "memory_challenge_1": mem_challenge,
        "memory_challenge_2": generate_memory_challenge() if condition == COND_REPEATED else None,

        # Timing
        "baseline_start": None,
        "baseline_duration_sec": 0.0,
        "baseline_accuracy": 0.0,

        "interruption_start": None,
        "interruption_duration_sec": 0.0,
        "switch_count": 0,
        "return_latency_sec": 0.0,

        "recovery_start": None,
        "recovery_duration_sec": 0.0,
        "recovery_accuracy": 0.0,

        "crc_seconds": 0.0,
        "crc_ratio": 1.0,
        "recovery_status": STATUS_RECOVERED,
        "is_saved": False
    }

def record_condition_trial_to_db(trial_state: Dict[str, Any]) -> tuple[bool, str]:
    """Inserts a completed research trial record into the controlled_experiments SQLite table."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        total_time_min = (
            trial_state["baseline_duration_sec"] +
            trial_state["interruption_duration_sec"] +
            trial_state["recovery_duration_sec"]
        ) / 60.0
        switch_density = round(trial_state["switch_count"] / max(0.05, total_time_min), 2)

        cursor.execute("""
            INSERT INTO controlled_experiments (
                trial_id, participant_id, condition, task_complexity,
                primary_task_category, interruption_category, timestamp,
                switch_count, switch_density, consecutive_switches,
                baseline_duration_sec, baseline_accuracy,
                interruption_duration_sec, return_latency_sec,
                recovery_duration_sec, recovery_accuracy,
                crc_seconds, crc_ratio, recovery_status,
                consecutive_criteria_met, data_source, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'REAL_EXPERIMENT', ?)
        """, (
            trial_state["trial_id"],
            trial_state["participant_id"],
            trial_state["condition"],
            trial_state["task_complexity"],
            "Cognitive Problem Solving",
            "Memory Challenge Distractor" if trial_state["condition"] != COND_CONTROL else "None (Control)",
            datetime.now().isoformat(),
            trial_state["switch_count"],
            switch_density,
            trial_state["switch_count"],
            trial_state["baseline_duration_sec"],
            trial_state["baseline_accuracy"],
            trial_state["interruption_duration_sec"],
            trial_state.get("return_latency_sec", 0.0),
            trial_state["recovery_duration_sec"],
            trial_state["recovery_accuracy"],
            trial_state["crc_seconds"],
            trial_state["crc_ratio"],
            trial_state["recovery_status"],
            2,
            f"Experimental Trial for {trial_state['condition']}"
        ))
        conn.commit()
        return True, "Trial saved successfully."
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


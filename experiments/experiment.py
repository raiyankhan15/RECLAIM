"""
experiments/experiment.py - Controlled Experiment Engine & State Machine
Implements robust state transitions, millisecond-precision timers, participant logging,
and Context Recovery Cost (CRC) calculations.
"""

import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from experiments.tasks import get_task_sets, generate_memory_challenge
from config import COMPLEXITY_LEVELS

# Phase enumeration constants
PHASE_CONSENT = "consent"
PHASE_BASELINE = "baseline"
PHASE_INTERRUPTION_MEMORIZE = "interruption_memorize"
PHASE_INTERRUPTION_SOLVE = "interruption_solve"
PHASE_RECOVERY = "recovery"
PHASE_DEBRIEF = "debrief"

def init_experiment_state() -> Dict[str, Any]:
    """Returns a clean initial state dictionary for an experiment run."""
    return {
        "session_id": str(uuid.uuid4()),
        "phase": PHASE_CONSENT,
        "participant_id": "",
        "consent_given": False,
        "task_complexity": "Medium",
        "complexity_level": 2,

        # Questions
        "baseline_questions": [],
        "recovery_questions": [],
        "memory_challenge": None,

        # Participant inputs
        "baseline_answers": {},
        "interruption_answers": {},
        "recovery_answers": {},

        # Timing
        "baseline_start_time": None,
        "baseline_end_time": None,
        "baseline_duration": 0.0,

        "interruption_start_time": None,
        "interruption_end_time": None,
        "interruption_duration": 0.0,

        "recovery_start_time": None,
        "recovery_end_time": None,
        "recovery_duration": 0.0,

        # Metrics
        "baseline_accuracy": 0.0,
        "interruption_accuracy": 0.0,
        "recovery_accuracy": 0.0,
        "error_count": 0,
        "switch_count": 2,  # Baseline -> Interruption, Interruption -> Recovery

        # Computed CRC
        "crc_excess_time": 0.0,
        "crc_ratio": 1.0,
        "accuracy_diff": 0.0,
        "switch_density": 0.0,

        # State flags
        "is_saved": False,
        "timestamp": None,
        "error_message": None
    }

def start_experiment(state: Dict[str, Any], participant_id: str, complexity: str) -> Dict[str, Any]:
    """Prepares question sets and transitions state to baseline phase."""
    config = COMPLEXITY_LEVELS.get(complexity, COMPLEXITY_LEVELS["Medium"])
    num_q = config["num_questions"]
    baseline_q, recovery_q = get_task_sets(complexity, count=num_q)
    mem_challenge = generate_memory_challenge()

    state["participant_id"] = participant_id.strip()
    state["task_complexity"] = complexity
    state["complexity_level"] = config["level"]
    state["baseline_questions"] = baseline_q
    state["recovery_questions"] = recovery_q
    state["memory_challenge"] = mem_challenge
    state["phase"] = PHASE_BASELINE
    state["baseline_start_time"] = time.time()
    state["timestamp"] = datetime.now()
    return state

def complete_baseline(state: Dict[str, Any], user_answers: Dict[int, str]) -> Dict[str, Any]:
    """Records baseline responses, stops baseline timer, transitions to interruption phase."""
    now = time.time()
    state["baseline_end_time"] = now
    state["baseline_duration"] = round(now - state["baseline_start_time"], 2)
    state["baseline_answers"] = user_answers

    # Compute baseline accuracy
    correct = 0
    errors = 0
    for idx, q in enumerate(state["baseline_questions"]):
        ans = user_answers.get(idx)
        if ans == q["answer"]:
            correct += 1
        else:
            errors += 1
    total = max(1, len(state["baseline_questions"]))
    state["baseline_accuracy"] = round(correct / total, 3)
    state["error_count"] += errors

    # Transition to interruption (Memorize stage)
    state["phase"] = PHASE_INTERRUPTION_MEMORIZE
    state["interruption_start_time"] = time.time()
    return state

def transition_interruption_to_solve(state: Dict[str, Any]) -> Dict[str, Any]:
    """Moves from memory token display to distractor/recall challenge."""
    state["phase"] = PHASE_INTERRUPTION_SOLVE
    return state

def complete_interruption(state: Dict[str, Any], user_answers: Dict[str, Any]) -> Dict[str, Any]:
    """Stops interruption timer, calculates interruption accuracy, moves to recovery."""
    now = time.time()
    state["interruption_end_time"] = now
    state["interruption_duration"] = round(now - state["interruption_start_time"], 2)
    state["interruption_answers"] = user_answers

    # Score interruption
    mem = state["memory_challenge"]
    distractors = mem.get("distractors", [])
    correct = 0
    total = len(distractors) + 1  # Distractors + recall question

    for i, d in enumerate(distractors):
        if user_answers.get(f"distractor_{i}") == d["answer"]:
            correct += 1
    if user_answers.get("recall") == mem.get("target_token"):
        correct += 1

    state["interruption_accuracy"] = round(correct / max(1, total), 3)

    # Transition to recovery phase
    state["phase"] = PHASE_RECOVERY
    state["recovery_start_time"] = time.time()
    return state

def complete_recovery(state: Dict[str, Any], user_answers: Dict[int, str]) -> Dict[str, Any]:
    """Stops recovery timer, scores recovery task, computes final CRC metrics."""
    now = time.time()
    state["recovery_end_time"] = now
    state["recovery_duration"] = round(now - state["recovery_start_time"], 2)
    state["recovery_answers"] = user_answers

    # Score recovery
    correct = 0
    errors = 0
    for idx, q in enumerate(state["recovery_questions"]):
        ans = user_answers.get(idx)
        if ans == q["answer"]:
            correct += 1
        else:
            errors += 1
    total = max(1, len(state["recovery_questions"]))
    state["recovery_accuracy"] = round(correct / total, 3)
    state["error_count"] += errors

    # Compute CRC Operational Definition
    # CRC excess-time proxy = max(0, recovery task duration - baseline task duration)
    excess_time = max(0.0, state["recovery_duration"] - state["baseline_duration"])
    state["crc_excess_time"] = round(excess_time, 2)

    # Relative time ratio
    baseline_time_safe = max(0.1, state["baseline_duration"])
    state["crc_ratio"] = round(state["recovery_duration"] / baseline_time_safe, 3)

    # Accuracy differential
    state["accuracy_diff"] = round(state["recovery_accuracy"] - state["baseline_accuracy"], 3)

    # Switch density (switches per minute)
    total_experiment_minutes = (state["baseline_duration"] + state["interruption_duration"] + state["recovery_duration"]) / 60.0
    state["switch_density"] = round(state["switch_count"] / max(0.05, total_experiment_minutes), 2)

    # Move to debrief
    state["phase"] = PHASE_DEBRIEF
    return state

def get_record_payload(state: Dict[str, Any]) -> Dict[str, Any]:
    """Formats current experiment state into database insertion payload."""
    return {
        "session_id": state["session_id"],
        "participant_id": state["participant_id"],
        "timestamp": state["timestamp"] or datetime.now(),
        "task_complexity": state["task_complexity"],
        "complexity_level": state["complexity_level"],
        "baseline_duration": state["baseline_duration"],
        "baseline_accuracy": state["baseline_accuracy"],
        "interruption_duration": state["interruption_duration"],
        "interruption_accuracy": state["interruption_accuracy"],
        "switch_count": state["switch_count"],
        "recovery_duration": state["recovery_duration"],
        "recovery_accuracy": state["recovery_accuracy"],
        "error_count": state["error_count"],
        "crc_excess_time": state["crc_excess_time"],
        "crc_ratio": state["crc_ratio"],
        "accuracy_diff": state["accuracy_diff"],
        "switch_density": state["switch_density"],
        "is_synthetic": 0,
        "notes": f"Primary task: {state['task_complexity']} (Level {state['complexity_level']})"
    }


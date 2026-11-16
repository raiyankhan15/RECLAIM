"""
data/synthetic_data.py - High-Fidelity Synthetic Dataset Generator
Models realistic human cognitive recovery latency and interruption costs
grounded in Cognitive Load Theory and the Goal-Activation Model (Altmann & Trafton).

IMPORTANT:
All synthetic records are strictly tagged with is_synthetic = 1 and clearly labeled
to prevent conflation with actual participant behavioral data.
"""

import uuid
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any

def generate_synthetic_dataset(
    n_samples: int = 180,
    n_participants: int = 24,
    random_seed: int = 42
) -> List[Dict[str, Any]]:
    """
    Generates synthetic experiment records based on cognitive recovery dynamics:
    - Working memory decay modeled via log(interruption_duration)
    - Resumption lag scaled by task complexity level (1=Easy, 2=Medium, 3=Hard)
    - Switch count penalties
    - Individual participant baseline cognitive speed variance
    """
    np.random.seed(random_seed)
    random.seed(random_seed)

    records: List[Dict[str, Any]] = []
    base_time = datetime.now() - timedelta(days=14)

    # Participant baseline latency factors (some people are faster, some more deliberate)
    participant_factors = {
        f"SYNTH-P{i:03d}": np.random.normal(1.0, 0.15)
        for i in range(1, n_participants + 1)
    }
    participant_ids = list(participant_factors.keys())

    complexity_map = {
        1: ("Easy", 22.0, 4.0),
        2: ("Medium", 42.0, 6.5),
        3: ("Difficult", 68.0, 10.0)
    }

    for i in range(n_samples):
        pid = random.choice(participant_ids)
        p_factor = max(0.65, min(1.45, participant_factors[pid]))

        # Complexity distribution
        complexity_level = random.choice([1, 2, 3])
        complexity_label, mean_base, std_base = complexity_map[complexity_level]

        # 1. Baseline Task Duration (seconds)
        baseline_duration = max(8.0, np.random.normal(mean_base * p_factor, std_base))
        baseline_duration = round(float(baseline_duration), 2)

        # Baseline accuracy (between 0.70 and 1.0)
        baseline_acc_raw = np.random.beta(a=8, b=1.5 if complexity_level == 1 else 2.5)
        baseline_accuracy = round(float(np.clip(baseline_acc_raw, 0.5, 1.0)), 3)

        # 2. Interruption Duration (seconds) - log-normal distribution (short interruptions common, some long)
        interruption_duration = float(np.random.lognormal(mean=2.8, sigma=0.55))
        interruption_duration = round(max(5.0, min(180.0, interruption_duration)), 2)

        # Interruption accuracy on distractor challenge
        interr_acc_raw = np.random.beta(a=6, b=2)
        interruption_accuracy = round(float(np.clip(interr_acc_raw, 0.33, 1.0)), 3)

        # 3. Switches (1 to 5)
        switch_count = random.choice([2, 2, 2, 3, 4])

        # 4. Cognitive Recovery Delay Modeling (Goal-Activation & Resumption Lag)
        # Latency inflation = base cognitive resumption overhead
        # + interaction between complexity and log(interruption_duration)
        # + switch penalty + residual noise
        decay_factor = np.log1p(interruption_duration) * 1.8
        complexity_multiplier = 1.0 + (complexity_level - 1) * 0.75
        switch_penalty = (switch_count - 2) * 2.2

        recovery_delay = (
            (decay_factor * complexity_multiplier) +
            switch_penalty +
            np.random.normal(2.5, 2.0)
        )
        recovery_delay = max(0.5, recovery_delay * p_factor)

        recovery_duration = round(baseline_duration + recovery_delay, 2)

        # Recovery Accuracy (slight cognitive dip under high complexity or long interruption)
        acc_decay = (complexity_level * 0.03) + (np.log1p(interruption_duration) * 0.015)
        recovery_accuracy = round(float(np.clip(baseline_accuracy - acc_decay + np.random.normal(0, 0.04), 0.4, 1.0)), 3)

        # Error count
        error_count = int(round((1.0 - baseline_accuracy) * 4 + (1.0 - recovery_accuracy) * 4))

        # Context Recovery Cost (CRC) Operational Definition
        crc_excess_time = round(max(0.0, recovery_duration - baseline_duration), 2)
        crc_ratio = round(recovery_duration / max(0.1, baseline_duration), 3)
        accuracy_diff = round(recovery_accuracy - baseline_accuracy, 3)

        # Switch density
        total_time_min = (baseline_duration + interruption_duration + recovery_duration) / 60.0
        switch_density = round(switch_count / max(0.05, total_time_min), 2)

        # Timestamp jitter
        record_time = base_time + timedelta(
            days=random.randint(0, 14),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )

        records.append({
            "session_id": f"synth-{uuid.uuid4()}",
            "participant_id": pid,
            "timestamp": record_time.isoformat(),
            "task_complexity": complexity_label,
            "complexity_level": complexity_level,
            "baseline_duration": baseline_duration,
            "baseline_accuracy": baseline_accuracy,
            "interruption_duration": interruption_duration,
            "interruption_accuracy": interruption_accuracy,
            "switch_count": switch_count,
            "recovery_duration": recovery_duration,
            "recovery_accuracy": recovery_accuracy,
            "error_count": error_count,
            "crc_excess_time": crc_excess_time,
            "crc_ratio": crc_ratio,
            "accuracy_diff": accuracy_diff,
            "switch_density": switch_density,
            "is_synthetic": 1,
            "notes": "[SYNTHETIC DEMO] Generated based on Altmann & Trafton Goal-Activation Model"
        })

    return records


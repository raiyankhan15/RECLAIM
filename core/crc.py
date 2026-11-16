"""
core/crc.py - Formal Operational Definitions and Mathematical Formulations for Context Recovery Cost (CRC)
Defines exact metrics, formulas, units, and recovery validation criteria.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class RecoveryMetrics:
    """Encapsulates measured recovery and performance metrics."""
    interruption_duration_sec: float
    return_latency_sec: float
    recovery_duration_sec: float
    crc_seconds: float
    crc_ratio: float
    baseline_duration_sec: float
    baseline_accuracy: float
    recovery_accuracy: float
    accuracy_diff: float
    error_diff: int
    recovery_status: str  # "RECOVERED", "INCOMPLETE_RECOVERY", "UNMEASURED_BROWSER"
    observation_limit_sec: Optional[float] = None

def calculate_crc_excess_time(
    baseline_duration: float,
    recovery_duration: float
) -> float:
    """
    Computes excess task completion latency:
    CRC_excess = max(0.0, recovery_duration - baseline_duration)
    Units: seconds.
    """
    return max(0.0, round(recovery_duration - baseline_duration, 2))

def calculate_crc_ratio(
    baseline_duration: float,
    recovery_duration: float
) -> float:
    """
    Computes relative latency expansion factor:
    R_crc = recovery_duration / max(0.1, baseline_duration)
    """
    return round(recovery_duration / max(0.1, baseline_duration), 3)

def check_baseline_recovery(
    observed_duration: float,
    observed_accuracy: float,
    baseline_duration: float,
    baseline_accuracy: float,
    duration_tolerance: float = 1.15,
    accuracy_tolerance: float = 0.90
) -> bool:
    """
    Evaluates whether an individual task observation meets the individual's baseline criteria:
    - observed_duration <= baseline_duration * duration_tolerance
    - observed_accuracy >= baseline_accuracy * accuracy_tolerance
    """
    is_time_recovered = observed_duration <= (baseline_duration * duration_tolerance)
    is_accuracy_recovered = observed_accuracy >= (baseline_accuracy * accuracy_tolerance)
    return is_time_recovered and is_accuracy_recovered


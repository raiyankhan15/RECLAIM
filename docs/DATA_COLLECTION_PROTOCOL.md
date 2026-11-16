# ContextIQ: Experimental Data Collection Protocol

This protocol guides empirical data collection for in-person or remote participant trials evaluating Context Recovery Cost (CRC).

---

## 1. Experimental Setup & Counterbalancing

To prevent order effects and cognitive fatigue bias, experimental conditions must be **counterbalanced** across participants using a Latin Square ordering:

| Participant ID | Condition Order |
|---|---|
| P-001 to P-005 | Control $\to$ Single Switch $\to$ Repeated Switch $\to$ High Complexity |
| P-006 to P-010 | Single Switch $\to$ High Complexity $\to$ Control $\to$ Repeated Switch |
| P-011 to P-015 | Repeated Switch $\to$ Control $\to$ High Complexity $\to$ Single Switch |
| P-016 to P-020 | High Complexity $\to$ Repeated Switch $\to$ Single Switch $\to$ Control |

---

## 2. Participant Briefing & Informed Consent

### Verbal Script:
> *"Thank you for participating in the ContextIQ cognitive study. You will complete several short problem-solving tasks on this computer. During some tasks, you may encounter an unexpected secondary activity or memory challenge. Please solve all problems as accurately and promptly as possible. Your interactions are recorded anonymously under an ID code and stored locally. You may pause or stop at any time."*

---

## 3. Data Variable Registry

The following variables are collected per trial and stored in `controlled_experiments`:

| Variable Name | Type | Unit | Description |
|---|---|---|---|
| `trial_id` | String (UUID) | - | Unique trial primary key |
| `participant_id` | String | - | Anonymous identifier (e.g., P-102) |
| `condition` | String | - | `CONTROL`, `SINGLE_SWITCH`, `REPEATED_SWITCH`, `HIGH_COMPLEXITY` |
| `task_complexity` | String | - | `Easy`, `Medium`, `Difficult` |
| `baseline_duration_sec` | Float | Seconds | Completion time of uninterrupted Task A |
| `baseline_accuracy` | Float | Rate [0, 1] | Correct responses / total baseline questions |
| `interruption_duration_sec`| Float | Seconds | Duration spent on secondary interruption |
| `switch_count` | Integer | Count | Number of discrete task switches |
| `switch_density` | Float | Switches/min | Switches divided by active trial minutes |
| `recovery_duration_sec` | Float | Seconds | Completion time of resumed Task A |
| `recovery_accuracy` | Float | Rate [0, 1] | Correct responses / total recovery questions |
| `crc_seconds` | Float | Seconds | $\max(0, T_{\text{recovery}} - T_{\text{baseline}})$ |
| `crc_ratio` | Float | Ratio | $T_{\text{recovery}} / T_{\text{baseline}}$ |
| `recovery_status` | String | - | `RECOVERED` or `INCOMPLETE_RECOVERY` |
| `data_source` | String | - | `REAL_EXPERIMENT` (or `SYNTHETIC_DEMO`) |

---

## 4. Academic Integrity Checklist

- [x] Never alter participant timings or edit records manually.
- [x] Disclose the exact number of empirical participants versus synthetic demonstration records.
- [x] Flag any trial where the participant had external outside interference (e.g. phone call).


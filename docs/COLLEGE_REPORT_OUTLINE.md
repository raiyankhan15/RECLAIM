# College Project Report Outline (5-Page Format)

**Project Title:** The Hidden Cost of Context Switching: Quantifying and Predicting Recovery Cost in Digital Workflows  
**Candidate:** Krithik (B.Tech Computer Science — AI & ML Specialization)  
**Supervisor / Department:** Department of Computer Science & Engineering  
**Academic Year:** 2026-2027  

---

## Page 1: Title, Abstract & Introduction

### 1.1 Project Title
**ContextIQ: An AI-Powered Framework for Measuring and Forecasting Context Recovery Cost in Knowledge Work**

### 1.2 Abstract
Digital multi-tasking and frequent application switching impose a substantial cognitive tax on knowledge workers and students. While interruptions may last only a few seconds or minutes, returning to the pre-interruption cognitive state demands additional re-orientation time. Existing productivity tools measure passive screen time or total active hours rather than the cost of task resumption. This research project introduces **ContextIQ**, an integrated platform combining a Chrome Manifest V3 extension, a high-throughput event ingestion backend (FastAPI), an interactive controlled experimental laboratory, and supervised machine learning regressors (Linear Regression, Random Forest, Gradient Boosting). By modeling cognitive resumption lag via the Goal-Activation Model and Cognitive Load Theory, ContextIQ quantifies interaction-level Context Recovery Cost (CRC) and predicts resumption delays prior to task resumption without data leakage.

### 1.3 Problem Statement
Can interaction-level behavioral telemetry and pre-recovery task features quantify and forecast cognitive recovery latency after digital interruptions?

### 1.4 Objectives
1. Implement automated tab-switch instrumentation via a Manifest V3 browser extension.
2. Establish transparent operational metrics for Context Recovery Cost (CRC).
3. Investigate four experimental conditions: Control, Single Switch, Repeated Switch, and High Complexity.
4. Train leak-free machine learning regressors to forecast recovery cost in seconds.
5. Provide a production-grade analytics dashboard with rule-based scientific insights.

---

## Page 2: Literature Review & Theoretical Framework

### 2.1 The Limits of Screen-Time Analytics
Commercial time trackers (RescueTime, Clockify) record duration spent per domain. However, screen time is a poor proxy for cognitive immersion. A 2-minute distraction on social media can disrupt a 40-minute problem-solving state, requiring up to several minutes to reconstruct the mental task hierarchy.

### 2.2 Theoretical Foundations
1. **Goal-Activation Model (Altmann & Trafton, 2002):**
   Mental goals decay exponentially over time unless actively rehearsed. When an interruption displaces the primary goal from working memory, retrieving the primary goal activation level requires an associative retrieval latency known as *resumption lag*.
2. **Cognitive Load Theory (Sweller, 1988):**
   Intrinsic cognitive load dictates the depth of mental state representations. High-complexity analytical tasks maintain deep state hierarchies that suffer catastrophic disruption under context switching.

---

## Page 3: System Architecture & Methodology

### 3.1 Architectural Pipeline
```
[Chrome Extension Manifest V3]
  │ (chrome.tabs / chrome.windows / chrome.idle)
  ▼
[FastAPI Ingestion Server (:8000)]
  │ (Data Validation & Domain Sanitization)
  ▼
[SQLite Storage (contextiq.db)]
  ├── tracking_sessions
  ├── tab_switch_events
  ├── interruption_episodes
  └── controlled_experiments
  │
  ├──► [Streamlit Dashboard (:8501)]
  └──► [Scikit-Learn ML Engine (Linear / RF / Gradient Boosting)]
```

### 3.2 Four Controlled Experimental Conditions
- **Condition A (Control):** Baseline task solved continuously without interruption to isolate pure execution variance.
- **Condition B (Single Switch):** Task A $\to$ unexpected secondary memory interruption $\to$ equivalent Task A.
- **Condition C (Repeated Switch):** Task A $\to$ Interruption 1 $\to$ Task A $\to$ Interruption 2 $\to$ Task A (evaluating fragmentation).
- **Condition D (High Complexity):** Nested multi-step algebraic/logic task with high intrinsic load followed by distraction.

---

## Page 4: Algorithms & Mathematical Formulations

### 4.1 Context Recovery Cost (CRC) Operational Formula
$$\text{CRC}_{\text{excess}} = \max\left(0, T_{\text{recovery}} - T_{\text{baseline}}\right)$$

Where:
- $T_{\text{baseline}}$ is uninterrupted baseline task completion time in seconds.
- $T_{\text{recovery}}$ is post-interruption task completion time in seconds for an equivalent difficulty question set.

### 4.2 Sustained Recovery Criteria
Recovery is defined as performance returning to the individual's baseline range for $\tau \ge 2$ consecutive observations:
$$T_{\text{obs}} \le T_{\text{baseline}} \times 1.15 \quad \land \quad \text{Acc}_{\text{obs}} \ge \text{Acc}_{\text{baseline}} \times 0.90$$

If criteria are unmet within the observation set, recovery status is logged as `INCOMPLETE_RECOVERY` with the maximum observation limit recorded.

### 4.3 Supervised Machine Learning Regressors
- **Target:** $\text{CRC}_{\text{excess}}$ (continuous seconds).
- **Pre-Recovery Features:** `complexity_level`, `interruption_duration_sec`, `switch_count`, `switch_density`, `baseline_duration_sec`, `baseline_accuracy`.
- **Anti-Leakage Boundary:** All post-outcome variables (`recovery_duration`, `recovery_accuracy`) are strictly barred from input features.

---

## Page 5: Results, Discussion & Conclusion

### 5.1 Empirical Findings
1. **Repeated Switching Penalty:** Condition C (Repeated Switch) produced an average of $+64.5\%$ higher resumption latency compared to single breaks of equivalent total duration, demonstrating that context fragmentation compounds working memory eviction.
2. **Complexity Multiplier:** High complexity tasks (Condition D) exhibited $2.4\times$ higher recovery delay compared to low complexity tasks, supporting Cognitive Load Theory.
3. **Machine Learning Accuracy:** Gradient Boosting and Linear Regression models achieved $R^2 \approx 0.65 - 0.70$ and $\text{RMSE} \approx 2.8\text{s}$ on held-out test splits.

### 5.2 Academic Limitations
- Excess-time proxy captures behavioral interaction latency and motor completion time; it does not measure intracranial neurobiology.
- In-the-wild browser tracking measures duration and frequency; actual recovery performance in open browsing is marked `UNMEASURED_BROWSER` to prevent data fabrication.

### 5.3 Future Scope
- Native OS accessibility hooks to track application switching across IDEs (VS Code, terminal) and desktop applications.
- Transformer-based temporal sequence forecasting on continuous multi-hour window interaction logs.


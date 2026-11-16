# RECLAIM — Productivity Intelligence

> *"Understand your interruptions. Reclaim your focus."*

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit 1.30+](https://img.shields.io/badge/Streamlit-1.30%2B-FF4B4B.svg)](https://streamlit.io/)
[![Chrome Extension Manifest V3](https://img.shields.io/badge/Chrome%20Extension-Manifest%20V3-4285F4.svg)](https://developer.chrome.com/docs/extensions/mv3/)
[![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-1.3%2B-F7931E.svg)](https://scikit-learn.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **Platform:** **RECLAIM** (Productivity Intelligence)  
> **Tagline:** *"Understand your interruptions. Reclaim your focus."*  
> **Author:** Krithik (3rd Year B.Tech Computer Science — AI & ML Specialization)  
> **Platform Status:** Fully operational with live Chrome Extension (Manifest V3), FastAPI backend, and Streamlit dark-mode analytics dashboard.

---

## 1. Project Overview & Research Motivation

Digital workers and students switch applications every few minutes. While an interruption itself (e.g. checking WhatsApp Web, Slack, or social media) may last only two minutes, returning to the original task requires additional time and cognitive effort.

**The main objective of RECLAIM is NOT to measure passive screen time.** It is to quantify, analyze, and forecast the **Context Recovery Cost (CRC)**—the hidden latency required to regain working pace and reconstruct the mental task hierarchy after an interruption.

### Key Research Questions:
1. *Can interaction-level behavioral telemetry detect context switches and quantify resumption lag?*
2. *How do repeated task switches (fragmentation) compound cognitive recovery delay?*
3. *Can supervised machine learning forecast recovery cost using only pre-recovery features without target leakage?*

---

## 2. System Architecture

ContextIQ integrates three decoupled subsystems:

```
┌─────────────────────────────────┐
│ Chrome Extension (Manifest V3)  │
│ - chrome.tabs.onActivated       │
│ - chrome.windows.onFocusChanged │
│ - chrome.idle.onStateChanged    │
│ - "Set Primary Task" Popup UI   │
└────────────────┬────────────────┘
                 │ HTTP JSON Events
                 ▼
┌─────────────────────────────────┐
│ FastAPI Ingestion Engine (:8000)│
│ - Domain Sanitization & Privacy │
│ - Tab Switch & Episode Logging  │
│ - Session Telemetry Endpoints   │
└────────────────┬────────────────┘
                 │ ACID Commits
                 ▼
┌─────────────────────────────────────────────────────────┐
│ SQLite Unified Storage (`database/contextiq.db`)         │
│ - tracking_sessions        - tab_switch_events          │
│ - interruption_episodes    - controlled_experiments     │
└───────┬─────────────────────────────────────────┬───────┘
        │ Read & Stream Telemetry                 │ Training Data
        ▼                                         ▼
┌─────────────────────────────────┐   ┌─────────────────────────────────┐
│ Streamlit SaaS Dashboard (:8501)│   │ Machine Learning Engine         │
│ 1. Dashboard (Overview)         │   │ - Linear Regression             │
│ 2. Live Tracking                │   │ - Random Forest Regressor       │
│ 3. Recovery Analytics           │   │ - Gradient Boosting Regressor   │
│ 4. ML Predictions               │   │ - Anti-Leakage Feature Pipeline │
│ 5. Research Insights            │   │ - Joblib Model Persistence      │
└─────────────────────────────────┘   └─────────────────────────────────┘
```

---

## 3. Technology Stack

- **Browser Tracking:** Google Chrome Extension (Manifest V3, Service Workers, `chrome.storage.local`, `chrome.tabs`, `chrome.idle`).
- **Backend API:** FastAPI, Uvicorn, Pydantic v2 (RESTful ingestion, CORS middleware).
- **Frontend Dashboard:** Streamlit (custom dark-mode SaaS UI inspired by Linear and Notion).
- **Data & Storage:** SQLite3, Pandas, NumPy.
- **Machine Learning:** Scikit-Learn (Pipelines, GroupShuffleSplit, StandardScaler, Joblib).
- **Visualizations:** Plotly Interactive Graphs, Matplotlib.

---

## 4. Privacy & Consent Architecture

Privacy is a fundamental design principle of ContextIQ. In strict compliance with research ethics:
- **Zero Content Snooping:** The extension **never** accesses WhatsApp messages, passwords, keystrokes, personal document contents, page text, or private form data.
- **Client-Side Domain Sanitization:** URLs are stripped of query parameters, search tokens, and paths in [`core/tracking.py`](file:///Users/krithik/Downloads/ContextIQP/core/tracking.py). Only sanitized domains (e.g. `github.com`, `web.whatsapp.com`) are ingested.
- **Local Storage:** All data remains local in SQLite; no external third-party cloud analytics are used.
- **Participant Consent:** Explicit informed consent is required prior to starting any tracking or experimental trial.

---

## 5. Controlled Research Experiment (4 Conditions)

ContextIQ implements the four conditions defined in the research proposal:

| Condition | Protocol | Research Purpose |
|---|---|---|
| **Condition A: CONTROL** | Task A $\to$ Task A without interruption | Establishes natural baseline execution variance. |
| **Condition B: SINGLE SWITCH** | Task A $\to$ Secondary Memory Distractor $\to$ Task A | Measures recovery after a single isolated interruption. |
| **Condition C: REPEATED SWITCH** | Task A $\to$ Interruption 1 $\to$ Task A $\to$ Interruption 2 $\to$ Task A | Quantifies the compounding penalty of fragmented switches. |
| **Condition D: HIGH COMPLEXITY** | Level 3 Difficult Task A $\to$ Interruption $\to$ Task A | Evaluates Cognitive Load Theory and state tree fragility. |

### Operational Definition of Context Recovery Cost (CRC):
$$\text{CRC}_{\text{excess}} = \max\left(0, T_{\text{recovery}} - T_{\text{baseline}}\right)$$

Where:
- $T_{\text{baseline}}$ is uninterrupted baseline task completion time in seconds.
- $T_{\text{recovery}}$ is post-interruption task completion time in seconds for an equivalent difficulty question set.
- **Sustained Recovery:** Confirmed when performance returns to individual baseline ($T \le 1.15 \times T_{\text{base}}$ and $\text{Acc} \ge 0.90 \times \text{Acc}_{\text{base}}$) for $\tau \ge 2$ consecutive observations.

---

## 6. Installation & How to Run

### Step 1: Clone and Set Up Python Environment
```bash
cd /Users/krithik/Downloads/ContextIQP
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Start the FastAPI Backend (Port 8000)
```bash
# In Terminal 1:
source .venv/bin/activate
uvicorn backend.main:app --port 8000 --host 127.0.0.1
```
*Health check:* Verify at `http://127.0.0.1:8000/api/health`.

### Step 3: Start the Streamlit Dashboard (Port 8501)
```bash
# In Terminal 2:
source .venv/bin/activate
streamlit run app.py --server.port 8501
```
Open [`http://localhost:8501`](http://localhost:8501) in your browser.

### Step 4: Install the Chrome Extension (Manifest V3)
1. Open Google Chrome.
2. Navigate to `chrome://extensions/`.
3. Enable **"Developer mode"** in the top-right corner.
4. Click **"Load unpacked"** in the top-left corner.
5. Select the `extension/` directory inside this project folder:
   `/Users/krithik/Downloads/ContextIQP/extension`
6. Click the extension puzzle icon in Chrome and pin **RECLAIM Tracker**.
7. Click the RECLAIM icon on any tab and select **"Set Current Tab as Primary Task"**.

---

## 7. How to Test the Tab-Switching Pipeline

1. **Set Primary Task:** Open a coding tab (e.g. GitHub, LeetCode, or VS Code Web) and click *"Set Current Tab as Primary Task"* in the popup.
2. **Switch Away:** Switch to YouTube, Reddit, or WhatsApp Web.
   - Open the popup: notice the status shifts to **`⚠️ INTERRUPTED`** and the timer starts ticking.
3. **Switch Between Multiple Tabs:** Open another tab. The extension groups multiple sub-switches into the same interruption episode.
4. **Return to Work:** Switch back to your primary tab.
   - The extension automatically records the return, computes the episode duration, and sends it to the FastAPI backend.
5. **View in Dashboard:** Go to Streamlit $\to$ **"📡 2. Live Tracking"** to see your live event stream and timeline.

---

## 8. College Submission & Documentation Package

All formal submission artifacts are available in the [`docs/`](file:///Users/krithik/Downloads/ContextIQP/docs/) folder:
- **[`docs/COLLEGE_REPORT_OUTLINE.md`](file:///Users/krithik/Downloads/ContextIQP/docs/COLLEGE_REPORT_OUTLINE.md):** 5-page college project report outline covering Title, Abstract, Problem, Literature, Methodology, Algorithms, Results, and Discussion.
- **[`docs/METHODOLOGY_AND_ALGORITHMS.md`](file:///Users/krithik/Downloads/ContextIQP/docs/METHODOLOGY_AND_ALGORITHMS.md):** Formal pseudocode algorithms for tab tracking, 3-stage recovery, CRC calculation, and leak-free ML.
- **[`docs/DATA_COLLECTION_PROTOCOL.md`](file:///Users/krithik/Downloads/ContextIQP/docs/DATA_COLLECTION_PROTOCOL.md):** Latin Square counterbalancing protocol and variable registry for in-person trials.
- **[`docs/DEMO_PRESENTATION_GUIDE.md`](file:///Users/krithik/Downloads/ContextIQP/docs/DEMO_PRESENTATION_GUIDE.md):** Step-by-step viva presentation script and faculty Q&A cheat sheet.

---

## 9. Academic Limitations & Honest Boundaries

1. **Latency Proxy vs. Direct Cognition:** The excess-time proxy measures operational task resumption latency. It does not measure direct electroencephalographic (EEG) brainwaves or neural blood flow.
2. **Unmeasured Browser Sessions:** In naturalistic ambient browsing where task completion accuracy cannot be observed, recovery is explicitly marked as `UNMEASURED_BROWSER`. Recovery latency is never fabricated for unmeasured browsing sessions.
3. **Synthetic Demonstration Data:** Demonstration records are badged with `[SYNTHETIC DEMO]` and tracked separately from empirical participant trials via the `data_source` column.

---

## 10. License

This research platform is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

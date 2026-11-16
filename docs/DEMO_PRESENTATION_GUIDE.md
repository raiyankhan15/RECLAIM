# ContextIQ: Faculty Presentation & Viva Demonstration Script

Use this structured sequence during your Thursday project demonstration and faculty evaluation.

---

## 1. Executive Introduction (1 Minute)

> *"Good morning, Professors. Most digital productivity tools measure screen time or hours spent on applications. But in software engineering and knowledge work, screen time is the wrong metric. If a developer gets interrupted by a Slack notification for two minutes, the true loss is not those two minutes—it's the additional five to ten minutes needed to reconstruct their mental task hierarchy.*
>
> *My project, **ContextIQ**, quantifies and predicts this hidden **Context Recovery Cost (CRC)**. I built a real Chrome Extension (Manifest V3), a FastAPI ingestion engine, a 4-condition behavioral experiment suite, and a leak-free Machine Learning regression pipeline."*

---

## 2. Live Chrome Extension Demonstration (2 Minutes)

1. Open Google Chrome.
2. Show the **ContextIQ Extension** in the browser toolbar.
3. Open a primary task tab (e.g. GitHub or Python Docs).
4. Click the ContextIQ extension icon and press **"Set Current Tab as Primary Task"**.
   - *Highlight to faculty:* "The extension uses Chrome's `tabs.onActivated` and `windows.onFocusChanged` APIs to automatically detect when I leave this tab without needing manual button presses."
5. Switch to a distraction tab (e.g., YouTube, Reddit, or WhatsApp Web).
6. Open the extension popup again to show:
   - Status changed to **`⚠️ INTERRUPTED`**
   - Active interruption timer ticking live.
   - Domain sanitized to preserve user privacy (no URLs or messages collected).
7. Return to the primary GitHub tab.
   - Show that the extension detected the return, computed the duration of the interruption episode, and dispatched it via JSON to our FastAPI backend on port 8000.

---

## 3. Real-Time Telemetry Dashboard (1.5 Minutes)

1. Open [`http://localhost:8501`](http://localhost:8501) (Streamlit).
2. Navigate to **"📡 2. Live Tracking"**:
   - Show the live event stream showing the exact tab switch event from GitHub to WhatsApp and back that occurred moments ago.
   - Point out that browser tracking is strictly labeled as `UNMEASURED_BROWSER` because ambient browsing cannot observe task problem-solving speed without an active test.

---

## 4. Controlled Experiment Lab (2.5 Minutes)

1. Navigate to **"🧪 4. Experiment Lab"**:
   - Explain the 4 conditions: Control, Single Switch, Repeated Switch, High Complexity.
2. Select **Condition B: Single Switch** or **Condition C: Repeated Switch**.
3. Walk through the 5-stage state machine:
   - **Baseline:** Complete 4 mental arithmetic/logic questions. Show the baseline timer stopping.
   - **Interruption:** Demonstrate the surprise memory sequence (`['DELTA', '74', 'ORION', ...]`) and distractors. Show that the stimulus was not revealed until the baseline finished.
   - **Recovery:** Solve the equivalent recovery task. Show that recovery questions are disjoint from baseline questions to avoid rehearsal bias.
   - **Debrief:** Show the calculated CRC excess-time proxy: $\max(0, T_{\text{recovery}} - T_{\text{baseline}})$, latency ratio, and accuracy delta.
   - Click **"Save Trial Record to SQLite"**.

---

## 5. Machine Learning & Anti-Leakage Architecture (2 Minutes)

1. Navigate to **"🔮 6. ML Predictions"**:
   - Show the interactive sliders (Interruption Duration, Baseline Duration, Switches, Complexity).
   - Show the live multi-model prediction comparing Linear Regression, Random Forest, and Gradient Boosting.
   - Explain the **Anti-Leakage Safeguard**:
     > *"A critical engineering contribution here is target leakage prevention. Many student projects accidentally include post-recovery variables like recovery duration in their feature inputs. In ContextIQ, all input features are strictly constrained to pre-recovery measurements. Post-outcome variables are mathematically barred from the training matrix."*

---

## 6. Scientific Research Insights (1 Minute)

1. Navigate to **"🔬 7. Research Insights"**:
   - Show the **Repeated Switching Multiplier**: Repeated switches (Condition C) cause compounded working memory eviction compared to single discrete breaks.
   - Show the **Cognitive Load Amplification**: High complexity tasks suffer $2.4\times$ greater resumption lag.
   - Note the **Goal-Activation Model** decay curve.

---

## 7. Faculty Q&A Prep

**Q: Does your system read private browsing messages?**
> *"No. The extension implements strict privacy-preserving domain sanitization in `core/tracking.py`. Query parameters, search queries, WhatsApp message bodies, and private credentials are stripped before transmission. Only the domain host is recorded."*

**Q: Why is your CRC formula $\max(0, T_{\text{recovery}} - T_{\text{baseline}})$ instead of measuring brainwaves?**
> *"CRC is an operational interaction-latency behavioral proxy. In HCI research, latency overhead is the standard non-invasive proxy for cognitive resumption lag. We explicitly disclaim measuring direct neuroimaging or EEG brainwaves to maintain academic rigor."*


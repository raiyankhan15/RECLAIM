"""
dashboard/run_experiment.py - Controlled Behavioral Experiment Wizard
Executes a multi-stage cognitive context-switch experiment:
Consent -> Baseline Task -> Unexpected Memory Interruption -> Recovery Task -> Performance Debrief.
"""

import time
import streamlit as st
from experiments.experiment import (
    init_experiment_state,
    start_experiment,
    complete_baseline,
    transition_interruption_to_solve,
    complete_interruption,
    complete_recovery,
    get_record_payload,
    PHASE_CONSENT,
    PHASE_BASELINE,
    PHASE_INTERRUPTION_MEMORIZE,
    PHASE_INTERRUPTION_SOLVE,
    PHASE_RECOVERY,
    PHASE_DEBRIEF
)
from database.db import insert_experiment
from config import COMPLEXITY_LEVELS

def get_or_create_state():
    """Initializes or retrieves experiment state from Streamlit session."""
    if "exp_state" not in st.session_state:
        st.session_state["exp_state"] = init_experiment_state()
    return st.session_state["exp_state"]

def reset_experiment():
    """Resets the experiment state to start fresh."""
    st.session_state["exp_state"] = init_experiment_state()
    st.rerun()

def render_run_experiment():
    """Renders the controlled experiment UI."""
    state = get_or_create_state()
    current_phase = state.get("phase", PHASE_CONSENT)

    # Top Control Bar
    top_col1, top_col2 = st.columns([3, 1])
    with top_col1:
        st.markdown('<div class="brand-badge">Controlled Experiment</div>', unsafe_allow_html=True)
        st.title("Context Recovery Behavioral Trial")
    with top_col2:
        if current_phase != PHASE_CONSENT:
            if st.button("Cancel / Restart Trial", type="secondary", use_container_width=True):
                reset_experiment()

    # Stepper Indicator
    steps = [
        ("1. Consent & Setup", PHASE_CONSENT),
        ("2. Baseline Primary Task", PHASE_BASELINE),
        ("3. Secondary Interruption", [PHASE_INTERRUPTION_MEMORIZE, PHASE_INTERRUPTION_SOLVE]),
        ("4. Resumed Primary Task", PHASE_RECOVERY),
        ("5. Performance Debrief", PHASE_DEBRIEF)
    ]

    cols = st.columns(len(steps))
    for i, (label, phase_val) in enumerate(steps):
        is_active = (current_phase == phase_val) if isinstance(phase_val, str) else (current_phase in phase_val)
        is_done = False
        if current_phase == PHASE_DEBRIEF and phase_val != PHASE_DEBRIEF:
            is_done = True
        elif current_phase == PHASE_RECOVERY and phase_val in [PHASE_CONSENT, PHASE_BASELINE, [PHASE_INTERRUPTION_MEMORIZE, PHASE_INTERRUPTION_SOLVE]]:
            is_done = True
        elif current_phase in [PHASE_INTERRUPTION_MEMORIZE, PHASE_INTERRUPTION_SOLVE] and phase_val in [PHASE_CONSENT, PHASE_BASELINE]:
            is_done = True
        elif current_phase == PHASE_BASELINE and phase_val == PHASE_CONSENT:
            is_done = True

        status_class = "active" if is_active else ("completed" if is_done else "")
        with cols[i]:
            st.markdown(f'<div class="step-item {status_class}">{"✓ " if is_done else ""}{label}</div>', unsafe_allow_html=True)

    st.markdown("<hr style='border-color: #1F2937; margin: 16px 0 24px 0;'>", unsafe_allow_html=True)

    # ==========================================
    # PHASE 1: CONSENT & CONFIGURATION
    # ==========================================
    if current_phase == PHASE_CONSENT:
        st.subheader("Participant Information & Informed Consent")
        st.markdown("""
        Welcome to the **RECLAIM Controlled Cognitive Experiment**.
        This study measures interaction-level context recovery latency following task interruptions.
        """)

        with st.form("consent_form"):
            c1, c2 = st.columns(2)
            with c1:
                participant_id = st.text_input(
                    "Participant ID (Anonymous Code):",
                    value=state.get("participant_id") or f"P-{int(time.time()) % 10000:04d}",
                    help="Enter an anonymous identifier (e.g., P-1024 or initials)."
                )

            with c2:
                complexity_choice = st.selectbox(
                    "Select Task Complexity Level:",
                    ["Easy", "Medium", "Difficult"],
                    index=1,
                    format_func=lambda x: COMPLEXITY_LEVELS[x]["label"]
                )
                selected_meta = COMPLEXITY_LEVELS[complexity_choice]
                st.caption(f"{selected_meta['description']} ({selected_meta['num_questions']} questions)")

            st.markdown("""
            <div class="callout">
                <strong>Experiment Protocol:</strong>
                <ol style="margin-top: 6px; padding-left: 20px;">
                    <li>You will complete a primary problem-solving task. Solve questions as accurately and quickly as possible.</li>
                    <li>Work through questions consecutively without external distractions.</li>
                    <li>All collected data is anonymized and utilized strictly for academic research in Context Recovery Cost modeling.</li>
                </ol>
            </div>
            """, unsafe_allow_html=True)

            consent_agreed = st.checkbox(
                "I agree to participate in this cognitive experiment and understand that my interaction timings and response accuracy will be recorded anonymously.",
                value=False
            )

            submit_start = st.form_submit_button("Begin Primary Task", type="primary", use_container_width=True)

            if submit_start:
                if not participant_id.strip():
                    st.error("Please enter a valid Participant ID.")
                elif not consent_agreed:
                    st.error("You must grant informed consent to begin the trial.")
                else:
                    start_experiment(state, participant_id, complexity_choice)
                    st.rerun()

    # ==========================================
    # PHASE 2: BASELINE PRIMARY TASK
    # ==========================================
    elif current_phase == PHASE_BASELINE:
        st.subheader("Phase 1: Primary Task (Baseline Condition)")
        st.info("Solve the questions below as quickly and accurately as possible. Timer is running.")

        questions = state.get("baseline_questions", [])
        with st.form("baseline_form"):
            user_answers = {}
            for idx, q in enumerate(questions):
                st.markdown(f"**Question {idx + 1}:** {q['prompt']}")
                user_answers[idx] = st.radio(
                    f"Select answer for Q{idx + 1}:",
                    q["options"],
                    key=f"base_q_{idx}",
                    horizontal=True
                )
                st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

            submit_baseline = st.form_submit_button("Submit Baseline Answers", type="primary", use_container_width=True)
            if submit_baseline:
                complete_baseline(state, user_answers)
                st.rerun()

    # ==========================================
    # PHASE 3A: INTERRUPTION - MEMORIZATION STIMULUS
    # ==========================================
    elif current_phase == PHASE_INTERRUPTION_MEMORIZE:
        st.warning("⚠️ CONTEXT SWITCH DETECTED: Secondary Task Interruption")
        st.markdown("""
        **Unexpected Secondary Challenge**: Your primary task has been suspended.
        Memorize the token sequence displayed below. You will be tested on it in a moment.
        """)

        mem = state.get("memory_challenge", {})
        tokens = mem.get("tokens", [])

        # Display Memory Tokens
        st.markdown('<div class="stimulus-box">', unsafe_allow_html=True)
        token_html = "".join([f'<span class="token-pill">{t}</span>' for t in tokens])
        st.markdown(token_html, unsafe_allow_html=True)
        st.markdown('<div style="color: #9CA3AF; margin-top: 12px; font-size: 0.85rem;">Study the exact positions of these tokens. Click below when ready.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("I have memorized the sequence — Proceed to Challenge", type="primary", use_container_width=True):
            transition_interruption_to_solve(state)
            st.rerun()

    # ==========================================
    # PHASE 3B: INTERRUPTION - SOLVE DISTRACTORS & RECALL
    # ==========================================
    elif current_phase == PHASE_INTERRUPTION_SOLVE:
        st.warning("⚠️ CONTEXT SWITCH: Active Interruption Task")
        st.markdown("Solve the distractor checks, then recall the requested token from memory.")

        mem = state.get("memory_challenge", {})
        distractors = mem.get("distractors", [])

        with st.form("interruption_solve_form"):
            user_interr_answers = {}
            st.markdown("#### Cognitive Distractor Checks")
            for i, d in enumerate(distractors):
                st.markdown(f"**Check {i + 1}:** {d['question']}")
                user_interr_answers[f"distractor_{i}"] = st.radio(
                    f"Select answer for check {i + 1}:",
                    d["options"],
                    key=f"interr_dist_{i}",
                    horizontal=True
                )

            st.markdown("<hr style='border-color: #1F2937; margin: 16px 0;'>", unsafe_allow_html=True)
            st.markdown("#### Memory Sequence Recall")
            st.markdown(f"**Recall Query:** {mem.get('recall_prompt')}")
            user_interr_answers["recall"] = st.radio(
                "Select recalled token:",
                mem.get("recall_options", []),
                key="interr_recall",
                horizontal=True
            )

            submit_interr = st.form_submit_button("Submit Interruption Answers", type="primary", use_container_width=True)
            if submit_interr:
                complete_interruption(state, user_interr_answers)
                st.rerun()

    # ==========================================
    # PHASE 4: RECOVERY TASK (RESUMED PRIMARY)
    # ==========================================
    elif current_phase == PHASE_RECOVERY:
        st.success("🔄 RESUMING PRIMARY TASK: Context Recovery Condition")
        st.info("You are now returning to your original problem-solving task. Solve the new questions below as accurately and quickly as possible.")

        recovery_questions = state.get("recovery_questions", [])
        with st.form("recovery_form"):
            user_rec_answers = {}
            for idx, q in enumerate(recovery_questions):
                st.markdown(f"**Question {idx + 1}:** {q['prompt']}")
                user_rec_answers[idx] = st.radio(
                    f"Select answer for Q{idx + 1}:",
                    q["options"],
                    key=f"rec_q_{idx}",
                    horizontal=True
                )
                st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

            submit_recovery = st.form_submit_button("Submit Recovery Answers", type="primary", use_container_width=True)
            if submit_recovery:
                complete_recovery(state, user_rec_answers)
                st.rerun()

    # ==========================================
    # PHASE 5: PERFORMANCE DEBRIEF & METRICS
    # ==========================================
    elif current_phase == PHASE_DEBRIEF:
        st.balloons()
        st.markdown('<div class="brand-badge" style="background: rgba(16,185,129,0.15); border-color: rgba(16,185,129,0.4); color: #34D399;">Trial Completed</div>', unsafe_allow_html=True)
        st.title("Context Recovery Analysis Report")
        st.markdown(f"Participant **{state['participant_id']}** &nbsp;|&nbsp; Complexity **{state['task_complexity']} (Level {state['complexity_level']})**")

        # Debrief KPI Cards
        d_col1, d_col2, d_col3, d_col4 = st.columns(4)
        with d_col1:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">Baseline Duration</div>
                <div class="kpi-value">{state['baseline_duration']:.2f}s</div>
                <div class="kpi-subtitle">Accuracy: {state['baseline_accuracy']*100:.0f}%</div>
            </div>
            """, unsafe_allow_html=True)

        with d_col2:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">Interruption Duration</div>
                <div class="kpi-value">{state['interruption_duration']:.2f}s</div>
                <div class="kpi-subtitle">Distractor Acc: {state['interruption_accuracy']*100:.0f}%</div>
            </div>
            """, unsafe_allow_html=True)

        with d_col3:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">Recovery Duration</div>
                <div class="kpi-value">{state['recovery_duration']:.2f}s</div>
                <div class="kpi-subtitle">Accuracy: {state['recovery_accuracy']*100:.0f}%</div>
            </div>
            """, unsafe_allow_html=True)

        with d_col4:
            crc_color = "#EF4444" if state['crc_excess_time'] > 10 else ("#F59E0B" if state['crc_excess_time'] > 3 else "#10B981")
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">Context Recovery Cost (CRC)</div>
                <div class="kpi-value" style="color: {crc_color};">+{state['crc_excess_time']:.2f}s</div>
                <div class="kpi-subtitle">Time Ratio: {state['crc_ratio']:.2f}x</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

        # Operational Analysis Breakdown
        acc_delta = state['accuracy_diff'] * 100.0
        acc_delta_str = f"+{acc_delta:.1f}%" if acc_delta >= 0 else f"{acc_delta:.1f}%"

        st.markdown(f"""
        <div class="callout">
            <strong>Cognitive Resumption Breakdown:</strong>
            <ul style="margin-top: 6px; padding-left: 20px;">
                <li><strong>Excess-Time Proxy:</strong> You required <strong>{state['crc_excess_time']:.2f} seconds</strong> of additional processing time to complete the post-interruption task compared to baseline.</li>
                <li><strong>Time Inflation Factor:</strong> Your post-interruption task took <strong>{state['crc_ratio']:.2f} times</strong> your uninterrupted baseline speed.</li>
                <li><strong>Accuracy Shift:</strong> Accuracy delta was <strong>{acc_delta_str}</strong> (Baseline {state['baseline_accuracy']*100:.0f}% vs Recovery {state['recovery_accuracy']*100:.0f}%).</li>
                <li><strong>Total Errors:</strong> {state['error_count']} incorrect answer(s) across all phases.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        # Action Buttons: Save & New Experiment
        act_col1, act_col2 = st.columns([1, 1])

        with act_col1:
            if not state.get("is_saved", False):
                if st.button("Save Trial to Database (SQLite)", type="primary", use_container_width=True):
                    payload = get_record_payload(state)
                    success, msg = insert_experiment(payload)
                    if success:
                        state["is_saved"] = True
                        st.success("Session saved successfully to SQLite database!")
                        st.rerun()
                    else:
                        st.error(f"Error saving session: {msg}")
            else:
                st.success("Record is securely stored in SQLite database.")

        with act_col2:
            if st.button("Start Another Experiment Run", type="secondary", use_container_width=True):
                reset_experiment()


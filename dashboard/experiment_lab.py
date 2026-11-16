"""
dashboard/experiment_lab.py - Controlled Research Experiment Suite
Implements the 4 experimental research proposal conditions:
Condition A: CONTROL
Condition B: SINGLE SWITCH
Condition C: REPEATED SWITCH
Condition D: HIGH COMPLEXITY
"""

import time
import streamlit as st
from core.experiment import (
    init_condition_state,
    record_condition_trial_to_db,
    CONDITIONS_META,
    COND_CONTROL,
    COND_SINGLE,
    COND_REPEATED,
    COND_COMPLEX
)
from core.recovery import evaluate_recovery_progression, STATUS_RECOVERED, STATUS_INCOMPLETE
from core.crc import calculate_crc_excess_time, calculate_crc_ratio

def get_or_init_lab_state():
    if "lab_state" not in st.session_state:
        st.session_state["lab_state"] = init_condition_state(COND_SINGLE, "P-101")
    return st.session_state["lab_state"]

def reset_lab_state(condition=COND_SINGLE, pid=""):
    st.session_state["lab_state"] = init_condition_state(condition, pid)
    st.rerun()

def render_experiment_lab():
    """Renders the interactive 4-condition experiment lab."""
    state = get_or_init_lab_state()
    current_phase = state.get("phase", "SETUP")

    st.markdown('<div class="brand-badge">Controlled Research Lab</div>', unsafe_allow_html=True)
    st.title("Behavioral Experiment Suite")
    st.markdown(
        "Execute the four controlled experimental conditions from the research proposal: "
        "**Control**, **Single Switch**, **Repeated Switch**, and **High Complexity**."
    )

    # Condition Selector & Cancel Bar
    top_col1, top_col2 = st.columns([3, 1])
    with top_col1:
        cond_meta = CONDITIONS_META.get(state["condition"], CONDITIONS_META[COND_SINGLE])
        st.markdown(f"**Current Condition:** `{cond_meta['name']}` — *{cond_meta['description']}*")
    with top_col2:
        if current_phase != "SETUP":
            if st.button("Cancel / Restart Trial", type="secondary", use_container_width=True):
                reset_lab_state(state["condition"], state["participant_id"])

    # Phase Indicator
    phases = ["SETUP", "BASELINE", "INTERRUPTION", "RECOVERY", "DEBRIEF"]
    p_cols = st.columns(len(phases))
    for i, p in enumerate(phases):
        is_active = (current_phase == p or (current_phase.startswith("INTERRUPT") and p == "INTERRUPTION"))
        status_cls = "active" if is_active else ""
        with p_cols[i]:
            st.markdown(f'<div class="step-item {status_cls}">{i+1}. {p}</div>', unsafe_allow_html=True)

    st.markdown("<hr style='border-color: #1F2937; margin: 16px 0;'>", unsafe_allow_html=True)

    # ==========================================
    # STAGE 1: SETUP & CONSENT
    # ==========================================
    if current_phase == "SETUP":
        st.subheader("1. Protocol Configuration & Participant Consent")

        with st.form("lab_setup_form"):
            c1, c2 = st.columns(2)
            with c1:
                selected_cond = st.selectbox(
                    "Select Research Condition:",
                    [COND_CONTROL, COND_SINGLE, COND_REPEATED, COND_COMPLEX],
                    format_func=lambda x: CONDITIONS_META[x]["name"],
                    index=[COND_CONTROL, COND_SINGLE, COND_REPEATED, COND_COMPLEX].index(state["condition"])
                )
                pid = st.text_input("Anonymous Participant ID:", value=state.get("participant_id") or f"P-{int(time.time())%10000:04d}")

            with c2:
                meta = CONDITIONS_META[selected_cond]
                st.markdown(f"""
                <div class="callout" style="height: 100%;">
                    <strong>Condition Protocol:</strong>
                    <p style="margin-top: 4px;">{meta['description']}</p>
                    <p><strong>Complexity:</strong> {meta['default_complexity']} | <strong>Expected Switches:</strong> {meta['expected_switches']}</p>
                </div>
                """, unsafe_allow_html=True)

            consent = st.checkbox("I grant informed consent to participate in this controlled context recovery experiment.")

            start_btn = st.form_submit_button("Start Experimental Trial", type="primary", use_container_width=True)

            if start_btn:
                if not consent:
                    st.error("Informed consent is required.")
                else:
                    st.session_state["lab_state"] = init_condition_state(selected_cond, pid)
                    st.session_state["lab_state"]["phase"] = "BASELINE"
                    st.session_state["lab_state"]["baseline_start"] = time.time()
                    st.rerun()

    # ==========================================
    # STAGE 2: BASELINE TASK
    # ==========================================
    elif current_phase == "BASELINE":
        st.subheader("Phase 1: Baseline Performance Establishment")
        st.info("Solve the problem set below as accurately and quickly as possible. Baseline timer is running.")

        questions = state.get("baseline_questions", [])
        with st.form("baseline_lab_form"):
            user_answers = {}
            for idx, q in enumerate(questions):
                st.markdown(f"**Question {idx + 1}:** {q['prompt']}")
                user_answers[idx] = st.radio(f"Select answer Q{idx+1}:", q["options"], key=f"lab_base_{idx}", horizontal=True)

            submit_b = st.form_submit_button("Submit Baseline Set", type="primary", use_container_width=True)
            if submit_b:
                now = time.time()
                dur = round(now - state["baseline_start"], 2)
                correct = sum(1 for idx, q in enumerate(questions) if user_answers.get(idx) == q["answer"])
                acc = round(correct / len(questions), 3)

                state["baseline_duration_sec"] = dur
                state["baseline_accuracy"] = acc

                # Transition depending on condition
                if state["condition"] == COND_CONTROL:
                    # In CONTROL condition, no interruption! Goes directly to recovery set to measure zero-interruption variance.
                    state["phase"] = "RECOVERY"
                    state["interruption_duration_sec"] = 0.0
                    state["switch_count"] = 0
                    state["recovery_start"] = time.time()
                else:
                    state["phase"] = "INTERRUPT_MEMORIZE"
                    state["interruption_start"] = time.time()
                    state["switch_count"] = 1
                st.rerun()

    # ==========================================
    # STAGE 3A: INTERRUPTION - MEMORIZE
    # ==========================================
    elif current_phase == "INTERRUPT_MEMORIZE":
        st.warning("⚠️ CONTEXT SWITCH DETECTED: Secondary Task Interruption")
        st.markdown("**Unexpected Interruption**: Study the sequence below before proceeding to the distractor challenge.")

        mem = state.get("memory_challenge_1", {})
        tokens = mem.get("tokens", [])

        st.markdown('<div class="stimulus-box">', unsafe_allow_html=True)
        token_html = "".join([f'<span class="token-pill">{t}</span>' for t in tokens])
        st.markdown(token_html, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("I have memorized the tokens — Proceed to Challenge", type="primary", use_container_width=True):
            state["phase"] = "INTERRUPT_SOLVE"
            st.rerun()

    # ==========================================
    # STAGE 3B: INTERRUPTION - SOLVE DISTRACTORS
    # ==========================================
    elif current_phase == "INTERRUPT_SOLVE":
        st.warning("⚠️ Active Interruption Challenge")
        mem = state.get("memory_challenge_1", {})
        distractors = mem.get("distractors", [])

        with st.form("interr_lab_form"):
            user_interr = {}
            for i, d in enumerate(distractors):
                st.markdown(f"**Check {i + 1}:** {d['question']}")
                user_interr[f"dist_{i}"] = st.radio(f"Check {i+1}:", d["options"], key=f"lab_dist_{i}", horizontal=True)

            st.markdown(f"**Recall Query:** {mem.get('recall_prompt')}")
            user_interr["recall"] = st.radio("Recalled Token:", mem.get("recall_options", []), key="lab_recall", horizontal=True)

            submit_i = st.form_submit_button("Submit Interruption Answers", type="primary", use_container_width=True)
            if submit_i:
                now = time.time()
                interr_dur = round(now - state["interruption_start"], 2)
                state["interruption_duration_sec"] = interr_dur

                if state["condition"] == COND_REPEATED:
                    state["switch_count"] = 4  # Repeated switch count
                else:
                    state["switch_count"] = 2

                state["phase"] = "RECOVERY"
                state["recovery_start"] = time.time()
                st.rerun()

    # ==========================================
    # STAGE 4: RECOVERY TASK (RESUMED TASK A)
    # ==========================================
    elif current_phase == "RECOVERY":
        st.success("🔄 RESUMING PRIMARY TASK: Context Recovery Condition")
        st.info("You are now returning to the primary problem-solving task. Solve the equivalent questions below.")

        questions = state.get("recovery_questions", [])
        with st.form("recovery_lab_form"):
            user_rec = {}
            for idx, q in enumerate(questions):
                st.markdown(f"**Question {idx + 1}:** {q['prompt']}")
                user_rec[idx] = st.radio(f"Select answer Q{idx+1}:", q["options"], key=f"lab_rec_{idx}", horizontal=True)

            submit_r = st.form_submit_button("Submit Recovery Set", type="primary", use_container_width=True)
            if submit_r:
                now = time.time()
                rec_dur = round(now - state["recovery_start"], 2)
                correct = sum(1 for idx, q in enumerate(questions) if user_rec.get(idx) == q["answer"])
                rec_acc = round(correct / len(questions), 3)

                state["recovery_duration_sec"] = rec_dur
                state["recovery_accuracy"] = rec_acc

                # Evaluate Recovery Against Baseline Thresholds
                # Primary CRC excess-time proxy = max(0, recovery - baseline)
                excess_time = calculate_crc_excess_time(state["baseline_duration_sec"], rec_dur)
                ratio = calculate_crc_ratio(state["baseline_duration_sec"], rec_dur)

                state["crc_seconds"] = excess_time
                state["crc_ratio"] = ratio

                # Check if baseline criteria was regained
                is_recovered = (rec_dur <= state["baseline_duration_sec"] * 1.25) and (rec_acc >= state["baseline_accuracy"] * 0.90)
                state["recovery_status"] = STATUS_RECOVERED if is_recovered else STATUS_INCOMPLETE

                state["phase"] = "DEBRIEF"
                st.rerun()

    # ==========================================
    # STAGE 5: DEBRIEF & PERSISTENCE
    # ==========================================
    elif current_phase == "DEBRIEF":
        st.balloons()
        st.markdown('<div class="brand-badge" style="background: rgba(16,185,129,0.15); border-color: rgba(16,185,129,0.4); color: #34D399;">Trial Complete</div>', unsafe_allow_html=True)
        st.title("Experimental Trial Debrief")
        st.markdown(f"Condition: **{state['condition']}** &nbsp;|&nbsp; Participant: **{state['participant_id']}** &nbsp;|&nbsp; Status: **{state['recovery_status']}**")

        # Metric summary cards
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">Baseline Duration</div>
                <div class="kpi-value">{state['baseline_duration_sec']:.2f}s</div>
                <div class="kpi-subtitle">Accuracy: {state['baseline_accuracy']*100:.0f}%</div>
            </div>
            """, unsafe_allow_html=True)

        with c2:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">Interruption Duration</div>
                <div class="kpi-value">{state['interruption_duration_sec']:.2f}s</div>
                <div class="kpi-subtitle">Switches: {state['switch_count']}</div>
            </div>
            """, unsafe_allow_html=True)

        with c3:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">Recovery Duration</div>
                <div class="kpi-value">{state['recovery_duration_sec']:.2f}s</div>
                <div class="kpi-subtitle">Accuracy: {state['recovery_accuracy']*100:.0f}%</div>
            </div>
            """, unsafe_allow_html=True)

        with c4:
            crc_col = "#10B981" if state["crc_seconds"] < 4 else ("#F59E0B" if state["crc_seconds"] < 15 else "#EF4444")
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">Context Recovery Cost (CRC)</div>
                <div class="kpi-value" style="color: {crc_col};">+{state['crc_seconds']:.2f}s</div>
                <div class="kpi-subtitle">Ratio: {state['crc_ratio']:.2f}x</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

        # Database Commit
        a1, a2 = st.columns(2)
        with a1:
            if not state.get("is_saved", False):
                if st.button("Save Trial Record to SQLite", type="primary", use_container_width=True):
                    success, msg = record_condition_trial_to_db(state)
                    if success:
                        state["is_saved"] = True
                        st.success("Experimental trial stored in SQLite database!")
                        st.rerun()
                    else:
                        st.error(f"Error saving record: {msg}")
            else:
                st.success("Trial record securely archived in database.")

        with a2:
            if st.button("Run Another Condition Trial", type="secondary", use_container_width=True):
                reset_lab_state(state["condition"], state["participant_id"])


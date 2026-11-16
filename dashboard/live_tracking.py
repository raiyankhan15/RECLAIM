"""
dashboard/live_tracking.py - Real-Time Browser Extension Session Monitor
Streams active session status, current tab domain, live interruption timer,
and recent switch timelines ingested from the Chrome Extension.
"""

import time
import streamlit as st
import pandas as pd
from datetime import datetime
from backend.database import get_connection

def render_live_tracking():
    """Renders real-time live tracking session telemetry."""
    st.markdown('<div class="brand-badge">Extension Telemetry</div>', unsafe_allow_html=True)
    st.title("Live Browser Session Tracking")
    st.markdown(
        "Real-time event feed powered by the **RECLAIM Chrome Extension** (Manifest V3) "
        "and FastAPI backend (`http://localhost:8000`)."
    )

    # Top refresh bar
    r_col1, r_col2 = st.columns([3, 1])
    with r_col1:
        st.caption("Active telemetry polling directly from SQLite session log.")
    with r_col2:
        if st.button("🔄 Refresh Telemetry", type="primary", use_container_width=True):
            st.rerun()

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tracking_sessions ORDER BY start_time DESC LIMIT 1")
        session_row = cursor.fetchone()

        if not session_row:
            st.info("No browser tracking session active. Start tracking using the Chrome Extension!")
            st.markdown("""
            <div class="callout">
                <strong>How to start tracking:</strong>
                <ol style="margin-top: 6px; padding-left: 20px;">
                    <li>Ensure FastAPI backend is running: <code>.venv/bin/uvicorn backend.main:app --port 8000</code></li>
                    <li>Open Chrome and navigate to your working tab (e.g., GitHub, VS Code Web, Docs).</li>
                    <li>Click the RECLAIM extension icon and select <strong>"Set Current Tab as Primary Task"</strong>.</li>
                    <li>Switch tabs — RECLAIM will automatically log switches and interruptions!</li>
                </ol>
            </div>
            """, unsafe_allow_html=True)
            return

        session = dict(session_row)
        sess_id = session["session_id"]

        # Fetch recent switch events
        cursor.execute("""
            SELECT timestamp, from_tab_id, to_tab_id, to_domain, to_category, duration_on_tab, is_primary, is_interruption
            FROM tab_switch_events
            WHERE session_id = ?
            ORDER BY timestamp DESC LIMIT 15
        """, (sess_id,))
        recent_switches = [dict(r) for r in cursor.fetchall()]

        # Fetch recent interruption episodes
        cursor.execute("""
            SELECT episode_id, start_time, end_time, duration_sec, switch_count, visited_domains, primary_interruption_category
            FROM interruption_episodes
            WHERE session_id = ?
            ORDER BY start_time DESC LIMIT 10
        """, (sess_id,))
        recent_episodes = [dict(r) for r in cursor.fetchall()]

    finally:
        conn.close()

    status = session.get("status", "ACTIVE")
    is_active = (status == "ACTIVE")
    last_switch = recent_switches[0] if recent_switches else None
    is_currently_interrupted = (last_switch and not last_switch["is_primary"]) if last_switch else False

    # Status Banner
    if is_currently_interrupted:
        st.markdown(f"""
        <div style="background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.4); border-radius: 8px; padding: 16px; margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="color: #EF4444; font-weight: 700; font-size: 1.1rem;">⚠️ INTERRUPTED: Away from Primary Task</span>
                    <div style="color: #D1D5DB; margin-top: 4px;">Currently on: <strong>{last_switch['to_domain']}</strong> ({last_switch['to_category']})</div>
                </div>
                <div style="font-size: 1.5rem; font-weight: 700; font-family: monospace; color: #EF4444;">
                    Active Episode
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.4); border-radius: 8px; padding: 16px; margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="color: #34D399; font-weight: 700; font-size: 1.1rem;">✓ ACTIVE: Focused on Primary Task</span>
                    <div style="color: #D1D5DB; margin-top: 4px;">Primary Domain: <strong>{session['primary_domain']}</strong> ({session['primary_category']})</div>
                </div>
                <div style="font-size: 0.85rem; color: #9CA3AF;">
                    Session: <code>{sess_id[:16]}...</code>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Telemetry KPI row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Primary Domain</div>
            <div class="kpi-value" style="font-size: 1.3rem;">{session['primary_domain']}</div>
            <div class="kpi-subtitle">Category: {session['primary_category']}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Total Tab Switches</div>
            <div class="kpi-value">{session['total_switches']}</div>
            <div class="kpi-subtitle">In this session</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Interruption Time</div>
            <div class="kpi-value">{session['total_interruption_time']:.1f}s</div>
            <div class="kpi-subtitle">Total time away from primary</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Interruption Episodes</div>
            <div class="kpi-value">{len(recent_episodes)}</div>
            <div class="kpi-subtitle">Completed departure cycles</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # Event Timeline & Episode Details
    t_col1, t_col2 = st.columns([1.2, 1])

    with t_col1:
        st.subheader("Live Event Stream (Recent Tab Switches)")
        if recent_switches:
            ev_df = pd.DataFrame(recent_switches)
            ev_df["Type"] = ev_df["is_primary"].apply(lambda p: "🎯 PRIMARY TASK" if p == 1 else "⚡ INTERRUPTION")
            ev_df["Time"] = ev_df["timestamp"].apply(lambda t: str(t)[11:19])
            st.dataframe(
                ev_df[["Time", "Type", "to_domain", "to_category", "duration_on_tab"]].rename(
                    columns={"to_domain": "Domain", "to_category": "Category", "duration_on_tab": "Dwell (s)"}
                ),
                use_container_width=True,
                height=280
            )
        else:
            st.info("No tab switch events logged in this session yet.")

    with t_col2:
        st.subheader("Grouped Interruption Episodes")
        if recent_episodes:
            ep_df = pd.DataFrame(recent_episodes)
            ep_df["Start"] = ep_df["start_time"].apply(lambda t: str(t)[11:19])
            st.dataframe(
                ep_df[["Start", "duration_sec", "switch_count", "primary_interruption_category"]].rename(
                    columns={"duration_sec": "Duration (s)", "switch_count": "Switches", "primary_interruption_category": "Category"}
                ),
                use_container_width=True,
                height=280
            )
        else:
            st.info("No completed interruption episodes yet.")


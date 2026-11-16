"""
dashboard/overview.py - RECLAIM Main Dashboard
Architecture & Layout Structure:
1. Your Productivity at a Glance
   - Header with RECLAIM branding, title, subtitle, date, segmented period filter, status pill.
   - Primary Task Indicator Panel (Domain, Category, Tracking Status, Session Duration).
   - Three Main Metric Cards (Interruptions, Time Away, Context Recovery Cost).
2. Focus Timeline (Signature Visual Feature)
   - Large continuous horizontal timeline of actual work session.
   - Segments: Teal (#43C6AC) for Primary Task, Amber (#E9A23B) for Interruption, Grey (#6B7280) for Idle/Paused.
   - Proportional segment widths, rich hover tooltips, time axis, color legend.
3. Interruption Breakdown
   - Clean horizontal bar chart showing top interruption websites/categories.
   - Values at ends of bars, percentage of time away, counts, tooltips, sorted.
4. Recovery Trend
   - Clean line chart across genuinely measured recovery observations.
   - Informative empty state when real measured observations are insufficient.
"""


import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timezone
from backend.database import get_connection

BG = "#0B0F12"
CARD = "#151D23"
TEAL = "#43C6AC"
AMBER = "#E9A23B"
GREY = "#6B7280"
TEXT = "#F4F6F8"
MUTED = "#89949E"


def format_duration(seconds):
    if pd.isna(seconds) or seconds < 0:
        return "0s"

    seconds = int(round(seconds))
    minutes, seconds = divmod(seconds, 60)

    if minutes == 0:
        return f"{seconds}s"

    return f"{minutes}m {seconds:02d}s"


def fetch_dashboard_data():
    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM tracking_sessions
            ORDER BY start_time DESC
        """)
        sessions = [dict(r) for r in cursor.fetchall()]

        cursor.execute("""
            SELECT *
            FROM interruption_episodes
            ORDER BY start_time DESC
        """)
        episodes = [dict(r) for r in cursor.fetchall()]

        cursor.execute("""
            SELECT *
            FROM tab_switch_events
            ORDER BY timestamp ASC
        """)
        switches = [dict(r) for r in cursor.fetchall()]

        cursor.execute("""
            SELECT *
            FROM controlled_experiments
        """)
        experiments = [dict(r) for r in cursor.fetchall()]

    finally:
        conn.close()

    return sessions, episodes, switches, experiments


def render_overview():

    sessions, episodes, switches, experiments = fetch_dashboard_data()

    now = datetime.now(timezone.utc)

    latest = sessions[0] if sessions else None

    # Header
    st.markdown("""
    <div style="margin-bottom:25px;">
        <div style="color:#43C6AC;font-size:12px;
                    font-weight:700;letter-spacing:3px;">
            RECLAIM
        </div>
        <h1 style="margin:4px 0 0 0;font-size:32px;">
            RECLAIM IQ Dashboard
        </h1>
        <p style="color:#89949E;margin-top:5px;">
            Understand your interruptions. Reclaim your focus.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Current task information
    status = latest.get("status", "STOPPED") if latest else "STOPPED"

    domain = (
        latest.get("primary_domain")
        if latest else None
    )

    category = (
        latest.get("primary_category")
        if latest else None
    )

    if latest:
        session_id = latest.get("session_id")

        current_episodes = [
            e for e in episodes
            if e.get("session_id") == session_id
        ]

        completed_interruptions = len(current_episodes)

        time_away = sum(
            float(e.get("duration_sec") or 0)
            for e in current_episodes
        )

    else:
        completed_interruptions = 0
        time_away = 0

    # Only genuinely measured CRC
    real_trials = [
        e for e in experiments
        if e.get("data_source") == "REAL_EXPERIMENT"
        and e.get("crc_seconds") is not None
    ]

    crc = (
        sum(float(e["crc_seconds"]) for e in real_trials)
        / len(real_trials)
        if real_trials else None
    )

    # KPI cards
    st.markdown("### Today's Overview")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "Interruptions",
            completed_interruptions
        )

    with c2:
        st.metric(
            "Time Away",
            format_duration(time_away)
        )

    with c3:
        st.metric(
            "Average Measured CRC",
            format_duration(crc) if crc is not None else "—"
        )

    st.markdown("---")

    # Focus Timeline
    st.markdown("### Focus Timeline")
    st.caption("A visual overview of your latest tracking session.")

    timeline = []

    if latest and switches:

        session_switches = [
            s for s in switches
            if s.get("session_id") == latest.get("session_id")
        ]

        session_switches.sort(key=lambda x: x.get("timestamp") or "")

        start = pd.to_datetime(
            latest.get("start_time"),
            utc=True,
            errors="coerce"
        )

        end_value = latest.get("end_time")

        end = (
            pd.to_datetime(end_value, utc=True, errors="coerce")
            if end_value else pd.Timestamp.now(tz="UTC")
        )

        if pd.notna(start) and pd.notna(end):

            previous_time = start
            previous_type = "Primary Task"

            for event in session_switches:

                event_time = pd.to_datetime(
                    event.get("timestamp"),
                    utc=True,
                    errors="coerce"
                )

                if pd.isna(event_time) or event_time <= previous_time:
                    continue

                timeline.append({
                    "Start": previous_time,
                    "Finish": event_time,
                    "Activity": previous_type
                })

                is_primary = event.get("is_primary") in (1, True)

                previous_type = (
                    "Primary Task"
                    if is_primary else "Interruption"
                )

                previous_time = event_time

            if end > previous_time:

                final_type = (
                    "Idle / Paused"
                    if latest.get("status") == "PAUSED"
                    else previous_type
                )

                timeline.append({
                    "Start": previous_time,
                    "Finish": end,
                    "Activity": final_type
                })

    if timeline:

        timeline_df = pd.DataFrame(timeline)

        fig = px.timeline(
            timeline_df,
            x_start="Start",
            x_end="Finish",
            y=["Latest Session"] * len(timeline_df),
            color="Activity",
            color_discrete_map={
                "Primary Task": TEAL,
                "Interruption": AMBER,
                "Idle / Paused": GREY
            }
        )

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor=CARD,
            height=150,
            margin=dict(l=5, r=5, t=15, b=35),
            legend=dict(
                orientation="h",
                y=-0.35
            ),
            yaxis=dict(visible=False),
            xaxis=dict(
                title="",
                gridcolor="#26313A"
            )
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    else:
        st.info(
            "No timeline available yet. Start a tracking session "
            "using the RECLAIM Chrome Extension."
        )

    st.markdown("---")

    # Current Primary Task
    st.markdown("### Current Primary Task")

    col1, col2 = st.columns([3, 1])

    with col1:

        if domain and domain not in ("blank", "None", ""):
            st.markdown(f"**{domain}**")
            st.caption(category or "General Work")
        else:
            st.markdown("**No primary task selected**")
            st.caption("Choose a primary tab using the Chrome extension.")

    with col2:

        if status == "ACTIVE":
            st.success("Tracking Active")
        elif status == "PAUSED":
            st.warning("Tracking Paused")
        else:
            st.caption("Tracking Stopped")

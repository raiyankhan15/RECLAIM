"""
dashboard/overview.py - RECLAIM main dashboard.

1. Header + KPI cards (Interruptions, Time Away, Average Measured CRC)
2. One-line insight about the latest session
3. Focus Timeline (zoomed to the real session window)
4. Current primary task
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timezone
from backend.database import get_connection

CARD = "#11171C"
TEAL = "#43C6AC"
AMBER = "#E9A23B"
GREY = "#6B7280"
GRID = "#1F2A33"


def format_duration(seconds):
    if seconds is None or pd.isna(seconds) or seconds < 0:
        return "0s"
    seconds = int(round(seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes:02d}m"
    if minutes:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"


def fetch_dashboard_data():
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM tracking_sessions ORDER BY start_time DESC")
        sessions = [dict(r) for r in cur.fetchall()]
        cur.execute("SELECT * FROM interruption_episodes ORDER BY start_time DESC")
        episodes = [dict(r) for r in cur.fetchall()]
        cur.execute("SELECT * FROM tab_switch_events ORDER BY timestamp ASC")
        switches = [dict(r) for r in cur.fetchall()]
        cur.execute("SELECT * FROM controlled_experiments")
        experiments = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
    return sessions, episodes, switches, experiments


def measured_crc_values(episodes, experiments):
    """All genuinely measured recovery times, in seconds.
    - live tracking: interruption_episodes.measured_recovery_sec
    - lab trials:    controlled_experiments.crc_seconds (REAL_EXPERIMENT only)
    """
    values = [
        float(e["measured_recovery_sec"])
        for e in episodes
        if e.get("measured_recovery_sec") is not None and float(e["measured_recovery_sec"]) >= 0
    ]
    values += [
        float(x["crc_seconds"])
        for x in experiments
        if x.get("data_source") == "REAL_EXPERIMENT" and x.get("crc_seconds") is not None
    ]
    return values


def build_timeline(latest, switches):
    """Return a list of {Start, Finish, Activity} segments for the latest session."""
    if not latest:
        return []

    session_switches = [s for s in switches if s.get("session_id") == latest.get("session_id")]
    session_switches.sort(key=lambda x: x.get("timestamp") or "")

    start = pd.to_datetime(latest.get("start_time"), utc=True, errors="coerce")
    if pd.isna(start):
        return []

    # End of the window: recorded end, else "now" only if still tracking,
    # else the last event we actually saw (avoids a bar stretching for hours/days).
    end_value = latest.get("end_time")
    last_event = None
    if session_switches:
        last_event = pd.to_datetime(session_switches[-1].get("timestamp"), utc=True, errors="coerce")

    if end_value:
        end = pd.to_datetime(end_value, utc=True, errors="coerce")
    elif latest.get("status") == "ACTIVE":
        end = pd.Timestamp.now(tz="UTC")
    else:
        end = last_event if last_event is not None and pd.notna(last_event) else start

    if pd.isna(end) or end <= start:
        return []

    segments, prev_time, prev_type = [], start, "Primary Task"
    for ev in session_switches:
        t = pd.to_datetime(ev.get("timestamp"), utc=True, errors="coerce")
        if pd.isna(t) or t <= prev_time:
            continue
        if t > end:
            break
        segments.append({"Start": prev_time, "Finish": t, "Activity": prev_type})
        prev_type = "Primary Task" if ev.get("is_primary") in (1, True) else "Interruption"
        prev_time = t

    if end > prev_time:
        final_type = "Idle / Paused" if latest.get("status") == "PAUSED" else prev_type
        segments.append({"Start": prev_time, "Finish": end, "Activity": final_type})
    return segments


def render_overview():
    sessions, episodes, switches, experiments = fetch_dashboard_data()
    latest = sessions[0] if sessions else None

    # ---------- Header ----------
    st.title("Dashboard")
    st.caption(f"{datetime.now(timezone.utc).astimezone().strftime('%A, %d %B %Y')}  |  Understand your interruptions. Reclaim your focus.")

    status = latest.get("status", "STOPPED") if latest else "STOPPED"
    domain = latest.get("primary_domain") if latest else None
    category = latest.get("primary_category") if latest else None

    current_episodes = [e for e in episodes if latest and e.get("session_id") == latest.get("session_id")]
    interruptions = len(current_episodes)
    time_away = sum(float(e.get("duration_sec") or 0) for e in current_episodes)

    crc_values = measured_crc_values(episodes, experiments)
    crc = sum(crc_values) / len(crc_values) if crc_values else None

    # ---------- KPIs ----------
    st.subheader("Today's overview")
    latencies = [
        float(e["return_latency_sec"])
        for e in episodes
        if e.get("return_latency_sec") is not None and float(e["return_latency_sec"]) >= 0
    ]
    cols = st.columns(4 if latencies else 3)
    c1, c2, c3 = cols[:3]
    with c1:
        st.metric("Interruptions", interruptions, help="Times you left your primary task in the latest session.")
    with c2:
        st.metric("Time away", format_duration(time_away), help="Total time spent off your primary task in the latest session.")
    with c3:
        st.metric(
            "Average measured CRC",
            format_duration(crc) if crc is not None else "No data yet",
            help="Context Recovery Cost: how long it takes to get back into your task after an interruption.",
        )
        if crc is None:
            st.caption("Measured in controlled experiment trials. Browser tracking alone can't measure it.")
        else:
            st.caption(f"Across {len(crc_values)} measured recover{'y' if len(crc_values) == 1 else 'ies'}.")
    if latencies:
        with cols[3]:
            st.metric(
                "Avg return latency",
                format_duration(sum(latencies) / len(latencies)),
                help="Browser-measured return time after an interruption. A proxy, not CRC.",
            )
            st.caption(f"From {len(latencies)} browser episode{'s' if len(latencies) != 1 else ''}.")

    # ---------- Insight ----------
    if current_episodes:
        longest = max(current_episodes, key=lambda e: float(e.get("duration_sec") or 0))
        where = longest.get("primary_interruption_category")
        suffix = f" ({where})" if where and where not in ("None", "") else ""
        st.info(f"Your longest interruption this session was {format_duration(longest.get('duration_sec'))}{suffix}.")

    st.markdown("---")

    # ---------- Focus timeline ----------
    st.subheader("Focus timeline")
    st.caption("Your latest tracking session, from first to last recorded activity.")

    segments = build_timeline(latest, switches)
    if segments:
        df = pd.DataFrame(segments)
        df["Session"] = "Latest session"
        df["Duration"] = (df["Finish"] - df["Start"]).dt.total_seconds().apply(format_duration)

        fig = px.timeline(
            df,
            x_start="Start",
            x_end="Finish",
            y="Session",
            color="Activity",
            hover_data={"Session": False, "Duration": True, "Start": "|%H:%M:%S", "Finish": "|%H:%M:%S"},
            color_discrete_map={"Primary Task": TEAL, "Interruption": AMBER, "Idle / Paused": GREY},
        )
        fig.update_traces(marker_line_width=2, marker_line_color=CARD)
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor=CARD,
            height=170,
            margin=dict(l=5, r=5, t=10, b=10),
            legend=dict(orientation="h", y=-0.4, title_text=""),
            yaxis=dict(visible=False),
            xaxis=dict(title="", gridcolor=GRID, range=[df["Start"].min(), df["Finish"].max()]),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No timeline yet. Start a tracking session from the RECLAIM Chrome extension.")

    st.markdown("---")

    # ---------- Current primary task ----------
    st.subheader("Current primary task")
    col1, col2 = st.columns([3, 1])
    with col1:
        if domain and domain not in ("blank", "None", ""):
            st.markdown(f"**{domain}**")
            st.caption(category or "General work")
        else:
            st.markdown("**No primary task selected**")
            st.caption("Choose a primary tab in the Chrome extension.")
    with col2:
        if status == "ACTIVE":
            st.success("Tracking active")
        elif status == "PAUSED":
            st.warning("Tracking paused")
        else:
            st.caption("Tracking stopped")
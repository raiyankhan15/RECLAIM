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
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timezone, timedelta
from backend.database import get_connection

# Visual Palette Constants
COLOR_BG_MAIN = "#0B0F12"
COLOR_BG_SEC = "#11171C"
COLOR_BG_CARD = "#151D23"
COLOR_BORDER = "#1C262F"
COLOR_TEXT_PRIMARY = "#F4F6F8"
COLOR_TEXT_SECONDARY = "#89949E"
COLOR_PRIMARY_TASK = "#43C6AC"  # Muted Teal
COLOR_INTERRUPTION = "#E9A23B"  # Warm Amber
COLOR_RECOVERY = "#7298F5"      # Subtle Blue
COLOR_IDLE = "#6B7280"          # Neutral Grey
COLOR_ALERT = "#E05252"         # Restrained Red

def format_duration(seconds: float) -> str:
    """Formats seconds into human-readable minutes and seconds (e.g. 37s, 8m 42s)."""
    if seconds is None or seconds < 0:
        return "0s"
    total_sec = round(seconds)
    if total_sec < 60:
        return f"{total_sec}s"
    minutes = total_sec // 60
    rem_sec = total_sec % 60
    if rem_sec == 0:
        return f"{minutes}m"
    return f"{minutes}m {rem_sec:02d}s"

def format_crc(seconds: float, prefix: bool = True) -> str:
    """Formats Context Recovery Cost (CRC) in seconds or minutes and seconds."""
    if seconds is None:
        return "N/A"
    total_sec = round(seconds, 1)
    p = "+" if prefix else ""
    if total_sec < 60:
        return f"{p}{total_sec:.1f}s"
    minutes = int(total_sec // 60)
    rem_sec = round(total_sec % 60)
    return f"{p}{minutes}m {rem_sec:02d}s"

def fetch_telemetry_data():
    """Fetches sessions, interruption episodes, tab switches, and experiments from SQLite."""
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Tracking sessions
        cursor.execute("SELECT * FROM tracking_sessions ORDER BY start_time DESC")
        session_rows = [dict(r) for r in cursor.fetchall()]
        latest_session = session_rows[0] if session_rows else None
        prev_session = session_rows[1] if len(session_rows) > 1 else None

        # Interruption episodes
        cursor.execute("""
            SELECT id, session_id, episode_id, start_time, end_time, duration_sec,
                   switch_count, visited_domains, primary_interruption_category,
                   return_latency_sec, recovery_status, measured_recovery_sec
            FROM interruption_episodes
            ORDER BY start_time DESC
        """)
        all_episodes = [dict(r) for r in cursor.fetchall()]

        # Tab switch events
        cursor.execute("""
            SELECT id, session_id, timestamp, from_tab_id, to_tab_id,
                   to_domain, to_category, duration_on_tab, is_primary, is_interruption
            FROM tab_switch_events
            ORDER BY timestamp ASC
        """)
        all_switches = [dict(r) for r in cursor.fetchall()]

        # Controlled experiments
        exp_df = pd.read_sql_query("SELECT * FROM controlled_experiments", conn)

    finally:
        conn.close()

    # Pre-parse timestamps
    ep_df = pd.DataFrame(all_episodes)
    if not ep_df.empty:
        ep_df["dt"] = pd.to_datetime(ep_df["start_time"], format="ISO8601", utc=True, errors="coerce")
    else:
        ep_df = pd.DataFrame(columns=["dt", "session_id", "duration_sec", "visited_domains", "primary_interruption_category", "start_time"])

    sw_df = pd.DataFrame(all_switches)
    if not sw_df.empty:
        sw_df["dt"] = pd.to_datetime(sw_df["timestamp"], format="ISO8601", utc=True, errors="coerce")
    else:
        sw_df = pd.DataFrame(columns=["dt", "session_id", "to_domain", "to_category", "duration_on_tab", "is_primary", "is_interruption"])

    if not exp_df.empty:
        exp_df["dt"] = pd.to_datetime(exp_df["timestamp"], format="ISO8601", utc=True, errors="coerce")

    return latest_session, prev_session, ep_df, sw_df, exp_df

def filter_by_period(time_period: str, ep_df: pd.DataFrame, sw_df: pd.DataFrame, exp_df: pd.DataFrame):
    """Filters dataframes consistently by the selected time period."""
    now_utc = datetime.now(timezone.utc)
    max_ref_dt = now_utc
    if not exp_df.empty and exp_df["dt"].notna().any():
        max_ref_dt = max(max_ref_dt, exp_df["dt"].max())

    if time_period == "Today":
        cutoff = max_ref_dt - timedelta(days=1)
        f_ep = ep_df[ep_df["dt"] >= cutoff] if not ep_df.empty else ep_df
        f_sw = sw_df[sw_df["dt"] >= cutoff] if not sw_df.empty else sw_df
        f_exp = exp_df[exp_df["dt"] >= cutoff] if not exp_df.empty else exp_df
    elif time_period == "7 Days":
        cutoff = max_ref_dt - timedelta(days=7)
        f_ep = ep_df[ep_df["dt"] >= cutoff] if not ep_df.empty else ep_df
        f_sw = sw_df[sw_df["dt"] >= cutoff] if not sw_df.empty else sw_df
        f_exp = exp_df[exp_df["dt"] >= cutoff] if not exp_df.empty else exp_df
    elif time_period == "30 Days":
        cutoff = max_ref_dt - timedelta(days=30)
        f_ep = ep_df[ep_df["dt"] >= cutoff] if not ep_df.empty else ep_df
        f_sw = sw_df[sw_df["dt"] >= cutoff] if not sw_df.empty else sw_df
        f_exp = exp_df[exp_df["dt"] >= cutoff] if not exp_df.empty else exp_df
    else:
        f_ep = ep_df
        f_sw = sw_df
        f_exp = exp_df

    return f_ep, f_sw, f_exp

def render_section_one(latest_session, prev_session, time_period, f_ep, f_exp):
    """Renders Section 1: Your productivity at a glance, primary task panel, and 3 metric cards."""
    now_utc = datetime.now(timezone.utc)
    current_date_str = datetime.now().strftime("%A, %b %d, %Y")

    tracking_status = latest_session.get("status", "STOPPED") if latest_session else "STOPPED"
    if tracking_status == "ACTIVE":
        status_pill_html = '<span class="reclaim-pill reclaim-pill-active"><span class="reclaim-dot"></span> Tracking Active</span>'
    elif tracking_status == "PAUSED":
        status_pill_html = '<span class="reclaim-pill reclaim-pill-paused"><span class="reclaim-dot"></span> Tracking Paused</span>'
    else:
        status_pill_html = '<span class="reclaim-pill reclaim-pill-stopped"><span class="reclaim-dot"></span> Tracking Stopped</span>'

    # Top Header
    h_col1, h_col2 = st.columns([2.6, 1.4])
    with h_col1:
        st.markdown(f"""
        <div>
            <div class="reclaim-brand-tag">RECLAIM</div>
            <h1 class="reclaim-heading">Your productivity at a glance</h1>
            <p class="reclaim-sub">A clearer picture of where your focus goes.</p>
        </div>
        """, unsafe_allow_html=True)

    with h_col2:
        st.markdown(f"""
        <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 8px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span class="reclaim-date-text">{current_date_str}</span>
                {status_pill_html}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Time-Period Selector (Compact segmented control)
    time_choice = st.segmented_control(
        "Time Horizon",
        options=["Today", "7 Days", "30 Days", "All Time"],
        default=time_period,
        label_visibility="collapsed",
        key="reclaim_period_selector"
    ) or time_period

    # Primary Task Indicator Panel
    has_primary = (
        latest_session is not None
        and latest_session.get("primary_domain")
        and latest_session["primary_domain"] not in ("blank", "", "None")
    )

    if has_primary:
        p_domain = latest_session["primary_domain"]
        p_category = latest_session.get("primary_category") or "General Work"
        switches_count = latest_session.get("total_switches") or 0

        # Calculate session duration
        sess_start = pd.to_datetime(latest_session["start_time"], format="ISO8601", utc=True, errors="coerce")
        if pd.notna(sess_start):
            if tracking_status == "ACTIVE":
                dur_sec = max(0.0, (now_utc - sess_start).total_seconds())
            elif latest_session.get("end_time"):
                sess_end = pd.to_datetime(latest_session["end_time"], format="ISO8601", utc=True, errors="coerce")
                dur_sec = max(0.0, (sess_end - sess_start).total_seconds()) if pd.notna(sess_end) else 0.0
            else:
                dur_sec = float(latest_session.get("total_interruption_time") or 0.0)
            duration_disp = format_duration(dur_sec)
        else:
            duration_disp = "—"

        st.markdown(f"""
        <div class="reclaim-task-banner">
            <div>
                <div class="reclaim-task-label">PRIMARY TASK</div>
                <div class="reclaim-task-domain">{p_domain}</div>
                <div class="reclaim-task-category">{p_category}</div>
            </div>
            <div class="reclaim-task-stats">
                <div class="reclaim-task-stat-item">
                    <div class="reclaim-task-stat-num">{duration_disp}</div>
                    <div class="reclaim-task-stat-lbl">SESSION DURATION</div>
                </div>
                <div class="reclaim-task-stat-item">
                    <div class="reclaim-task-stat-num">{switches_count}</div>
                    <div class="reclaim-task-stat-lbl">TAB SWITCHES</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="reclaim-task-banner" style="border-style: dashed;">
            <div>
                <div class="reclaim-task-label" style="color: #89949E;">PRIMARY TASK</div>
                <div class="reclaim-task-domain" style="color: #89949E; font-size: 17px;">No Active Primary Task</div>
                <div class="reclaim-task-category">Select an active tab via the RECLAIM Chrome Extension to designate your primary focus.</div>
            </div>
            <div class="reclaim-task-stats">
                <div class="reclaim-task-stat-item">
                    <div class="reclaim-task-stat-num" style="color: #89949E; font-size: 14px;">Awaiting Tab</div>
                    <div class="reclaim-task-stat-lbl">STATUS</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Metric 1: Interruptions
    completed_interruptions = len(f_ep)
    interr_subtext = ""
    if prev_session and not f_ep.empty:
        prev_ep_count = len(f_ep[f_ep["session_id"] == prev_session["session_id"]])
        if prev_ep_count > 0:
            diff = completed_interruptions - prev_ep_count
            if diff > 0:
                interr_subtext = f'<span style="color: #E9A23B; font-weight: 600;">+{diff}</span> vs previous session'
            elif diff < 0:
                interr_subtext = f'<span style="color: #43C6AC; font-weight: 600;">{diff}</span> vs previous session'
            else:
                interr_subtext = 'Equal to previous session'
    if not interr_subtext:
        interr_subtext = f'Logged in {time_choice.lower()}'

    # Metric 2: Time Away
    total_time_away_sec = float(f_ep["duration_sec"].sum()) if not f_ep.empty else 0.0
    time_away_disp = format_duration(total_time_away_sec)
    avg_per_ep = format_duration(total_time_away_sec / max(1, completed_interruptions))

    # Metric 3: Context Recovery Cost (CRC)
    # Strictly distinguish measured vs estimated vs unavailable
    real_exp = f_exp[f_exp["data_source"] == "REAL_EXPERIMENT"] if not f_exp.empty and "data_source" in f_exp.columns else pd.DataFrame()

    if not real_exp.empty:
        crc_val = float(real_exp["crc_seconds"].mean())
        crc_display = format_crc(crc_val)
        crc_badge = '<span class="reclaim-pill reclaim-pill-active" style="font-size: 11px;">Measured</span>'
        crc_sub = f"Empirical recovery latency across {len(real_exp)} measured trials."
    elif total_time_away_sec > 0:
        # Estimated resumption overhead (clearly labeled as estimate)
        est_crc = total_time_away_sec * 0.40
        crc_display = format_crc(est_crc)
        crc_badge = '<span class="reclaim-pill reclaim-pill-paused" style="font-size: 11px;">Estimated</span>'
        crc_sub = "Model estimate based on time away. Awaiting measured trials."
    else:
        crc_display = "—"
        crc_badge = '<span class="reclaim-pill reclaim-pill-stopped" style="font-size: 11px;">Unavailable</span>'
        crc_sub = "Measured during controlled recovery trials."

    # Render Three Large Metric Cards
    st.markdown(f"""
    <div class="reclaim-metrics-row">
        <!-- Card 1: Interruptions -->
        <div class="reclaim-metric-card">
            <div>
                <div class="reclaim-metric-top">
                    <span class="reclaim-metric-title">INTERRUPTIONS</span>
                </div>
                <div class="reclaim-metric-number">{completed_interruptions}</div>
                <div class="reclaim-metric-desc">Completed interruption episodes.</div>
            </div>
            <div class="reclaim-metric-subtext">{interr_subtext}</div>
        </div>

        <!-- Card 2: Time Away -->
        <div class="reclaim-metric-card">
            <div>
                <div class="reclaim-metric-top">
                    <span class="reclaim-metric-title">TIME AWAY</span>
                </div>
                <div class="reclaim-metric-number" style="color: {'#E9A23B' if total_time_away_sec > 60 else '#F4F6F8'};">{time_away_disp}</div>
                <div class="reclaim-metric-desc">Total time away from your primary task.</div>
            </div>
            <div class="reclaim-metric-subtext">Avg per episode: <strong style="color: #F4F6F8;">{avg_per_ep}</strong></div>
        </div>

        <!-- Card 3: Context Recovery Cost -->
        <div class="reclaim-metric-card">
            <div>
                <div class="reclaim-metric-top">
                    <span class="reclaim-metric-title">CONTEXT RECOVERY COST</span>
                    {crc_badge}
                </div>
                <div class="reclaim-metric-number" style="color: #43C6AC;">{crc_display}</div>
                <div class="reclaim-metric-desc">Additional recovery time.</div>
            </div>
            <div class="reclaim-metric-subtext">{crc_sub}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    return time_choice

def render_section_two_focus_timeline(latest_session, sw_df):
    """Renders Section 2: Large, interactive horizontal Focus Timeline (Signature Feature)."""
    st.markdown("""
    <div class="reclaim-card">
        <div class="reclaim-card-title">Focus Timeline</div>
        <p class="reclaim-card-desc">
            Visual continuous timeline of your work session. Segments represent focused work, departures, and task resumptions.
        </p>
    """, unsafe_allow_html=True)

    timeline_segments = []
    if latest_session and not sw_df.empty:
        sess_switches = sw_df[sw_df["session_id"] == latest_session["session_id"]].sort_values("dt")
        if not sess_switches.empty:
            sess_start = pd.to_datetime(latest_session["start_time"], format="ISO8601", utc=True, errors="coerce")
            sess_end = pd.to_datetime(latest_session["end_time"], format="ISO8601", utc=True, errors="coerce") if latest_session.get("end_time") else datetime.now(timezone.utc)
            if pd.isna(sess_start):
                sess_start = sess_switches["dt"].min() - timedelta(seconds=10)

            p_domain = latest_session.get("primary_domain", "primary tab")
            status = latest_session.get("status", "STOPPED")

            prev_t = sess_start
            prev_type = "Primary Task"
            prev_domain = p_domain

            for _, sw in sess_switches.iterrows():
                sw_t = sw["dt"]
                if sw_t > prev_t:
                    dur_sec = (sw_t - prev_t).total_seconds()
                    timeline_segments.append({
                        "start": prev_t,
                        "end": sw_t,
                        "type": prev_type,
                        "domain": prev_domain,
                        "duration_sec": dur_sec,
                        "duration_disp": format_duration(dur_sec),
                        "start_disp": prev_t.strftime("%H:%M:%S"),
                        "end_disp": sw_t.strftime("%H:%M:%S"),
                        "activity": "Primary Focus" if prev_type == "Primary Task" else "Interruption",
                        "row": "Focus Session"
                    })
                prev_t = sw_t
                if sw.get("is_primary") == 1 or sw.get("to_domain") == p_domain:
                    prev_type = "Primary Task"
                    prev_domain = p_domain
                else:
                    prev_type = "Interruption"
                    prev_domain = sw.get("to_domain") or "Secondary Tab"

            if sess_end > prev_t:
                dur_sec = (sess_end - prev_t).total_seconds()
                final_type = "Idle / Paused" if status == "PAUSED" else prev_type
                timeline_segments.append({
                    "start": prev_t,
                    "end": sess_end,
                    "type": final_type,
                    "domain": prev_domain,
                    "duration_sec": dur_sec,
                    "duration_disp": format_duration(dur_sec),
                    "start_disp": prev_t.strftime("%H:%M:%S"),
                    "end_disp": sess_end.strftime("%H:%M:%S"),
                    "activity": "Paused" if status == "PAUSED" else ("Primary Focus" if final_type == "Primary Task" else "Interruption"),
                    "row": "Focus Session"
                })

    if timeline_segments:
        tl_df = pd.DataFrame(timeline_segments)
        fig_tl = px.timeline(
            tl_df,
            x_start="start",
            x_end="end",
            y="row",
            color="type",
            color_discrete_map={
                "Primary Task": COLOR_PRIMARY_TASK,
                "Interruption": COLOR_INTERRUPTION,
                "Idle / Paused": COLOR_IDLE
            },
            custom_data=["domain", "duration_disp", "start_disp", "end_disp", "activity"]
        )

        fig_tl.update_traces(
            hovertemplate=(
                "<b>%{customdata[4]}</b><br>" +
                "<b>Website / Domain:</b> %{customdata[0]}<br>" +
                "<b>Time:</b> %{customdata[2]} – %{customdata[3]}<br>" +
                "<b>Duration:</b> %{customdata[1]}<extra></extra>"
            )
        )

        fig_tl.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor=COLOR_BG_SEC,
            height=100,
            margin=dict(l=5, r=5, t=5, b=22),
            showlegend=False,
            yaxis=dict(visible=False),
            xaxis=dict(
                title="",
                tickformat="%H:%M:%S",
                gridcolor=COLOR_BORDER,
                zerolinecolor="#24303B",
                tickfont=dict(color=COLOR_TEXT_SECONDARY, size=11)
            )
        )

        st.plotly_chart(fig_tl, use_container_width=True)

        # Color Legend
        st.markdown(f"""
        <div class="reclaim-legend">
            <span class="reclaim-legend-item"><span style="width: 10px; height: 10px; background: {COLOR_PRIMARY_TASK}; border-radius: 2px;"></span> Primary Task ({latest_session.get('primary_domain', 'Focused')})</span>
            <span class="reclaim-legend-item"><span style="width: 10px; height: 10px; background: {COLOR_INTERRUPTION}; border-radius: 2px;"></span> Interruption (Switched Away)</span>
            <span class="reclaim-legend-item"><span style="width: 10px; height: 10px; background: {COLOR_IDLE}; border-radius: 2px;"></span> Idle / Paused</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="reclaim-empty-box">
            <div class="reclaim-empty-title">No Session Activity Recorded</div>
            Start a tracking session in Google Chrome and switch tabs to stream real-time Focus Timeline events.
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

def render_section_three_interruption_breakdown(f_sw, f_ep):
    """Renders Section 3: Horizontal bar chart showing where interruptions originate."""
    st.markdown("""
    <div class="reclaim-card" style="height: 100%;">
        <div class="reclaim-card-title">Interruption Breakdown</div>
        <p class="reclaim-card-desc">
            Websites and categories accounting for your digital interruptions, sorted by duration.
        </p>
    """, unsafe_allow_html=True)

    breakdown_data = []

    # 1. Prefer domain-level breakdown from tab_switch_events
    if not f_sw.empty:
        interr_sw = f_sw[f_sw["is_interruption"] == 1]
        if not interr_sw.empty:
            for domain, group in interr_sw.groupby("to_domain"):
                dur = group["duration_on_tab"].sum()
                count = len(group)
                cat = group["to_category"].iloc[0] if "to_category" in group.columns and pd.notna(group["to_category"].iloc[0]) else "Browsing"
                breakdown_data.append({
                    "label": domain,
                    "category": cat,
                    "duration_sec": dur,
                    "count": count
                })

    # 2. Fallback to interruption_episodes if switch events empty
    if not breakdown_data and not f_ep.empty:
        for cat, group in f_ep.groupby("primary_interruption_category"):
            dur = group["duration_sec"].sum()
            count = len(group)
            breakdown_data.append({
                "label": cat or "General Distraction",
                "category": cat or "General",
                "duration_sec": dur,
                "count": count
            })

    if breakdown_data:
        b_df = pd.DataFrame(breakdown_data).sort_values("duration_sec", ascending=False)
        total_time = max(0.1, b_df["duration_sec"].sum())
        b_df["pct"] = (b_df["duration_sec"] / total_time) * 100.0

        # Limit default display to top 5 categories/websites as requested
        top_5_df = b_df.head(5).iloc[::-1]  # reversed for horizontal bar order (highest at top)

        bar_texts = [f"{c} ep • {format_duration(d)} ({p:.1f}%)" for c, d, p in zip(top_5_df["count"], top_5_df["duration_sec"], top_5_df["pct"])]

        fig_breakdown = go.Figure(go.Bar(
            x=top_5_df["pct"],
            y=top_5_df["label"],
            orientation="h",
            marker=dict(
                color=COLOR_INTERRUPTION,
                line=dict(color="#D48822", width=1)
            ),
            text=bar_texts,
            textposition="outside",
            textfont=dict(color=COLOR_TEXT_SECONDARY, size=11),
            customdata=np.stack((top_5_df["duration_sec"].apply(format_duration), top_5_df["count"], top_5_df["category"]), axis=-1),
            hovertemplate=(
                "<b>%{y}</b> (%{customdata[2]})<br>" +
                "<b>Share of Distraction:</b> %{x:.1f}%<br>" +
                "<b>Total Time Away:</b> %{customdata[0]}<br>" +
                "<b>Interruptions:</b> %{customdata[1]} episodes<extra></extra>"
            )
        ))

        fig_breakdown.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor=COLOR_BG_SEC,
            height=260,
            margin=dict(l=10, r=40, t=10, b=25),
            xaxis=dict(
                title="Share of Interruption Time (%)",
                ticksuffix="%",
                range=[0, max(115, top_5_df["pct"].max() * 1.25)],
                gridcolor=COLOR_BORDER,
                zerolinecolor="#24303B",
                tickfont=dict(color=COLOR_TEXT_SECONDARY)
            ),
            yaxis=dict(
                tickfont=dict(color=COLOR_TEXT_PRIMARY, size=12)
            )
        )

        st.plotly_chart(fig_breakdown, use_container_width=True)

        if len(b_df) > 5:
            with st.expander(f"View all {len(b_df)} interruption sources"):
                st.dataframe(
                    b_df[["label", "category", "count", "duration_sec", "pct"]].rename(columns={
                        "label": "Website / Source",
                        "category": "Category",
                        "count": "Interruptions",
                        "duration_sec": "Duration (s)",
                        "pct": "Share (%)"
                    }),
                    use_container_width=True,
                    hide_index=True
                )
    else:
        st.markdown("""
        <div class="reclaim-empty-box">
            <div class="reclaim-empty-title">Zero Interruptions Logged</div>
            No interruption sources recorded for the selected period. Your focus remained uninterrupted.
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

def render_section_four_recovery_trend(f_exp, time_period):
    """Renders Section 4: Line chart of genuinely measured recovery observations or informative empty state."""
    st.markdown("""
    <div class="reclaim-card" style="height: 100%;">
        <div class="reclaim-card-title">Recovery Trend</div>
        <p class="reclaim-card-desc">
            Context Recovery Cost (CRC) progression over time across genuinely measured cognitive sessions.
        </p>
    """, unsafe_allow_html=True)

    # Filter strictly for genuine empirical experiment trials
    real_exp = f_exp[f_exp["data_source"] == "REAL_EXPERIMENT"] if not f_exp.empty and "data_source" in f_exp.columns else pd.DataFrame()

    if not real_exp.empty and len(real_exp) >= 2:
        trend_df = real_exp.sort_values("dt").copy()

        if time_period == "Today":
            daily_trend = trend_df.groupby(trend_df["dt"].dt.strftime("%H:%M")).agg(
                mean_crc=("crc_seconds", "mean"),
                count=("crc_seconds", "count")
            ).reset_index()
            x_col = "dt"
        else:
            daily_trend = trend_df.groupby(trend_df["dt"].dt.date).agg(
                mean_crc=("crc_seconds", "mean"),
                count=("crc_seconds", "count")
            ).reset_index()
            daily_trend["date_str"] = daily_trend["dt"].apply(lambda d: d.strftime("%b %d"))
            x_col = "date_str"

        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(
            x=daily_trend[x_col],
            y=daily_trend["mean_crc"],
            mode="lines+markers",
            line=dict(color=COLOR_RECOVERY, width=2.5),
            marker=dict(size=7, color=COLOR_RECOVERY, line=dict(color="#FFFFFF", width=1.5)),
            customdata=daily_trend["count"],
            hovertemplate=(
                "<b>Date / Period:</b> %{x}<br>" +
                "<b>Mean Recovery Cost (CRC):</b> +%{y:.1f}s<br>" +
                "<b>Measured Trials:</b> %{customdata} sessions<extra></extra>"
            ),
            name="Measured CRC"
        ))

        fig_trend.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor=COLOR_BG_SEC,
            height=260,
            margin=dict(l=10, r=20, t=10, b=25),
            xaxis=dict(
                gridcolor=COLOR_BORDER,
                zerolinecolor="#24303B",
                tickfont=dict(color=COLOR_TEXT_SECONDARY)
            ),
            yaxis=dict(
                title="Recovery Cost (s)",
                ticksuffix="s",
                gridcolor=COLOR_BORDER,
                zerolinecolor="#24303B",
                tickfont=dict(color=COLOR_TEXT_SECONDARY)
            ),
            showlegend=False
        )

        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.markdown("""
        <div class="reclaim-empty-box">
            <div class="reclaim-empty-title">Awaiting Controlled Recovery Measurements</div>
            RECLAIM requires comparable, genuinely measured recovery observations from controlled trials to plot your recovery trend over time.<br><br>
            Browser tab tracking measures time away and switch frequency, but quantifying cognitive recovery latency requires completed trial sessions.
            <div style="margin-top: 12px; font-size: 11.5px; color: #556277;">
                Honest Metric Standard: Zero synthetic data or unmeasured extrapolations are substituted here.
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

def render_overview():
    """Main executive entry point for RECLAIM Dashboard."""
    # 0. Fetch Stored Data
    latest_session, prev_session, ep_df, sw_df, exp_df = fetch_telemetry_data()

    # 1. Section One: Your Productivity at a Glance & Segmented Time Filter
    selected_period = render_section_one(latest_session, prev_session, "All Time", ep_df, exp_df)

    # Apply Time-Period Filter
    f_ep, f_sw, f_exp = filter_by_period(selected_period, ep_df, sw_df, exp_df)

    # 2. Section Two: Focus Timeline (Signature Visual Feature)
    render_section_two_focus_timeline(latest_session, sw_df)

    # 3. Section Three & Four: Two-Column Row (Interruption Breakdown + Recovery Trend)
    col_breakdown, col_trend = st.columns(2)

    with col_breakdown:
        render_section_three_interruption_breakdown(f_sw, f_ep)

    with col_trend:
        render_section_four_recovery_trend(f_exp, selected_period)

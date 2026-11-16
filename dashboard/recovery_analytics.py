"""
dashboard/recovery_analytics.py - Deep Recovery Analytics & Behavioral Trends
Analyzes recovery latency by category, complexity, switch frequency,
and empirical duration distributions with graceful error handling and zero crash guarantees.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from backend.database import get_connection

def render_recovery_analytics():
    """Renders the comprehensive recovery analytics page."""
    st.markdown('<div class="brand-badge">Cognitive Analytics</div>', unsafe_allow_html=True)
    st.title("Context Recovery Analytics")
    st.markdown(
        "Empirical investigation of resumption lag across task categories, interruption lengths, "
        "and cognitive load conditions."
    )

    conn = get_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM controlled_experiments", conn)
        episodes_df = pd.read_sql_query("SELECT * FROM interruption_episodes", conn)
    finally:
        conn.close()

    # Empty Dataset Handling
    if df.empty:
        st.warning("No experiment records available for recovery analytics.")
        st.info("Start tracking in Chrome or run trials to populate recovery records.")
        return

    # Filter Controls
    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1:
        conditions = df["condition"].unique().tolist() if "condition" in df.columns else []
        cond_filter = st.multiselect(
            "Filter Conditions:",
            options=conditions,
            default=conditions
        )
    with f_col2:
        complexities = df["task_complexity"].unique().tolist() if "task_complexity" in df.columns else []
        comp_filter = st.multiselect(
            "Filter Task Complexity:",
            options=complexities,
            default=complexities
        )
    with f_col3:
        source_filter = st.selectbox(
            "Data Source:",
            ["All Records", "Real Experiment Trials Only", "Synthetic Demo Records Only"]
        )

    # Apply Filters
    filtered_df = df.copy()
    if cond_filter:
        filtered_df = filtered_df[filtered_df["condition"].isin(cond_filter)]
    if comp_filter:
        filtered_df = filtered_df[filtered_df["task_complexity"].isin(comp_filter)]

    if source_filter == "Real Experiment Trials Only":
        filtered_df = filtered_df[filtered_df["data_source"] == "REAL_EXPERIMENT"]
    elif source_filter == "Synthetic Demo Records Only":
        filtered_df = filtered_df[filtered_df["data_source"] == "SYNTHETIC_DEMO"]

    if filtered_df.empty:
        st.warning("No records match the current filter selection. Try adjusting the filters above.")
        return

    # Summary KPI row
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total Analyzed Trials", len(filtered_df))
    with m2:
        avg_interr = filtered_df['interruption_duration_sec'].mean() if 'interruption_duration_sec' in filtered_df.columns else 0.0
        st.metric("Mean Interruption Duration", f"{avg_interr:.1f}s")
    with m3:
        avg_crc = filtered_df['crc_seconds'].mean() if 'crc_seconds' in filtered_df.columns else 0.0
        st.metric("Mean Measured CRC", f"{avg_crc:.2f}s")
    with m4:
        if 'recovery_accuracy' in filtered_df.columns and 'baseline_accuracy' in filtered_df.columns:
            acc_retention = (filtered_df['recovery_accuracy'].mean() - filtered_df['baseline_accuracy'].mean()) * 100
            st.metric("Mean Accuracy Retention", f"{acc_retention:+.1f}%")
        else:
            st.metric("Mean Accuracy Retention", "N/A")

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # Row 1: Interruption vs Recovery Duration & Recovery by Complexity
    row1_c1, row1_c2 = st.columns(2)

    with row1_c1:
        st.subheader("Interruption Duration vs. Context Recovery Cost")
        # Robust scatter plot: Try trendline="ols" if supported; fallback cleanly without crashing
        has_trendline = False
        try:
            fig_trend = px.scatter(
                filtered_df,
                x="interruption_duration_sec",
                y="crc_seconds",
                color="condition" if "condition" in filtered_df.columns else None,
                trendline="ols",
                hover_data=["participant_id", "baseline_duration_sec", "task_complexity"],
                labels={"interruption_duration_sec": "Interruption Duration (s)", "crc_seconds": "CRC (s)"}
            )
            has_trendline = True
        except Exception:
            # Safe fallback if statsmodels is unavailable or sample size too small
            fig_trend = px.scatter(
                filtered_df,
                x="interruption_duration_sec",
                y="crc_seconds",
                color="condition" if "condition" in filtered_df.columns else None,
                hover_data=["participant_id", "baseline_duration_sec", "task_complexity"],
                labels={"interruption_duration_sec": "Interruption Duration (s)", "crc_seconds": "CRC (s)"}
            )

        fig_trend.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(17,24,39,0.5)",
            margin=dict(l=20, r=20, t=20, b=20)
        )
        st.plotly_chart(fig_trend, use_container_width=True)
        if has_trendline:
            st.caption("Fitted ordinary least squares trendlines showing cognitive resumption trajectories.")
        else:
            st.caption("Scatter distribution of interruption duration vs. measured Context Recovery Cost.")

    with row1_c2:
        st.subheader("Recovery Duration by Task Complexity")
        if "task_complexity" in filtered_df.columns and "baseline_duration_sec" in filtered_df.columns and "recovery_duration_sec" in filtered_df.columns:
            comp_grouped = filtered_df.groupby("task_complexity")[["baseline_duration_sec", "recovery_duration_sec"]].mean().reset_index()
            fig_comp = px.bar(
                comp_grouped,
                x="task_complexity",
                y=["baseline_duration_sec", "recovery_duration_sec"],
                barmode="group",
                labels={"value": "Mean Duration (seconds)", "variable": "Task Stage"},
                color_discrete_map={"baseline_duration_sec": "#4F46E5", "recovery_duration_sec": "#818CF8"}
            )
            fig_comp.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(17,24,39,0.5)",
                margin=dict(l=20, r=20, t=20, b=20)
            )
            st.plotly_chart(fig_comp, use_container_width=True)
            st.caption("Baseline vs post-interruption task completion time by complexity.")
        else:
            st.info("Complexity attributes unavailable for current selection.")

    # Row 2: Switch Frequency & Recovery Distribution
    row2_c1, row2_c2 = st.columns(2)

    with row2_c1:
        st.subheader("Context Switch Density vs. Resumption Overhead")
        if "switch_density" in filtered_df.columns and "crc_seconds" in filtered_df.columns:
            fig_density = px.scatter(
                filtered_df,
                x="switch_density",
                y="crc_seconds",
                color="condition" if "condition" in filtered_df.columns else None,
                size="switch_count" if "switch_count" in filtered_df.columns else None,
                labels={"switch_density": "Switches per Minute", "crc_seconds": "CRC Excess (s)"}
            )
            fig_density.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(17,24,39,0.5)",
                margin=dict(l=20, r=20, t=20, b=20)
            )
            st.plotly_chart(fig_density, use_container_width=True)
            st.caption("High switch density compounds the total resumption latency.")
        else:
            st.info("Switch density metrics unavailable.")

    with row2_c2:
        st.subheader("Context Recovery Cost (CRC) Distribution")
        if "crc_seconds" in filtered_df.columns:
            fig_hist = px.histogram(
                filtered_df,
                x="crc_seconds",
                nbins=20,
                color="condition" if "condition" in filtered_df.columns else None,
                marginal="box"
            )
            fig_hist.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(17,24,39,0.5)",
                xaxis=dict(title="CRC Excess Seconds", gridcolor="#1F2937"),
                yaxis=dict(title="Trial Count", gridcolor="#1F2937"),
                margin=dict(l=20, r=20, t=20, b=20)
            )
            st.plotly_chart(fig_hist, use_container_width=True)
            st.caption("Empirical latency distributions across experimental conditions.")
        else:
            st.info("CRC distribution unavailable.")

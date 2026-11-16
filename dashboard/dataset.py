"""
dashboard/dataset.py - Dataset Management & Explorer
Provides tabular inspection, exploratory statistics, condition filters,
CSV export, and controlled synthetic data generation.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from backend.database import get_connection
from data.synthetic_data import generate_synthetic_dataset
from database.db import bulk_insert_experiments

def render_dataset():
    """Renders the dataset explorer interface."""
    st.markdown('<div class="brand-badge">Dataset Management</div>', unsafe_allow_html=True)
    st.title("Dataset Explorer & Export")
    st.markdown(
        "Inspect, filter, audit, and export interaction records stored in SQLite. "
        "Strict boundaries are maintained between actual participant records and synthetic demonstration data."
    )

    conn = get_connection()
    try:
        exp_df = pd.read_sql_query("SELECT * FROM controlled_experiments ORDER BY timestamp DESC", conn)
        track_df = pd.read_sql_query("SELECT * FROM tracking_sessions ORDER BY start_time DESC", conn)
        episodes_df = pd.read_sql_query("SELECT * FROM interruption_episodes ORDER BY start_time DESC", conn)
    finally:
        conn.close()

    dataset_tab = st.radio(
        "Select Table to Inspect:",
        ["Controlled Experiment Trials", "Browser Tracking Sessions", "Interruption Episodes"],
        horizontal=True
    )

    if dataset_tab == "Controlled Experiment Trials":
        if exp_df.empty:
            st.warning("No controlled experiment trials recorded yet.")
            return

        # Filters
        c1, c2, c3 = st.columns(3)
        with c1:
            sources = ["All Sources"] + exp_df["data_source"].unique().tolist()
            s_filter = st.selectbox("Data Source:", sources)
        with c2:
            conditions = ["All Conditions"] + exp_df["condition"].unique().tolist()
            cond_filter = st.selectbox("Condition Filter:", conditions)
        with c3:
            participants = ["All Participants"] + exp_df["participant_id"].unique().tolist()
            p_filter = st.selectbox("Participant Filter:", participants)

        filtered = exp_df.copy()
        if s_filter != "All Sources":
            filtered = filtered[filtered["data_source"] == s_filter]
        if cond_filter != "All Conditions":
            filtered = filtered[filtered["condition"] == cond_filter]
        if p_filter != "All Participants":
            filtered = filtered[filtered["participant_id"] == p_filter]

        # Metric summary
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Total Records", len(filtered))
        with m2:
            st.metric("Unique Participants", filtered["participant_id"].nunique())
        with m3:
            st.metric("Mean Measured CRC", f"{filtered['crc_seconds'].mean():.2f}s")
        with m4:
            st.metric("Mean Latency Ratio", f"{filtered['crc_ratio'].mean():.2f}x")

        # CSV Download Button
        csv_data = filtered.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download Experiment Trials as CSV",
            data=csv_data,
            file_name=f"contextiq_experiments_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            type="primary"
        )

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        display_cols = [
            "trial_id", "participant_id", "condition", "task_complexity",
            "switch_count", "baseline_duration_sec", "interruption_duration_sec",
            "recovery_duration_sec", "crc_seconds", "crc_ratio", "recovery_status", "data_source"
        ]
        available_cols = [c for c in display_cols if c in filtered.columns]
        st.dataframe(filtered[available_cols], use_container_width=True, height=360)

        with st.expander("Descriptive Statistics"):
            num_cols = ["baseline_duration_sec", "baseline_accuracy", "interruption_duration_sec", "recovery_duration_sec", "recovery_accuracy", "crc_seconds", "crc_ratio", "switch_density"]
            st.dataframe(filtered[num_cols].describe().round(3), use_container_width=True)

    elif dataset_tab == "Browser Tracking Sessions":
        if track_df.empty:
            st.info("No Chrome Extension browser sessions logged yet. Install and activate the extension to populate.")
        else:
            st.dataframe(track_df, use_container_width=True)
            csv_track = track_df.to_csv(index=False).encode("utf-8")
            st.download_button("Download Tracking Sessions as CSV", csv_track, "contextiq_browser_sessions.csv", "text/csv")

    elif dataset_tab == "Interruption Episodes":
        if episodes_df.empty:
            st.info("No ambient interruption episodes logged yet.")
        else:
            st.dataframe(episodes_df, use_container_width=True)
            csv_ep = episodes_df.to_csv(index=False).encode("utf-8")
            st.download_button("Download Interruption Episodes as CSV", csv_ep, "contextiq_interruption_episodes.csv", "text/csv")

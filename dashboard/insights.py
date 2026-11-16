"""
dashboard/insights.py - Cognitive Science Foundations & Empirical Findings
Presents established cognitive psychological research, empirical findings from local trials,
and clear academic boundaries without requiring external third-party LLM API keys.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from backend.database import get_connection
from core.analytics import generate_empirical_insights
from config import COND_SINGLE, COND_REPEATED, CONDITIONS_LABELS

def render_insights():
    """Renders the comprehensive, human-designed research insights page."""
    st.markdown("""
    <div class="page-header">
        <h1 class="page-title">Research Insights</h1>
        <p class="page-desc">
            Bridging cognitive psychology, human-computer interaction, and machine learning to analyze the hidden cost of context switching.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # 1. Conceptual Framework: Interruption Duration vs. Context Recovery Cost
    # -------------------------------------------------------------------------
    st.markdown('<div class="page-title" style="font-size: 16px; margin: 20px 0 6px 0;">1. Understanding Context Recovery</div>', unsafe_allow_html=True)
    st.markdown("""
    In digital workflows, **screen time** is an insufficient metric for cognitive productivity.
    When a knowledge worker switches away from a task, two distinct temporal components occur:
    """)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("""
        <div class="metric-card" style="min-height: auto;">
            <div class="metric-header">
                <span class="metric-label">Stage 1: Interruption Duration (Time Away)</span>
            </div>
            <div style="font-size: 13.5px; color: #E6EDF3; line-height: 1.5;">
                The elapsed clock time spent actively engaged in a secondary activity (e.g., checking messages, opening social media, answering an email).
            </div>
            <div class="metric-footer">
                Measured directly via browser tab activity
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_b:
        st.markdown("""
        <div class="metric-card" style="min-height: auto;">
            <div class="metric-header">
                <span class="metric-label">Stage 2: Context Recovery Cost (Resumption Lag)</span>
            </div>
            <div style="font-size: 13.5px; color: #E6EDF3; line-height: 1.5;">
                The additional delay required <em>after returning</em> to reconstruct the mental task hierarchy, recall working state, and regain baseline speed.
            </div>
            <div class="metric-footer">
                CRC = max(0, Recovery Duration − Baseline Duration)
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # 2. Established Cognitive Science Literature (Published Research)
    # -------------------------------------------------------------------------
    st.markdown('<div class="page-title" style="font-size: 16px; margin: 24px 0 6px 0;">2. Theoretical Foundations from Cognitive Science</div>', unsafe_allow_html=True)
    st.markdown("""
    RECLAIM grounds its predictive models in two peer-reviewed frameworks from cognitive psychology:
    """)

    t_col1, t_col2 = st.columns(2)
    with t_col1:
        st.markdown("""
        <div class="info-panel" style="margin-top: 0;">
            <div class="info-panel-title">Goal-Activation Model (Altmann & Trafton, 2002)</div>
            <p style="margin: 0; font-size: 13px; color: #8B949E; line-height: 1.5;">
                Mental goals decay exponentially in working memory unless actively rehearsed. When an interruption displaces a primary goal, resuming work requires an associative retrieval process to rebuild activation levels. This retrieval lag accounts for the initial sluggishness observed upon task return.
            </p>
        </div>
        """, unsafe_allow_html=True)

    with t_col2:
        st.markdown("""
        <div class="info-panel" style="margin-top: 0;">
            <div class="info-panel-title">Cognitive Load Theory (Sweller, 1988)</div>
            <p style="margin: 0; font-size: 13px; color: #8B949E; line-height: 1.5;">
                Tasks with high intrinsic cognitive load require maintaining deep mental state trees (such as nested code logic, multi-step math, or drafting complex prose). Disrupting a deep state hierarchy causes near-total eviction, multiplying the time needed to re-orient.
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # 3. Empirical Findings from Local Project Data
    # -------------------------------------------------------------------------
    st.markdown('<div class="page-title" style="font-size: 16px; margin: 24px 0 6px 0;">3. Findings from Collected Experimental Data</div>', unsafe_allow_html=True)
    st.markdown("""
    The findings below are derived from empirical records stored in the local SQLite database (`controlled_experiments` table).
    """)

    conn = get_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM controlled_experiments", conn)
    finally:
        conn.close()

    if df.empty or len(df) < 3:
        st.markdown("""
        <div class="info-panel">
            <div class="info-panel-title">Insufficient Participant Sample Size</div>
            <p style="margin: 0; color: #8B949E;">
                The database currently contains fewer than 3 experiment trials.
                Empirical comparative statistics require additional participant records to generate statistically valid insights.
                As trials are logged, this section will automatically populate.
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Generate empirical insights safely
        insights_list = generate_empirical_insights(df)

        for ins in insights_list:
            st.markdown(f"""
            <div class="info-panel">
                <div class="info-panel-title" style="color: #58A6FF;">{ins['title']}</div>
                <div style="font-size: 13.5px; color: #E6EDF3; margin: 4px 0 6px 0;">
                    <strong>Observed Pattern:</strong> {ins['finding']}
                </div>
                <div style="font-size: 12.5px; color: #8B949E;">
                    <strong>Practical Implication:</strong> {ins['recommendation']}
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Visualizations of Empirical Data
        ch_col1, ch_col2 = st.columns(2)

        with ch_col1:
            st.markdown('<div style="font-size: 13px; font-weight: 600; color: #C9D1D9; margin-bottom: 6px;">Condition Impact: Single vs. Repeated Switching</div>', unsafe_allow_html=True)
            switch_df = df[df["condition"].isin([COND_SINGLE, COND_REPEATED])]
            if not switch_df.empty:
                fig_cond = px.box(
                    switch_df,
                    x="condition",
                    y="crc_seconds",
                    color="condition",
                    color_discrete_map={COND_SINGLE: "#58A6FF", COND_REPEATED: "#F85149"},
                    points="all"
                )
                fig_cond.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="#161B22",
                    height=280,
                    showlegend=False,
                    xaxis=dict(title="", gridcolor="#21262D", color="#8B949E"),
                    yaxis=dict(title="Recovery Cost (s)", gridcolor="#21262D", color="#8B949E"),
                    margin=dict(l=10, r=10, t=10, b=10)
                )
                st.plotly_chart(fig_cond, use_container_width=True)
                st.caption("Distribution of resumption delay across single vs. repeated context switches.")
            else:
                st.info("No comparative condition records available.")

        with ch_col2:
            st.markdown('<div style="font-size: 13px; font-weight: 600; color: #C9D1D9; margin-bottom: 6px;">Cognitive Load: CRC by Task Complexity</div>', unsafe_allow_html=True)
            if "task_complexity" in df.columns:
                comp_stats = df.groupby("task_complexity")["crc_seconds"].mean().reset_index()
                fig_comp = px.bar(
                    comp_stats,
                    x="task_complexity",
                    y="crc_seconds",
                    color="task_complexity",
                    color_discrete_sequence=["#238636", "#D29922", "#F85149"]
                )
                fig_comp.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="#161B22",
                    height=280,
                    showlegend=False,
                    xaxis=dict(title="", gridcolor="#21262D", color="#8B949E"),
                    yaxis=dict(title="Mean CRC (s)", gridcolor="#21262D", color="#8B949E"),
                    margin=dict(l=10, r=10, t=10, b=10)
                )
                st.plotly_chart(fig_comp, use_container_width=True)
                st.caption("Average resumption latency scaling with intrinsic task complexity.")
            else:
                st.info("Complexity data unavailable.")

    # -------------------------------------------------------------------------
    # 4. Methodological Boundaries & Limitations
    # -------------------------------------------------------------------------
    st.markdown('<div class="page-title" style="font-size: 16px; margin: 28px 0 6px 0;">4. Research Limitations & Boundaries</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="note-box">
        <strong>What this research establishes and what it cannot:</strong>
        <ul style="margin: 6px 0 0 16px; padding: 0;">
            <li><strong>Behavioral Latency Proxy:</strong> Context Recovery Cost is operationally defined as excess completion time: <code>max(0, T_recovery − T_baseline)</code>. It measures behavioral latency, not intracranial neural firing or EEG brainwaves.</li>
            <li><strong>Correlation vs. Causation:</strong> Statistical associations between interruption frequency and recovery delay describe empirical tendencies in task sessions, not deterministic causal laws.</li>
            <li><strong>Ambient Browser Boundaries:</strong> Natural browser switching sessions without formal problem-solving testing are classified as <code>UNMEASURED_BROWSER</code>. Recovery time is never fabricated for unmeasured browsing.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

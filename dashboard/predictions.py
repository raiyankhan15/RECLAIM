"""
dashboard/predictions.py - Real-Time ML Context Recovery Cost Predictor
Interactive inference simulator enabling users to manipulate context-switch parameters
and receive instant multi-model predictions, confidence intervals, and cognitive risk tiers.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from ml.predict import predict_crc, get_loaded_models, get_model_metadata
from ml.train import train_and_compare_models
from database.db import get_all_experiments, bulk_insert_experiments
from data.synthetic_data import generate_synthetic_dataset
from config import COMPLEXITY_LEVELS

def render_predictions():
    """Renders the ML prediction simulator."""
    st.markdown('<div class="brand-badge">Supervised Inference</div>', unsafe_allow_html=True)
    st.title("Context Recovery Cost (CRC) Predictor")
    st.markdown(
        "Simulate digital interruptions and forecast the expected resumption lag (CRC in seconds) "
        "before returning to the primary cognitive task."
    )

    models = get_loaded_models()
    metadata = get_model_metadata()

    # If no models found, prompt user to train
    if not models or not metadata:
        st.warning("No trained machine learning models found in `models/` directory.")
        st.info("Train models below using your existing database or generate demonstration data to activate the inference engine.")

        t_col1, t_col2 = st.columns(2)
        with t_col1:
            if st.button("Train Models with Existing Data", type="primary", use_container_width=True):
                df = get_all_experiments(include_synthetic=True)
                if len(df) < 10:
                    st.error(f"Current database has only {len(df)} records. At least 10 records are required.")
                else:
                    with st.spinner("Training regression models..."):
                        res = train_and_compare_models(df, dataset_label="Existing SQLite Records")
                        if res.get("success"):
                            st.success(f"Models trained successfully! Best model: {res.get('best_model_name')}")
                            st.rerun()
                        else:
                            st.error(res.get("error"))

        with t_col2:
            if st.button("Seed 150 Demo Records & Train", type="secondary", use_container_width=True):
                with st.spinner("Seeding demo data and training..."):
                    demo_records = generate_synthetic_dataset(n_samples=150, n_participants=20)
                    bulk_insert_experiments(demo_records)
                    df = get_all_experiments(include_synthetic=True)
                    res = train_and_compare_models(df, dataset_label="Synthetic Demonstration Dataset")
                    if res.get("success"):
                        st.success(f"Training complete! Best model: {res.get('best_model_name')}")
                        st.rerun()
                    else:
                        st.error(res.get("error"))
        return

    # Disclosure Banner
    trained_dataset = metadata.get("dataset_label", "Unknown")
    best_model_name = metadata.get("best_model_name", "Gradient Boosting")
    is_synth_trained = "synthetic" in trained_dataset.lower() or "demo" in trained_dataset.lower()

    if is_synth_trained:
        badge_html = f'<span class="badge-synthetic">Trained on {trained_dataset}</span>'
    else:
        badge_html = f'<span class="badge-real">Trained on {trained_dataset}</span>'

    st.markdown(
        f"<div style='margin-bottom: 20px;'><strong>Model Source:</strong> {badge_html} &nbsp;|&nbsp; "
        f"<strong>Optimal Architecture:</strong> <code style='color: #818CF8;'>{best_model_name}</code></div>",
        unsafe_allow_html=True
    )

    # Interactive Input Controls
    st.subheader("Interruption Scenario Parameters")
    ctrl_col1, ctrl_col2, ctrl_col3 = st.columns(3)

    with ctrl_col1:
        complexity = st.selectbox(
            "Task Complexity Level:",
            ["Easy", "Medium", "Difficult"],
            index=1,
            format_func=lambda x: COMPLEXITY_LEVELS[x]["label"]
        )
        complexity_level = COMPLEXITY_LEVELS[complexity]["level"]

        switch_count = st.slider(
            "Context Switch Count:",
            min_value=1,
            max_value=6,
            value=2,
            help="Number of transitions between applications or tasks during the episode."
        )

    with ctrl_col2:
        interruption_duration = st.slider(
            "Interruption Duration (seconds):",
            min_value=5.0,
            max_value=180.0,
            value=35.0,
            step=5.0,
            help="Time spent away dealing with secondary notification or task."
        )

        interruption_accuracy = st.slider(
            "Distractor Engagement (Accuracy):",
            min_value=0.2,
            max_value=1.0,
            value=0.85,
            step=0.05,
            help="Cognitive engagement level on the secondary task."
        )

    with ctrl_col3:
        baseline_duration = st.slider(
            "Baseline Task Duration (seconds):",
            min_value=10.0,
            max_value=120.0,
            value=COMPLEXITY_LEVELS[complexity]["time_target_seconds"],
            step=5.0,
            help="Normal uninterrupted duration for this task complexity."
        )

        baseline_accuracy = st.slider(
            "Baseline Accuracy:",
            min_value=0.5,
            max_value=1.0,
            value=0.95,
            step=0.05
        )

    # Model Selection
    selected_model = st.selectbox(
        "Active Prediction Model:",
        list(models.keys()),
        index=list(models.keys()).index(best_model_name) if best_model_name in models else 0
    )

    # Execute Prediction
    input_features = {
        "complexity_level": complexity_level,
        "baseline_duration": baseline_duration,
        "baseline_accuracy": baseline_accuracy,
        "interruption_duration": interruption_duration,
        "interruption_accuracy": interruption_accuracy,
        "switch_count": switch_count
    }

    pred_result = predict_crc(input_features, selected_model_name=selected_model)

    if not pred_result.get("success"):
        st.error(pred_result.get("error"))
        return

    predicted_seconds = pred_result["predicted_crc_seconds"]
    overhead_pct = pred_result["time_overhead_percentage"]
    tier_name = pred_result["risk_tier"]
    tier_color = pred_result["risk_color"]
    tier_desc = pred_result["risk_description"]

    st.markdown("<hr style='border-color: #1F2937; margin: 28px 0;'>", unsafe_allow_html=True)

    # Prediction Results Cards
    st.subheader("Predicted Recovery Cost")
    res_col1, res_col2, res_col3 = st.columns([1.2, 1, 1.2])

    with res_col1:
        st.markdown(f"""
        <div class="kpi-card" style="border-color: {tier_color};">
            <div class="kpi-title">Predicted Excess Recovery Time</div>
            <div class="kpi-value" style="color: {tier_color};">+{predicted_seconds:.2f}s</div>
            <div class="kpi-subtitle">Estimated resumption delay to re-engage</div>
        </div>
        """, unsafe_allow_html=True)

    with res_col2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Relative Latency Overhead</div>
            <div class="kpi-value" style="color: {'#EF4444' if overhead_pct > 25 else '#F59E0B'};">+{overhead_pct:.1f}%</div>
            <div class="kpi-subtitle">Baseline: {baseline_duration:.1f}s → Total: {baseline_duration + predicted_seconds:.1f}s</div>
        </div>
        """, unsafe_allow_html=True)

    with res_col3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Cognitive Resumption Risk</div>
            <div class="kpi-value" style="font-size: 1.3rem; color: {tier_color};">{tier_name}</div>
            <div class="kpi-subtitle">{tier_desc}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # Multi-Model Comparison Chart & Gauge
    chart_col1, chart_col2 = st.columns([2, 1.5])

    with chart_col1:
        st.subheader("Cross-Model Comparison")
        all_preds = pred_result.get("all_model_predictions", {})
        model_names = list(all_preds.keys())
        pred_values = [all_preds[m].get("predicted_crc_seconds", 0.0) for m in model_names]
        ci_lowers = [all_preds[m].get("ci_lower", 0.0) for m in model_names]
        ci_uppers = [all_preds[m].get("ci_upper", 0.0) for m in model_names]

        fig_compare = go.Figure()
        fig_compare.add_trace(go.Bar(
            x=model_names,
            y=pred_values,
            marker_color=["#6366F1", "#10B981", "#8B5CF6"][:len(model_names)],
            error_y=dict(
                type="data",
                symmetric=False,
                array=[u - p for u, p in zip(ci_uppers, pred_values)],
                arrayminus=[p - l for p, l in zip(pred_values, ci_lowers)],
                color="#D1D5DB"
            ),
            text=[f"+{v:.2f}s" for v in pred_values],
            textposition="auto"
        ))

        fig_compare.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(17,24,39,0.5)",
            yaxis=dict(title="Predicted CRC (seconds)", gridcolor="#1F2937"),
            margin=dict(l=20, r=20, t=20, b=20)
        )
        st.plotly_chart(fig_compare, use_container_width=True)
        st.caption("Error bars represent 95% confidence intervals based on cross-validation test RMSE.")

    with chart_col2:
        st.subheader("Latency Risk Meter")
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=predicted_seconds,
            number=dict(suffix="s", font=dict(size=36, color="#F9FAFB")),
            gauge=dict(
                axis=dict(range=[0, 40], tickcolor="#9CA3AF"),
                bar=dict(color=tier_color),
                steps=[
                    dict(range=[0, 5], color="rgba(16, 185, 129, 0.25)"),
                    dict(range=[5, 15], color="rgba(245, 158, 11, 0.25)"),
                    dict(range=[15, 28], color="rgba(239, 68, 68, 0.25)"),
                    dict(range=[28, 40], color="rgba(139, 92, 246, 0.25)")
                ],
                threshold=dict(
                    line=dict(color="#EF4444", width=3),
                    thickness=0.75,
                    value=25
                )
            )
        ))
        fig_gauge.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=30, b=20),
            height=260
        )
        st.plotly_chart(fig_gauge, use_container_width=True)
        st.caption("Operational risk gauge: Green (Minimal), Amber (Moderate), Red (High), Purple (Severe).")


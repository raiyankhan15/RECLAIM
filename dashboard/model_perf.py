"""
dashboard/model_perf.py - Machine Learning Model Performance & Evaluation
Displays rigorous cross-model benchmarks (MAE, RMSE, R2), actual vs predicted diagnostics,
residual distributions, feature importances, and leakage-prevention auditing.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from ml.predict import get_model_metadata, get_loaded_models
from ml.train import train_and_compare_models
from database.db import get_all_experiments, get_experiment_counts
from config import FEATURE_COLS

def render_model_performance():
    """Renders the model evaluation and diagnostic interface."""
    st.markdown('<div class="brand-badge">Evaluation & Benchmarks</div>', unsafe_allow_html=True)
    st.title("Model Performance & Diagnostics")
    st.markdown(
        "Empirical evaluation of regression models forecasting Context Recovery Cost. "
        "Strict participant-grouped partitioning and leakage-free feature boundaries ensure validity."
    )

    metadata = get_model_metadata()
    counts = get_experiment_counts()

    # Re-training Controls Card
    with st.expander("Model Retraining & Data Split Configuration", expanded=(metadata is None)):
        st.markdown("#### Train Models on SQLite Database")
        train_col1, train_col2 = st.columns([2, 1])

        with train_col1:
            dataset_source = st.radio(
                "Training Dataset Source:",
                ["All Available Records (Real + Synthetic)", "Real Participant Data Only", "Synthetic Demo Data Only"],
                horizontal=True
            )

        with train_col2:
            st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
            train_clicked = st.button("Train / Retrain Models", type="primary", use_container_width=True)

        if train_clicked:
            if dataset_source == "Real Participant Data Only":
                df_train = get_all_experiments(include_synthetic=False)
                label = "Real Participant Records"
            elif dataset_source == "Synthetic Demo Data Only":
                df_train = get_all_experiments(only_synthetic=True)
                label = "Synthetic Demo Records"
            else:
                df_train = get_all_experiments(include_synthetic=True)
                label = "Combined Real + Synthetic Dataset"

            if len(df_train) < 10:
                st.error(f"Selected dataset has only {len(df_train)} records. At least 10 records are required to train.")
            else:
                with st.spinner("Training Linear Regression, Random Forest, and Gradient Boosting..."):
                    res = train_and_compare_models(df_train, dataset_label=label)
                    if res.get("success"):
                        st.success(f"Models successfully trained! Optimal model: {res.get('best_model_name')}")
                        st.rerun()
                    else:
                        st.error(res.get("error"))

    if not metadata:
        st.warning("No model evaluation metadata found. Please train models above to view benchmarks.")
        return

    # Metadata Header
    trained_at = metadata.get("trained_at", "Unknown")[:19].replace("T", " ")
    trained_dataset = metadata.get("dataset_label", "Unknown")
    total_samples = metadata.get("total_samples", 0)
    train_samples = metadata.get("train_samples", 0)
    test_samples = metadata.get("test_samples", 0)
    best_model_name = metadata.get("best_model_name", "Gradient Boosting")

    is_synth_trained = "synthetic" in trained_dataset.lower() or "demo" in trained_dataset.lower()
    badge_html = f'<span class="badge-synthetic">{trained_dataset}</span>' if is_synth_trained else f'<span class="badge-real">{trained_dataset}</span>'

    st.markdown(f"""
    <div style="background: #111827; border: 1px solid #1F2937; border-radius: 8px; padding: 14px 18px; margin: 16px 0;">
        <strong>Dataset:</strong> {badge_html} &nbsp;|&nbsp;
        <strong>Sample Count:</strong> {total_samples} total ({train_samples} train / {test_samples} test) &nbsp;|&nbsp;
        <strong>Last Trained:</strong> <code>{trained_at}</code> &nbsp;|&nbsp;
        <strong>Top Performer:</strong> <span style="color: #818CF8; font-weight: 600;">{best_model_name}</span>
    </div>
    """, unsafe_allow_html=True)

    # Cross-Model Benchmark Leaderboard Table
    st.subheader("Model Comparison Leaderboard")
    models_data = metadata.get("models", {})

    leaderboard_rows = []
    for name, data in models_data.items():
        metrics = data.get("metrics", {})
        leaderboard_rows.append({
            "Model Architecture": name,
            "MAE (Mean Absolute Error)": f"{metrics.get('MAE', 0.0):.3f}s",
            "RMSE (Root Mean Squared Error)": f"{metrics.get('RMSE', 0.0):.3f}s",
            "R² Score (Variance Explained)": f"{metrics.get('R2', 0.0):.3f}",
            "Status": "★ Top Model" if name == best_model_name else "Candidate"
        })

    leaderboard_df = pd.DataFrame(leaderboard_rows)
    st.dataframe(leaderboard_df, use_container_width=True, hide_index=True)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # Model Diagnostics: Actual vs Predicted & Feature Importances
    col_diag1, col_diag2 = st.columns(2)

    with col_diag1:
        st.subheader("Actual vs. Predicted CRC (Test Set)")
        best_data = models_data.get(best_model_name, {})
        sample_preds = best_data.get("sample_predictions", [])

        if sample_preds:
            sp_df = pd.DataFrame(sample_preds)
            fig_avp = go.Figure()

            # Scatter points
            fig_avp.add_trace(go.Scatter(
                x=sp_df["actual"],
                y=sp_df["predicted"],
                mode="markers",
                marker=dict(color="#6366F1", size=9, opacity=0.85, line=dict(color="#818CF8", width=1)),
                name="Hold-Out Test Cases"
            ))

            # Ideal identity diagonal line
            min_v = min(sp_df["actual"].min(), sp_df["predicted"].min()) * 0.9
            max_v = max(sp_df["actual"].max(), sp_df["predicted"].max()) * 1.1
            fig_avp.add_trace(go.Scatter(
                x=[min_v, max_v],
                y=[min_v, max_v],
                mode="lines",
                line=dict(color="#9CA3AF", dash="dash"),
                name="Ideal Prediction (y = x)"
            ))

            fig_avp.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(17,24,39,0.5)",
                xaxis=dict(title="Actual CRC (seconds)", gridcolor="#1F2937"),
                yaxis=dict(title="Predicted CRC (seconds)", gridcolor="#1F2937"),
                margin=dict(l=20, r=20, t=20, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_avp, use_container_width=True)
            st.caption(f"Evaluated on held-out test split for {best_model_name}.")
        else:
            st.info("No sample test predictions recorded.")

    with col_diag2:
        st.subheader("Feature Importance Analysis")
        feat_imp_list = best_data.get("feature_importance", [])

        if feat_imp_list:
            feat_df = pd.DataFrame(feat_imp_list)
            # Map technical feature names to human-readable scientific labels
            label_map = {
                "complexity_level": "Task Complexity Level",
                "interruption_duration": "Interruption Duration",
                "baseline_duration": "Baseline Task Duration",
                "switch_count": "Context Switch Count",
                "switch_density": "Context Switch Density",
                "baseline_accuracy": "Baseline Accuracy",
                "interruption_accuracy": "Distractor Accuracy"
            }
            feat_df["feature_label"] = feat_df["feature"].map(lambda x: label_map.get(x, x))
            feat_df = feat_df.sort_values(by="importance", ascending=True)

            fig_feat = px.bar(
                feat_df,
                x="importance",
                y="feature_label",
                orientation="h",
                color="importance",
                color_continuous_scale="Purples"
            )
            fig_feat.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(17,24,39,0.5)",
                xaxis=dict(title="Relative Importance Weight", gridcolor="#1F2937"),
                yaxis=dict(title="", gridcolor="#1F2937"),
                coloraxis_showscale=False,
                margin=dict(l=20, r=20, t=20, b=20)
            )
            st.plotly_chart(fig_feat, use_container_width=True)
            st.caption(f"Gini feature importance / normalized coefficient weights for {best_model_name}.")
        else:
            st.info("No feature importance weights recorded.")

    st.markdown("<hr style='border-color: #1F2937; margin: 28px 0;'>", unsafe_allow_html=True)

    # Data Leakage Prevention & Scientific Rigor Audit
    st.subheader("Machine Learning Rigor & Data Leakage Prevention")
    st.markdown("""
    <div class="callout">
        <strong>Anti-Leakage Architecture Guarantee:</strong>
        <p style="margin-top: 6px;">
            A common failure in behavioral ML models is <em>target leakage</em> — including post-event indicators
            (such as post-interruption task time or recovery accuracy) as model inputs.
            RECLAIM enforces mathematical boundaries:
        </p>
        <ul style="padding-left: 20px;">
            <li><strong>Strict Pre-Recovery Inputs:</strong> Features are restricted to pre-recovery measurements: <code>complexity_level</code>, <code>interruption_duration</code>, <code>baseline_duration</code>, <code>baseline_accuracy</code>, and <code>switch_count</code>.</li>
            <li><strong>Forbidden Post-Recovery Variables:</strong> <code>recovery_duration</code>, <code>recovery_accuracy</code>, <code>crc_ratio</code>, and <code>accuracy_diff</code> are strictly excluded from the training matrix $X$.</li>
            <li><strong>Group-Aware Partitioning:</strong> When participant data allows, <code>GroupShuffleSplit</code> groups sessions by participant to prevent participant identity leakage across folds.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)


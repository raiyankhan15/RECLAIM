"""
app.py - Main Entrypoint for RECLAIM Platform
Handles global page configuration, theme injection, modern SaaS sidebar navigation,
system health indicators, and route dispatching for the 5 core sections.
"""

import os
from pathlib import Path
import streamlit as st
import urllib.request

# Configure cache directory prior to scientific imports
os.environ.setdefault("MPLCONFIGDIR", "/tmp/contextiq_mpl")

from config import ASSETS_DIR, BASE_DIR
from backend.database import init_all_tables, get_connection
from database.db import get_experiment_counts
from ml.predict import get_model_metadata, get_loaded_models

from dashboard.overview import render_overview
from dashboard.live_tracking import render_live_tracking
from dashboard.recovery_analytics import render_recovery_analytics
from dashboard.predictions import render_predictions
from dashboard.insights import render_insights

# Initialize Database Schema
init_all_tables()

# Streamlit Page Setup
st.set_page_config(
    page_title="RECLAIM — Productivity Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject Custom CSS Styling
def load_css():
    css_file = ASSETS_DIR / "style.css"
    if css_file.exists():
        with open(css_file, "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

def render_sidebar():
    """Renders modern SaaS sidebar navigation without radio buttons."""
    if "nav_page" not in st.session_state:
        st.session_state["nav_page"] = "Dashboard"

    with st.sidebar:
        # Branding Header: RECLAIM Wordmark & Tagline
        st.markdown("""
        <div style="padding: 10px 0 18px 0;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <div style="width: 28px; height: 28px; border-radius: 6px; background: #43C6AC; display: flex; align-items: center; justify-content: center; font-weight: 800; color: #0B0F12; font-size: 14px; letter-spacing: -0.05em;">R</div>
                <div>
                    <h2 style="margin: 0; font-size: 1.25rem; font-weight: 800; color: #F4F6F8; letter-spacing: 0.08em; text-transform: uppercase;">RECLAIM</h2>
                    <span style="font-size: 0.68rem; color: #43C6AC; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;">Productivity Intelligence</span>
                </div>
            </div>
            <p style="font-size: 0.76rem; color: #89949E; margin-top: 10px; line-height: 1.4;">
                Understand your interruptions. Reclaim your focus.
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<hr style='border-color: #1C262F; margin: 0 0 16px 0;'>", unsafe_allow_html=True)

        st.markdown("<div style='font-size: 0.72rem; font-weight: 600; color: #89949E; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 8px; padding-left: 4px;'>Platform Navigation</div>", unsafe_allow_html=True)

        # 5 Requested Sections
        NAV_PAGES = [
            ("Dashboard", "📊"),
            ("Live Tracking", "📡"),
            ("Recovery Analytics", "📈"),
            ("ML Predictions", "🔮"),
            ("Research Insights", "🔬"),
        ]

        # Render Modern Clickable SaaS Navigation Buttons (No radio buttons!)
        for page_name, icon in NAV_PAGES:
            is_active = (st.session_state["nav_page"] == page_name)
            btn_type = "primary" if is_active else "secondary"
            btn_label = f"{icon}  {page_name}"
            
            if st.button(btn_label, key=f"nav_item_{page_name}", use_container_width=True, type=btn_type):
                if st.session_state["nav_page"] != page_name:
                    st.session_state["nav_page"] = page_name
                    st.rerun()

        st.markdown("<hr style='border-color: #1F2937; margin: 24px 0 16px 0;'>", unsafe_allow_html=True)

        # Telemetry Indicators
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM tracking_sessions")
            track_count = cur.fetchone()[0] or 0
            cur.execute("SELECT COUNT(*) FROM interruption_episodes")
            interr_count = cur.fetchone()[0] or 0
        finally:
            conn.close()

        models = get_loaded_models()
        meta = get_model_metadata()
        ml_label = f"Ready ({meta.get('best_model_name', 'Trained')})" if models and meta else ("No Models" if not models else "Ready")

        # FastAPI Live Connection Ping
        try:
            with urllib.request.urlopen("http://127.0.0.1:8000/api/health", timeout=0.4) as resp:
                fastapi_online = (resp.status == 200)
        except Exception:
            fastapi_online = False

        api_color = "#43C6AC" if fastapi_online else "#E05252"
        api_text = "Online (:8000)" if fastapi_online else "Offline"

        st.markdown(f"""
        <div style="background: #11171C; border: 1px solid #1C262F; border-radius: 10px; padding: 14px; font-size: 0.78rem;">
            <div style="font-weight: 700; color: #F4F6F8; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.06em; font-size: 0.72rem;">System Telemetry</div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                <span style="color: #89949E;">FastAPI Server:</span>
                <span style="color: {api_color}; font-weight: 600;">● {api_text}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                <span style="color: #89949E;">Browser Sessions:</span>
                <span style="color: #43C6AC; font-weight: 600;">● {track_count} active</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                <span style="color: #89949E;">Interruptions:</span>
                <span style="color: #E9A23B; font-weight: 600;">● {interr_count} episodes</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span style="color: #89949E;">ML Engine:</span>
                <span style="color: #7298F5; font-weight: 600;">● {ml_label}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style="margin-top: 20px; font-size: 0.72rem; color: #89949E; text-align: center;">
            RECLAIM • Productivity Intelligence<br>
            Understand your interruptions. Reclaim your focus.
        </div>
        """, unsafe_allow_html=True)

    return st.session_state["nav_page"]

def main():
    current_page = render_sidebar()

    if current_page == "Dashboard":
        render_overview()
    elif current_page == "Live Tracking":
        render_live_tracking()
    elif current_page == "Recovery Analytics":
        render_recovery_analytics()
    elif current_page == "ML Predictions":
        render_predictions()
    elif current_page == "Research Insights":
        render_insights()

if __name__ == "__main__":
    main()

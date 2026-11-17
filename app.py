"""
app.py - Main entrypoint for the RECLAIM platform.
Page config, theme injection, sidebar navigation, system status, and routing.
All visual styling lives in assets/style.css; this file only emits semantic classes.
"""

import os
import urllib.request
from pathlib import Path

import streamlit as st

# Configure cache directory prior to scientific imports
os.environ.setdefault("MPLCONFIGDIR", "/tmp/contextiq_mpl")

from config import ASSETS_DIR
from backend.database import init_all_tables, get_connection
from ml.predict import get_model_metadata, get_loaded_models

from dashboard.overview import render_overview
from dashboard.live_tracking import render_live_tracking
from dashboard.recovery_analytics import render_recovery_analytics
from dashboard.predictions import render_predictions
from dashboard.insights import render_insights
from dashboard.experiment_lab import render_experiment_lab

init_all_tables()

st.set_page_config(
    page_title="RECLAIM | Productivity Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)


def load_css():
    css_file = ASSETS_DIR / "style.css"
    if css_file.exists():
        st.markdown(f"<style>{css_file.read_text()}</style>", unsafe_allow_html=True)


load_css()

# (label, Material icon). Requires a recent Streamlit (>= 1.40 recommended).
NAV_PAGES = [
    ("Dashboard", ":material/space_dashboard:"),
    ("Live Tracking", ":material/sensors:"),
    ("Recovery Analytics", ":material/show_chart:"),
    ("ML Predictions", ":material/psychology:"),
    ("Experiment Lab", ":material/experiment:"),
    ("Research Insights", ":material/science:"),
]


def _status_row(label: str, value: str, tone: str) -> str:
    """One status line: label on the left, coloured pill on the right.
    tone is one of: ok, warn, bad, info, idle (see .rc-pill in style.css)."""
    return (
        f'<div class="rc-status-row"><span class="rc-status-label">{label}</span>'
        f'<span class="rc-pill rc-pill-{tone}"><i></i>{value}</span></div>'
    )


def _api_url():
    """Where the FastAPI backend lives. Set RECLAIM_API_URL (env var or Streamlit secret)
    once the API is hosted. Locally it defaults to localhost. On Streamlit Cloud with no
    URL configured there is no backend to reach, so return None (demo mode)."""
    url = os.environ.get("RECLAIM_API_URL")
    if not url:
        try:
            url = st.secrets.get("RECLAIM_API_URL")
        except Exception:
            url = None
    if url:
        return url.rstrip("/")
    if Path("/mount/src").exists():  # Streamlit Community Cloud
        return None
    return "http://127.0.0.1:8000"


def _api_online(url: str) -> bool:
    try:
        with urllib.request.urlopen(f"{url}/api/health", timeout=0.8) as resp:
            return resp.status == 200
    except Exception:
        return False


def render_sidebar() -> str:
    if "nav_page" not in st.session_state:
        st.session_state["nav_page"] = "Dashboard"

    with st.sidebar:
        # Brand: the only place the RECLAIM wordmark appears on screen
        st.markdown(
            '<div class="rc-brand">'
            '<div class="rc-logo">R</div>'
            '<div><div class="rc-wordmark">Reclaim</div>'
            '<div class="rc-tagline">Understand your interruptions.<br>Reclaim your focus.</div></div>'
            "</div>",
            unsafe_allow_html=True,
        )

        for page_name, icon in NAV_PAGES:
            is_active = st.session_state["nav_page"] == page_name
            if st.button(
                page_name,
                icon=icon,
                key=f"nav_item_{page_name}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                if not is_active:
                    st.session_state["nav_page"] = page_name
                    st.rerun()

        # System status
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM tracking_sessions")
            session_count = cur.fetchone()[0] or 0
            cur.execute("SELECT COUNT(*) FROM interruption_episodes")
            episode_count = cur.fetchone()[0] or 0
        finally:
            conn.close()

        models = get_loaded_models()
        meta = get_model_metadata()
        if models:
            ml_text = (meta or {}).get("best_model_name", "Trained")
            ml_tone = "info"
        else:
            ml_text, ml_tone = "No model", "bad"

        api_url = _api_url()
        if api_url is None:
            api_row = _status_row("API server", "Demo mode", "idle")
        else:
            api_up = _api_online(api_url)
            api_row = _status_row("API server", "Online" if api_up else "Offline", "ok" if api_up else "bad")

        st.markdown(
            '<div class="rc-status">'
            '<div class="rc-status-title">System status</div>'
            + api_row
            + _status_row("Sessions", f"{session_count} tracked", "ok" if session_count else "idle")
            + _status_row("Interruptions", f"{episode_count} logged", "warn" if episode_count else "idle")
            + _status_row("ML engine", ml_text, ml_tone)
            + "</div>",
            unsafe_allow_html=True,
        )

    return st.session_state["nav_page"]


def main():
    page = render_sidebar()
    {
        "Dashboard": render_overview,
        "Live Tracking": render_live_tracking,
        "Recovery Analytics": render_recovery_analytics,
        "ML Predictions": render_predictions,
        "Experiment Lab": render_experiment_lab,
        "Research Insights": render_insights,
    }[page]()


if __name__ == "__main__":
    main()
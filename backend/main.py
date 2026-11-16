"""
backend/main.py - FastAPI Service for RECLAIM Chrome Extension Event Ingestion
Provides REST endpoints for tab switching, interruption episodes, session management,
and real-time telemetry streaming to the analytics dashboard.
"""

import json
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from backend.database import get_connection, init_all_tables
from backend.schemas import (
    StartSessionRequest,
    StopSessionRequest,
    TabSwitchEventRequest,
    InterruptionEpisodeRequest,
    WindowFocusEventRequest,
    IdleEventRequest,
    StandardResponse
)
from core.tracking import sanitize_url

app = FastAPI(
    title="RECLAIM Ingestion API",
    description="High-throughput event ingestion API connecting RECLAIM Chrome Extension and SQLite analytics engine.",
    version="1.0.0"
)

# Enable CORS for Chrome Extension (chrome-extension://*) and Local Streamlit UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_all_tables()

@app.get("/api/health", response_model=StandardResponse)
def health_check():
    """Health endpoint for extension and dashboard connectivity checks."""
    return StandardResponse(status="success", message="RECLAIM API is healthy and operational.")

@app.post("/api/session/start", response_model=StandardResponse)
def start_session(payload: StartSessionRequest):
    """Initializes or updates a browser tracking session with designated primary task tab."""
    conn = get_connection()
    cursor = conn.cursor()
    now_str = (payload.timestamp or datetime.now()).isoformat()

    try:
        clean_domain, clean_category = sanitize_url(payload.primary_url)
        cursor.execute("""
            INSERT INTO tracking_sessions (
                session_id, start_time, primary_tab_id, primary_domain,
                primary_category, status, total_switches, total_interruption_time
            ) VALUES (?, ?, ?, ?, ?, 'ACTIVE', 0, 0.0)
            ON CONFLICT(session_id) DO UPDATE SET
                primary_tab_id=excluded.primary_tab_id,
                primary_domain=excluded.primary_domain,
                primary_category=excluded.primary_category,
                status='ACTIVE'
        """, (
            payload.session_id,
            now_str,
            payload.primary_tab_id,
            clean_domain,
            clean_category
        ))
        conn.commit()
        return StandardResponse(
            status="success",
            message=f"Session {payload.session_id} active. Primary domain: {clean_domain}",
            data={"session_id": payload.session_id, "primary_domain": clean_domain}
        )
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/api/session/stop", response_model=StandardResponse)
def stop_session(payload: StopSessionRequest):
    """Terminates an active tracking session."""
    conn = get_connection()
    cursor = conn.cursor()
    now_str = (payload.timestamp or datetime.now()).isoformat()

    try:
        cursor.execute("""
            UPDATE tracking_sessions
            SET status='STOPPED', end_time=?
            WHERE session_id=?
        """, (now_str, payload.session_id))
        conn.commit()
        return StandardResponse(status="success", message=f"Session {payload.session_id} terminated.")
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/api/events/tab-switch", response_model=StandardResponse)
def log_tab_switch(payload: TabSwitchEventRequest):
    """Records an individual tab switch event."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        clean_domain, clean_category = sanitize_url(payload.to_url)
        ts_str = payload.timestamp.isoformat()

        cursor.execute("""
            INSERT INTO tab_switch_events (
                session_id, timestamp, from_tab_id, to_tab_id,
                to_domain, to_category, duration_on_tab,
                is_primary, is_interruption
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            payload.session_id,
            ts_str,
            payload.from_tab_id,
            payload.to_tab_id,
            clean_domain,
            clean_category,
            payload.duration_on_tab,
            1 if payload.is_primary else 0,
            1 if payload.is_interruption else 0
        ))

        # Update total switch count in session
        cursor.execute("""
            UPDATE tracking_sessions
            SET total_switches = total_switches + 1
            WHERE session_id = ?
        """, (payload.session_id,))

        conn.commit()
        return StandardResponse(status="success", message="Tab switch recorded.")
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/api/events/interruption-episode", response_model=StandardResponse)
def log_interruption_episode(payload: InterruptionEpisodeRequest):
    """Records a completed grouped interruption episode when returning to the primary tab."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        domains_str = ", ".join(payload.visited_domains) if payload.visited_domains else "unknown"
        cursor.execute("""
            INSERT INTO interruption_episodes (
                session_id, episode_id, start_time, end_time,
                duration_sec, switch_count, visited_domains,
                primary_interruption_category, return_latency_sec,
                recovery_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'UNMEASURED_BROWSER')
            ON CONFLICT(episode_id) DO UPDATE SET
                end_time=excluded.end_time,
                duration_sec=excluded.duration_sec,
                switch_count=excluded.switch_count
        """, (
            payload.session_id,
            payload.episode_id,
            payload.start_time.isoformat(),
            payload.end_time.isoformat(),
            payload.duration_sec,
            payload.switch_count,
            domains_str,
            payload.primary_interruption_category,
            payload.return_latency_sec
        ))

        # Update total interruption duration in session
        cursor.execute("""
            UPDATE tracking_sessions
            SET total_interruption_time = total_interruption_time + ?
            WHERE session_id = ?
        """, (payload.duration_sec, payload.session_id))

        conn.commit()
        return StandardResponse(status="success", message="Interruption episode saved.")
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/api/events/window-focus", response_model=StandardResponse)
def log_window_focus(payload: WindowFocusEventRequest):
    """Logs browser window focus loss or regain."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        event_name = "WINDOW_FOCUS_GAINED" if payload.has_focus else "WINDOW_FOCUS_LOST"
        cursor.execute("""
            INSERT INTO window_and_idle_events (session_id, timestamp, event_type, details)
            VALUES (?, ?, ?, ?)
        """, (payload.session_id, payload.timestamp.isoformat(), event_name, payload.details or ""))
        conn.commit()
        return StandardResponse(status="success", message=f"Focus event {event_name} logged.")
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/api/events/idle", response_model=StandardResponse)
def log_idle_state(payload: IdleEventRequest):
    """Logs user idle or lock transitions."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO window_and_idle_events (session_id, timestamp, event_type, details)
            VALUES (?, ?, ?, ?)
        """, (payload.session_id, payload.timestamp.isoformat(), f"IDLE_{payload.idle_state.upper()}", payload.details or ""))
        conn.commit()
        return StandardResponse(status="success", message=f"Idle state {payload.idle_state} logged.")
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/api/session/current")
def get_current_session():
    """Returns details of the latest active or most recent session."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM tracking_sessions ORDER BY start_time DESC LIMIT 1")
        session_row = cursor.fetchone()
        if not session_row:
            return {"active": False, "session": None}

        sess_dict = dict(session_row)
        # Fetch last 5 switch events
        cursor.execute("""
            SELECT timestamp, to_domain, to_category, is_primary, is_interruption, duration_on_tab
            FROM tab_switch_events
            WHERE session_id = ?
            ORDER BY timestamp DESC LIMIT 5
        """, (sess_dict["session_id"],))
        recent_switches = [dict(r) for r in cursor.fetchall()]

        # Fetch recent interruption episodes
        cursor.execute("""
            SELECT episode_id, duration_sec, switch_count, visited_domains, primary_interruption_category, return_latency_sec
            FROM interruption_episodes
            WHERE session_id = ?
            ORDER BY start_time DESC LIMIT 5
        """, (sess_dict["session_id"],))
        recent_episodes = [dict(r) for r in cursor.fetchall()]

        return {
            "active": sess_dict["status"] == "ACTIVE",
            "session": sess_dict,
            "recent_switches": recent_switches,
            "recent_episodes": recent_episodes
        }
    finally:
        conn.close()

@app.get("/api/analytics/summary")
def get_analytics_summary():
    """Aggregates browser tracking metrics across all sessions."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*), SUM(total_switches), SUM(total_interruption_time) FROM tracking_sessions")
        row = cursor.fetchone()
        total_sessions = row[0] or 0
        total_switches = row[1] or 0
        total_interruption_time = round(row[2] or 0.0, 1)

        cursor.execute("SELECT COUNT(*), AVG(duration_sec) FROM interruption_episodes")
        ep_row = cursor.fetchone()
        total_episodes = ep_row[0] or 0
        avg_interruption_sec = round(ep_row[1] or 0.0, 2)

        return {
            "total_tracked_sessions": total_sessions,
            "total_switches": total_switches,
            "total_interruption_episodes": total_episodes,
            "total_interruption_seconds": total_interruption_time,
            "avg_interruption_seconds": avg_interruption_sec
        }
    finally:
        conn.close()


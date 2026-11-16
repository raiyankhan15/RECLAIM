"""
backend/database.py - Unified SQLite Database for Real-Time Tracking & Controlled Experiments
Stores browser tracking sessions, tab switch events, grouped interruption episodes,
and controlled cognitive experiment trials with strict ACID compliance.
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
import pandas as pd
from config import DB_PATH

def get_connection() -> sqlite3.Connection:
    """Returns a connection to SQLite with Row factory."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_all_tables() -> None:
    """Initializes schemas for both browser tracking and controlled experiments."""
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Tracking Sessions (Extension sessions)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tracking_sessions (
            session_id TEXT PRIMARY KEY,
            start_time DATETIME NOT NULL,
            end_time DATETIME,
            primary_tab_id INTEGER,
            primary_domain TEXT NOT NULL,
            primary_category TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            total_switches INTEGER DEFAULT 0,
            total_interruption_time REAL DEFAULT 0.0,
            notes TEXT
        );
    """)

    # 2. Individual Tab Switch Events
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tab_switch_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            timestamp DATETIME NOT NULL,
            from_tab_id INTEGER,
            to_tab_id INTEGER,
            to_domain TEXT NOT NULL,
            to_category TEXT NOT NULL,
            duration_on_tab REAL DEFAULT 0.0,
            is_primary INTEGER NOT NULL DEFAULT 0,
            is_interruption INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (session_id) REFERENCES tracking_sessions(session_id)
        );
    """)

    # 3. Grouped Interruption Episodes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interruption_episodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            episode_id TEXT UNIQUE NOT NULL,
            start_time DATETIME NOT NULL,
            end_time DATETIME,
            duration_sec REAL DEFAULT 0.0,
            switch_count INTEGER DEFAULT 1,
            visited_domains TEXT,
            primary_interruption_category TEXT,
            return_latency_sec REAL DEFAULT 0.0,
            recovery_status TEXT NOT NULL DEFAULT 'UNMEASURED_BROWSER',
            measured_recovery_sec REAL,
            FOREIGN KEY (session_id) REFERENCES tracking_sessions(session_id)
        );
    """)

    # 4. Window & Idle Events
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS window_and_idle_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            timestamp DATETIME NOT NULL,
            event_type TEXT NOT NULL, -- 'WINDOW_FOCUS_LOST', 'WINDOW_FOCUS_GAINED', 'IDLE_ACTIVE', 'IDLE_LOCKED'
            details TEXT
        );
    """)

    # 5. Controlled Research Experiment Trials (4 Conditions)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS controlled_experiments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trial_id TEXT UNIQUE NOT NULL,
            participant_id TEXT NOT NULL,
            condition TEXT NOT NULL, -- 'CONTROL', 'SINGLE_SWITCH', 'REPEATED_SWITCH', 'HIGH_COMPLEXITY'
            task_complexity TEXT NOT NULL,
            primary_task_category TEXT DEFAULT 'Cognitive Problem Solving',
            interruption_category TEXT DEFAULT 'Memory Challenge Distractor',
            timestamp DATETIME NOT NULL,
            switch_count INTEGER NOT NULL DEFAULT 0,
            switch_density REAL NOT NULL DEFAULT 0.0,
            consecutive_switches INTEGER NOT NULL DEFAULT 0,
            baseline_duration_sec REAL NOT NULL,
            baseline_accuracy REAL NOT NULL,
            interruption_duration_sec REAL NOT NULL,
            return_latency_sec REAL NOT NULL DEFAULT 0.0,
            recovery_duration_sec REAL NOT NULL,
            recovery_accuracy REAL NOT NULL,
            crc_seconds REAL NOT NULL,
            crc_ratio REAL NOT NULL,
            recovery_status TEXT NOT NULL DEFAULT 'RECOVERED',
            consecutive_criteria_met INTEGER DEFAULT 2,
            data_source TEXT NOT NULL DEFAULT 'REAL_EXPERIMENT', -- 'REAL_EXPERIMENT' or 'SYNTHETIC_DEMO'
            notes TEXT
        );
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trial_cond ON controlled_experiments(condition);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trial_source ON controlled_experiments(data_source);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_switch_sess ON tab_switch_events(session_id);")

    conn.commit()
    conn.close()

# Ensure schema exists on load
init_all_tables()


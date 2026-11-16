"""
database/db.py - SQLite Database Management for ContextIQ
Handles schema creation, validation, duplicate prevention, querying, and CSV export.
"""

import sqlite3
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, Any, List
from config import DB_PATH

def get_connection() -> sqlite3.Connection:
    """Creates a connection to the SQLite database with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    """Initializes the database schema if not present."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS experiments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            participant_id TEXT NOT NULL,
            timestamp DATETIME NOT NULL,
            task_complexity TEXT NOT NULL,
            complexity_level INTEGER NOT NULL,
            baseline_duration REAL NOT NULL,
            baseline_accuracy REAL NOT NULL,
            interruption_duration REAL NOT NULL,
            interruption_accuracy REAL NOT NULL,
            switch_count INTEGER NOT NULL,
            recovery_duration REAL NOT NULL,
            recovery_accuracy REAL NOT NULL,
            error_count INTEGER NOT NULL,
            crc_excess_time REAL NOT NULL,
            crc_ratio REAL NOT NULL,
            accuracy_diff REAL NOT NULL,
            switch_density REAL NOT NULL,
            is_synthetic INTEGER NOT NULL DEFAULT 0,
            notes TEXT
        );
    """)
    # Indexes for fast querying
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_is_synthetic ON experiments(is_synthetic);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_complexity ON experiments(complexity_level);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_participant ON experiments(participant_id);")
    conn.commit()
    conn.close()

def validate_experiment_record(record: Dict[str, Any]) -> tuple[bool, str]:
    """
    Validates experimental record constraints before insertion.
    Returns (is_valid, error_message).
    """
    required_fields = [
        "session_id", "participant_id", "task_complexity", "complexity_level",
        "baseline_duration", "baseline_accuracy", "interruption_duration",
        "interruption_accuracy", "switch_count", "recovery_duration",
        "recovery_accuracy", "error_count", "crc_excess_time"
    ]
    for field in required_fields:
        if field not in record:
            return False, f"Missing required field: {field}"
        if record[field] is None:
            return False, f"Field cannot be None: {field}"

    if not str(record["participant_id"]).strip():
        return False, "Participant ID cannot be empty."

    if record["baseline_duration"] < 0 or record["recovery_duration"] < 0 or record["interruption_duration"] < 0:
        return False, "Durations cannot be negative."

    if not (0.0 <= record["baseline_accuracy"] <= 1.0) or not (0.0 <= record["recovery_accuracy"] <= 1.0):
        return False, "Accuracy must be between 0.0 and 1.0."

    if record["complexity_level"] not in [1, 2, 3]:
        return False, "Complexity level must be 1, 2, or 3."

    return True, ""

def insert_experiment(record: Dict[str, Any]) -> tuple[bool, str]:
    """
    Validates and inserts a single experiment record into SQLite.
    Prevents duplicates based on session_id.
    """
    is_valid, msg = validate_experiment_record(record)
    if not is_valid:
        return False, msg

    conn = get_connection()
    cursor = conn.cursor()
    try:
        timestamp_str = record.get("timestamp")
        if isinstance(timestamp_str, datetime):
            timestamp_str = timestamp_str.isoformat()
        elif not timestamp_str:
            timestamp_str = datetime.now().isoformat()

        cursor.execute("""
            INSERT INTO experiments (
                session_id, participant_id, timestamp, task_complexity,
                complexity_level, baseline_duration, baseline_accuracy,
                interruption_duration, interruption_accuracy, switch_count,
                recovery_duration, recovery_accuracy, error_count,
                crc_excess_time, crc_ratio, accuracy_diff, switch_density,
                is_synthetic, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(record["session_id"]),
            str(record["participant_id"]).strip(),
            timestamp_str,
            str(record["task_complexity"]),
            int(record["complexity_level"]),
            float(record["baseline_duration"]),
            float(record["baseline_accuracy"]),
            float(record["interruption_duration"]),
            float(record["interruption_accuracy"]),
            int(record["switch_count"]),
            float(record["recovery_duration"]),
            float(record["recovery_accuracy"]),
            int(record["error_count"]),
            float(record["crc_excess_time"]),
            float(record.get("crc_ratio", 1.0)),
            float(record.get("accuracy_diff", 0.0)),
            float(record.get("switch_density", 0.0)),
            int(record.get("is_synthetic", 0)),
            str(record.get("notes", ""))
        ))
        conn.commit()
        return True, "Record inserted successfully."
    except sqlite3.IntegrityError as e:
        return False, f"Duplicate session or integrity error: {str(e)}"
    except Exception as e:
        return False, f"Database error: {str(e)}"
    finally:
        conn.close()

def bulk_insert_experiments(records: List[Dict[str, Any]]) -> int:
    """Inserts multiple records in a single transaction. Returns count inserted."""
    inserted = 0
    conn = get_connection()
    cursor = conn.cursor()
    try:
        for r in records:
            is_valid, _ = validate_experiment_record(r)
            if not is_valid:
                continue
            timestamp_str = r.get("timestamp")
            if isinstance(timestamp_str, datetime):
                timestamp_str = timestamp_str.isoformat()
            elif not timestamp_str:
                timestamp_str = datetime.now().isoformat()

            cursor.execute("""
                INSERT OR IGNORE INTO experiments (
                    session_id, participant_id, timestamp, task_complexity,
                    complexity_level, baseline_duration, baseline_accuracy,
                    interruption_duration, interruption_accuracy, switch_count,
                    recovery_duration, recovery_accuracy, error_count,
                    crc_excess_time, crc_ratio, accuracy_diff, switch_density,
                    is_synthetic, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(r["session_id"]),
                str(r["participant_id"]).strip(),
                timestamp_str,
                str(r["task_complexity"]),
                int(r["complexity_level"]),
                float(r["baseline_duration"]),
                float(r["baseline_accuracy"]),
                float(r["interruption_duration"]),
                float(r["interruption_accuracy"]),
                int(r["switch_count"]),
                float(r["recovery_duration"]),
                float(r["recovery_accuracy"]),
                int(r["error_count"]),
                float(r["crc_excess_time"]),
                float(r.get("crc_ratio", 1.0)),
                float(r.get("accuracy_diff", 0.0)),
                float(r.get("switch_density", 0.0)),
                int(r.get("is_synthetic", 0)),
                str(r.get("notes", ""))
            ))
            if cursor.rowcount > 0:
                inserted += 1
        conn.commit()
    finally:
        conn.close()
    return inserted

def get_all_experiments(
    include_synthetic: bool = True,
    only_synthetic: bool = False,
    complexity_filter: Optional[str] = None
) -> pd.DataFrame:
    """
    Fetches experiment records as a Pandas DataFrame with optional filters.
    """
    conn = get_connection()
    query = "SELECT * FROM experiments WHERE 1=1"
    params: List[Any] = []

    if only_synthetic:
        query += " AND is_synthetic = 1"
    elif not include_synthetic:
        query += " AND is_synthetic = 0"

    if complexity_filter and complexity_filter != "All":
        query += " AND task_complexity = ?"
        params.append(complexity_filter)

    query += " ORDER BY timestamp DESC"

    try:
        df = pd.read_sql_query(query, conn, params=params)
    finally:
        conn.close()
    return df

def get_experiment_counts() -> Dict[str, int]:
    """Returns total, real, and synthetic record counts."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), SUM(CASE WHEN is_synthetic = 0 THEN 1 ELSE 0 END), SUM(CASE WHEN is_synthetic = 1 THEN 1 ELSE 0 END) FROM experiments")
    row = cursor.fetchone()
    conn.close()
    total = row[0] if row and row[0] is not None else 0
    real = row[1] if row and row[1] is not None else 0
    synthetic = row[2] if row and row[2] is not None else 0
    return {"total": total, "real": real, "synthetic": synthetic}

def clear_experiments(only_synthetic: bool = False) -> int:
    """Clears either all records or synthetic records only."""
    conn = get_connection()
    cursor = conn.cursor()
    if only_synthetic:
        cursor.execute("DELETE FROM experiments WHERE is_synthetic = 1")
    else:
        cursor.execute("DELETE FROM experiments")
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted

# Ensure table is ready on module import
init_db()


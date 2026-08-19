"""
SQLite Storage for Detected Anomalies
----------------------------------------
Stores every detected anomaly so the dashboard can show history/trends.
"""

import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).resolve().parent / "anomalies.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS anomalies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            detected_at TEXT,
            log_timestamp TEXT,
            server TEXT,
            cpu REAL,
            mem REAL,
            failed_logins INTEGER,
            resp_ms REAL,
            error_count INTEGER,
            ml_score REAL,
            rule_violations TEXT,
            severity TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_anomaly(entry: dict, ml_score: float, rule_violations, severity: str = "MEDIUM"):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO anomalies (detected_at, log_timestamp, server, cpu, mem,
                                failed_logins, resp_ms, error_count, ml_score,
                                rule_violations, severity)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        entry["timestamp"], entry["server"], entry["cpu"], entry["mem"],
        entry["failed_logins"], entry["resp_ms"], entry["error_count"],
        ml_score, "; ".join(rule_violations), severity,
    ))
    conn.commit()
    conn.close()


def get_all_anomalies(limit: int = 100):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM anomalies ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    init_db()
    print(f"Database ready at: {DB_PATH}")
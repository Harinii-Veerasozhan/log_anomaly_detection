"""
PostgreSQL Storage for Detected Anomalies
---------------------------------------------
Same interface as storage/database.py but backed by Postgres so Grafana
can connect directly as a data source.

Install first: pip install psycopg2-binary
"""

import psycopg2
import os
from datetime import datetime

DB_CONFIG = {
    "host": os.environ.get("POSTGRES_HOST", "localhost"),
    "port": int(os.environ.get("POSTGRES_PORT", "5432")),
    "dbname": os.environ.get("POSTGRES_DB", "anomalies"),
    "user": os.environ.get("POSTGRES_USER", "loganomaly"),
    "password": os.environ.get("POSTGRES_PASSWORD", "loganomaly"),
}


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS anomalies (
            id SERIAL PRIMARY KEY,
            detected_at TIMESTAMP,
            log_timestamp TEXT,
            server TEXT,
            cpu REAL,
            mem REAL,
            failed_logins INTEGER,
            resp_ms REAL,
            error_count INTEGER,
            ml_score REAL,
            rule_violations TEXT,
            severity TEXT,
            explanation TEXT,
            log_type TEXT DEFAULT 'system_metrics'
        )
    """)
    cur.execute("ALTER TABLE anomalies ADD COLUMN IF NOT EXISTS explanation TEXT")
    cur.execute("ALTER TABLE anomalies ADD COLUMN IF NOT EXISTS log_type TEXT DEFAULT 'system_metrics'")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS remediation_actions (
            id SERIAL PRIMARY KEY,
            detected_at TIMESTAMP,
            anomaly_id INTEGER REFERENCES anomalies(id),
            action_type TEXT,
            target TEXT,
            status TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS blocked_entities (
            id SERIAL PRIMARY KEY,
            blocked_at TIMESTAMP,
            identifier TEXT,
            reason TEXT,
            anomaly_id INTEGER REFERENCES anomalies(id)
        )
    """)
    conn.commit()
    cur.close()
    conn.close()


def save_anomaly(entry: dict, ml_score: float, rule_violations, severity: str = "MEDIUM",
                 explanation: str = "", log_type: str = "system_metrics"):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO anomalies (detected_at, log_timestamp, server, cpu, mem,
                                failed_logins, resp_ms, error_count, ml_score,
                                rule_violations, severity, explanation, log_type)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        datetime.now(), entry["timestamp"], entry["server"], entry["cpu"], entry["mem"],
        entry["failed_logins"], entry["resp_ms"], entry["error_count"],
        ml_score, "; ".join(rule_violations), severity, explanation, log_type,
    ))
    anomaly_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return anomaly_id


def save_remediation_action(anomaly_id, action_type: str, target: str, status: str = "SIMULATED"):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO remediation_actions (detected_at, anomaly_id, action_type, target, status)
        VALUES (%s, %s, %s, %s, %s)
    """, (datetime.now(), anomaly_id, action_type, target, status))
    conn.commit()
    cur.close()
    conn.close()


def save_blocked_entity(anomaly_id, identifier: str, reason: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO blocked_entities (blocked_at, identifier, reason, anomaly_id)
        VALUES (%s, %s, %s, %s)
    """, (datetime.now(), identifier, reason, anomaly_id))
    conn.commit()
    cur.close()
    conn.close()


def get_all_anomalies(limit: int = 100):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM anomalies ORDER BY id DESC LIMIT %s", (limit,))
    columns = [desc[0] for desc in cur.description]
    rows = [dict(zip(columns, row)) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return rows


if __name__ == "__main__":
    init_db()
    print("Postgres anomalies table ready.")
"""
Streamlit Dashboard - Anomaly Monitoring
--------------------------------------------
Run:
    streamlit run dashboard/app.py
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
import time
from storage.postgres_database import get_all_anomalies, init_db

st.set_page_config(page_title="IT Log Anomaly Dashboard", layout="wide")
st.title("🖥️ Real-Time IT Log Anomaly Detection Dashboard")

init_db()

placeholder = st.empty()

while True:
    anomalies = get_all_anomalies(limit=200)

    with placeholder.container():
        if not anomalies:
            st.info("No anomalies detected yet. Run `python main.py` and `python ingestion/log_generator.py` to generate live data.")
        else:
            df = pd.DataFrame(anomalies)

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Anomalies", len(df))
            col2.metric("High Severity", len(df[df["severity"] == "HIGH"]))
            col3.metric("Medium Severity", len(df[df["severity"] == "MEDIUM"]))
            col4.metric("Servers Affected", df["server"].nunique())

            st.subheader("CPU % over time (anomalous entries)")
            st.line_chart(df.set_index("detected_at")[["cpu", "mem"]])

            st.subheader("Recent Anomalies")
            st.dataframe(
                df[["detected_at", "server", "severity", "cpu", "mem",
                    "failed_logins", "resp_ms", "error_count", "rule_violations"]],
                use_container_width=True,
            )

    time.sleep(3)
    st.rerun()
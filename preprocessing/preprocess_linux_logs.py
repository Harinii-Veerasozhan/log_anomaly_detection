"""
Preprocesses Linux auth logs (SSH login attempts, failures) into per-minute
aggregated features suitable for anomaly detection.

Run:
    python preprocessing/preprocess_linux_logs.py
"""

import re
import pandas as pd
from pathlib import Path

RAW_FILE = Path(__file__).resolve().parent.parent / "data" / "raw" / "linux.logs"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LINE_PATTERN = re.compile(
    r"^(?P<month>\w+)\s+(?P<day>\d+)\s+(?P<time>[\d:]+)\s+(?P<host>\S+)\s+(?P<process>[\w\(\)_]+)\[?\d*\]?:\s*(?P<message>.+)"
)


def parse_line(line: str):
    match = LINE_PATTERN.match(line.strip())
    if not match:
        return None
    d = match.groupdict()
    is_failure = "authentication failure" in d["message"].lower()
    is_unknown_user = "user unknown" in d["message"].lower()
    rhost_match = re.search(r"rhost=(\S+)", d["message"])
    rhost = rhost_match.group(1) if rhost_match else None

    return {
        "month": d["month"], "day": d["day"], "time": d["time"],
        "host": d["host"], "process": d["process"],
        "is_failure": int(is_failure),
        "is_unknown_user": int(is_unknown_user),
        "rhost": rhost,
        "message": d["message"],
    }


def aggregate_by_minute(df: pd.DataFrame) -> pd.DataFrame:
    # Group by day + minute (drop seconds) to get per-minute activity windows
    df["minute"] = df["day"] + "_" + df["time"].str.slice(0, 5)  # e.g. "14_15:16"

    agg = df.groupby("minute").agg(
        total_events=("is_failure", "count"),
        failed_login_count=("is_failure", "sum"),
        unknown_user_count=("is_unknown_user", "sum"),
        distinct_rhosts=("rhost", "nunique"),
    ).reset_index()

    return agg


if __name__ == "__main__":
    print(f"Reading {RAW_FILE} ...")
    rows = []
    with open(RAW_FILE, "r", errors="ignore") as f:
        for line in f:
            parsed = parse_line(line)
            if parsed:
                rows.append(parsed)

    df = pd.DataFrame(rows)
    print(f"Parsed {len(df)} lines")

    agg = aggregate_by_minute(df)
    print(f"Aggregated into {len(agg)} one-minute windows")
    print(agg.describe())

    output_path = OUTPUT_DIR / "linux_processed.csv"
    agg.to_csv(output_path, index=False)
    print(f"\nSaved to {output_path}")
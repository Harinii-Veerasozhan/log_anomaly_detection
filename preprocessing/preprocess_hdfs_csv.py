"""
Preprocesses LogHub's structured HDFS CSV files (hdfs_1.csv, hdfs_2.csv, hdfs_3.csv).
Extracts a BlockId from each log line's Content, aggregates per-block features,
and joins with anomaly_label.csv if available for ground-truth labels.

Run:
    python preprocessing/preprocess_hdfs_csv.py
"""

import pandas as pd
import re
import glob
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BLOCK_ID_PATTERN = re.compile(r"blk_-?\d+")


def load_all_hdfs_csvs():
    files = sorted(glob.glob(str(RAW_DIR / "hdfs_*.csv")))
    print(f"Found {len(files)} HDFS CSV files: {files}")
    dfs = [pd.read_csv(f) for f in files]
    df = pd.concat(dfs, ignore_index=True)
    print(f"Combined shape: {df.shape}")
    return df


def extract_block_id(content: str):
    match = BLOCK_ID_PATTERN.search(str(content))
    return match.group() if match else None


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    df["BlockId"] = df["Content"].apply(extract_block_id)
    df = df.dropna(subset=["BlockId"])

    # Aggregate per block: how many events, how many were ERROR/WARN level,
    # how many distinct event types occurred (a common HDFS anomaly signal)
    agg = df.groupby("BlockId").agg(
        event_count=("EventId", "count"),
        distinct_event_types=("EventId", "nunique"),
        error_or_warn_count=("Level", lambda x: (x.isin(["ERROR", "WARN"])).sum()),
    ).reset_index()

    return agg


def join_labels(features: pd.DataFrame) -> pd.DataFrame:
    label_path = RAW_DIR / "anomaly_label.csv"
    if not label_path.exists():
        print("No anomaly_label.csv found - proceeding WITHOUT ground-truth labels.")
        print("You can still train unsupervised, but won't get precision/recall metrics.")
        features["Label"] = "Unknown"
        return features

    labels = pd.read_csv(label_path)
    labels.columns = labels.columns.str.strip()
    merged = features.merge(labels, on="BlockId", how="left")
    merged["Label"] = merged["Label"].fillna("Unknown")
    print(f"Joined labels. Distribution:\n{merged['Label'].value_counts()}")
    return merged


if __name__ == "__main__":
    raw_df = load_all_hdfs_csvs()
    features = build_features(raw_df)
    result = join_labels(features)

    output_path = OUTPUT_DIR / "hdfs_processed.csv"
    result.to_csv(output_path, index=False)
    print(f"\nSaved processed data to {output_path}")
    print(f"Final shape: {result.shape}")
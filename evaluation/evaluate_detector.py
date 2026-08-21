"""Evaluate the hybrid anomaly detector on controlled synthetic data.

Run with:
    python evaluation/evaluate_detector.py
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score

from detection.isolation_forest_model import entry_to_vector
from detection.rule_engine import check_rules
from detection.sclad_model import predict as predict_sclad
from detection.sclad_model import train_model as train_sclad_model


def normal_entry(rng: random.Random) -> dict:
    return {
        "cpu": rng.uniform(20, 45),
        "mem": rng.uniform(30, 60),
        "failed_logins": rng.randint(0, 2),
        "resp_ms": rng.uniform(80, 200),
        "error_count": rng.randint(0, 1),
    }


def anomalous_entry(kind: str) -> dict:
    entry = {
        "cpu": 35,
        "mem": 45,
        "failed_logins": 1,
        "resp_ms": 120,
        "error_count": 0,
    }
    entry.update({
        "cpu_spike": {"cpu": 98},
        "memory_spike": {"mem": 96},
        "failed_logins": {"failed_logins": 45},
        "latency_spike": {"resp_ms": 4500},
        "error_burst": {"error_count": 90},
    }[kind])
    entry["msg"] = kind
    return entry


def evaluate_detector(training_entries, test_entries, labels):
    """Return classification metrics for the combined ML and rule detector."""
    features = np.array([entry_to_vector(entry) for entry in training_entries])
    model = IsolationForest(contamination=0.05, random_state=42)
    model.fit(features)

    predictions = []
    for entry in test_entries:
        ml_anomaly = model.predict([entry_to_vector(entry)])[0] == -1
        rule_anomaly = bool(check_rules(entry))
        predictions.append(int(ml_anomaly or rule_anomaly))

    return {
        "precision": precision_score(labels, predictions, zero_division=0),
        "recall": recall_score(labels, predictions, zero_division=0),
        "f1_score": f1_score(labels, predictions, zero_division=0),
        "confusion_matrix": confusion_matrix(labels, predictions).tolist(),
    }


def entry_to_log_line(entry: dict) -> str:
    """Serialize evaluation entries into the raw-line input expected by SCLAD."""
    return (
        f"{entry.get('timestamp', '2025-01-01 00:00:00')} | "
        f"{entry.get('server', 'evaluation')} | {entry.get('level', 'INFO')} | "
        f"CPU={entry['cpu']}% | MEM={entry['mem']}% | "
        f"logins_failed={entry['failed_logins']} | resp_ms={entry['resp_ms']} | "
        f"errors={entry['error_count']} | msg={entry.get('msg', 'heartbeat OK')}"
    )


def evaluate_sclad(training_entries, test_entries, labels):
    """Evaluate SCLAD on the same entries and labels as the hybrid detector."""
    training_lines = [entry_to_log_line(entry) for entry in training_entries]
    test_lines = [entry_to_log_line(entry) for entry in test_entries]
    model = train_sclad_model(training_lines)
    predictions = [int(predict_sclad(model, line)["is_anomaly"]) for line in test_lines]
    return {
        "precision": precision_score(labels, predictions, zero_division=0),
        "recall": recall_score(labels, predictions, zero_division=0),
        "f1_score": f1_score(labels, predictions, zero_division=0),
        "confusion_matrix": confusion_matrix(labels, predictions).tolist(),
    }


def build_evaluation_data():
    rng = random.Random(42)
    training_entries = [normal_entry(rng) for _ in range(300)]
    normal_entries = [normal_entry(rng) for _ in range(100)]
    anomaly_entries = [
        anomalous_entry(kind)
        for kind in [
            "cpu_spike", "memory_spike", "failed_logins", "latency_spike", "error_burst"
        ]
        for _ in range(20)
    ]
    return training_entries, normal_entries + anomaly_entries, [0] * 100 + [1] * 100


if __name__ == "__main__":
    training_entries, test_entries, labels = build_evaluation_data()
    results = {
        "hybrid": evaluate_detector(training_entries, test_entries, labels),
        "sclad": evaluate_sclad(training_entries, test_entries, labels),
    }
    for detector_name, detector_results in results.items():
        print(f"{detector_name}:")
        for name, value in detector_results.items():
            print(f"  {name}: {value}")
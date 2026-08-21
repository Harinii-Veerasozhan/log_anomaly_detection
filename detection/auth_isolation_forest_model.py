"""Isolation Forest detector for rolling authentication activity features."""

from collections import deque
from datetime import datetime, timedelta
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest

MODEL_PATH = Path(__file__).resolve().parent / "models" / "auth_isolation_forest.pkl"
FEATURES = ["failed_attempts_last_minute", "distinct_ips_last_minute", "distinct_usernames_last_minute"]
MODEL_PATH.parent.mkdir(exist_ok=True)


def entry_to_vector(entry: dict):
    return [entry[feature] for feature in FEATURES]


def train_model(training_entries, contamination: float = 0.05):
    model = IsolationForest(contamination=contamination, random_state=42)
    model.fit(np.array([entry_to_vector(entry) for entry in training_entries]))
    joblib.dump(model, MODEL_PATH)
    return model


def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError("No auth Isolation Forest found. Run train_model() first.")
    return joblib.load(MODEL_PATH)


def predict(model, features: dict):
    vector = np.array([entry_to_vector(features)])
    return {
        "is_anomaly": model.predict(vector)[0] == -1,
        "score": round(float(model.decision_function(vector)[0]), 4),
    }


class RollingFeatureWindow:
    def __init__(self, window_seconds: int = 60):
        self.window = timedelta(seconds=window_seconds)
        self.events = deque()

    def features(self, event: dict):
        now = datetime.strptime(event["timestamp"], "%Y-%m-%d %H:%M:%S")
        self.events.append((now, event))
        cutoff = now - self.window
        while self.events and self.events[0][0] < cutoff:
            self.events.popleft()
        recent = [item for _, item in self.events]
        failed = [item for item in recent if not item.get("success", False)]
        return {
            "failed_attempts_last_minute": len(failed),
            "distinct_ips_last_minute": len({item["source_ip"] for item in failed}),
            "distinct_usernames_last_minute": len({item["username"] for item in failed}),
        }
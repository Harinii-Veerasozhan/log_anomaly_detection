"""
Isolation Forest Anomaly Detector
------------------------------------
Trains on "normal" log data, then scores new log entries as normal/anomalous.

Run standalone to train + test on synthetic data:
    python detection/isolation_forest_model.py
"""

import joblib
from pathlib import Path
from sklearn.ensemble import IsolationForest
import numpy as np

MODEL_PATH = Path(__file__).resolve().parent / "models" / "isolation_forest.pkl"
MODEL_PATH.parent.mkdir(exist_ok=True)

FEATURES = ["cpu", "mem", "failed_logins", "resp_ms", "error_count"]


def entry_to_vector(entry: dict) -> list:
    """Turn a parsed log entry dict into a numeric feature vector."""
    return [entry[f] for f in FEATURES]


def train_model(training_entries, contamination: float = 0.05):
    """
    Train Isolation Forest on a list of parsed log entries.
    contamination = expected proportion of anomalies in training data (~5% is a good default).
    """
    X = np.array([entry_to_vector(e) for e in training_entries])
    model = IsolationForest(contamination=contamination, random_state=42)
    model.fit(X)
    model.feature_means_ = np.mean(X, axis=0)
    model.feature_stds_ = np.std(X, axis=0)
    joblib.dump(model, MODEL_PATH)
    print(f"Model trained on {len(training_entries)} entries, saved to {MODEL_PATH}")
    return model


def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError("No trained model found. Run train_model() first.")
    return joblib.load(MODEL_PATH)


def predict(model, entry: dict) -> dict:
    """
    Returns dict with is_anomaly (bool) and score (float, lower = more anomalous).
    """
    X = np.array([entry_to_vector(entry)])
    prediction = model.predict(X)[0]  # -1 = anomaly, 1 = normal
    score = model.decision_function(X)[0]
    return {
        "is_anomaly": prediction == -1,
        "score": round(float(score), 4),
    }


if __name__ == "__main__":
    import random

    random.seed(42)
    training_data = []
    for _ in range(300):
        training_data.append({
            "cpu": random.uniform(20, 45),
            "mem": random.uniform(30, 60),
            "failed_logins": random.randint(0, 2),
            "resp_ms": random.uniform(80, 200),
            "error_count": random.randint(0, 1),
        })

    model = train_model(training_data)

    normal_test = {"cpu": 35, "mem": 45, "failed_logins": 1, "resp_ms": 120, "error_count": 0}
    anomaly_test = {"cpu": 98, "mem": 95, "failed_logins": 45, "resp_ms": 4500, "error_count": 90}

    print("\nNormal entry:", predict(model, normal_test))
    print("Anomalous entry:", predict(model, anomaly_test))
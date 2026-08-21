import sys
import random
import threading
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))

from ingestion.kafka_consumer import watch
from ingestion.auth_kafka_consumer import watch as watch_auth
from detection.auth_isolation_forest_model import RollingFeatureWindow
from detection.auth_isolation_forest_model import load_model as load_auth_model
from detection.auth_isolation_forest_model import predict as predict_auth
from detection.auth_isolation_forest_model import train_model as train_auth_model
from detection.isolation_forest_model import load_model, predict, train_model, MODEL_PATH
from detection.rule_engine import check_rules
from storage.postgres_database import init_db, save_anomaly
from alerts.alert_engine import build_explanation, send_alert
from alerts.remediation_engine import remediate


def ensure_model_exists():
    if MODEL_PATH.exists():
        model = load_model()
        if hasattr(model, "feature_means_") and hasattr(model, "feature_stds_"):
            return model
    import random
    random.seed(42)
    training_data = [{
        "cpu": random.uniform(20, 45), "mem": random.uniform(30, 60),
        "failed_logins": random.randint(0, 2), "resp_ms": random.uniform(80, 200),
        "error_count": random.randint(0, 1),
    } for _ in range(300)]
    return train_model(training_data)


def determine_severity(ml_anomaly, rule_violations):
    if ml_anomaly and rule_violations:
        return "HIGH"
    elif ml_anomaly or rule_violations:
        return "MEDIUM"
    return "LOW"


def process_entry(entry, model):
    ml_result = predict(model, entry)
    rule_violations = check_rules(entry)
    if ml_result["is_anomaly"] or rule_violations:
        severity = determine_severity(ml_result["is_anomaly"], rule_violations)
        features = ["cpu", "mem", "failed_logins", "resp_ms", "error_count"]
        means = dict(zip(features, model.feature_means_))
        stds = dict(zip(features, model.feature_stds_))
        explanation = build_explanation(entry, means, stds)
        anomaly_id = save_anomaly(entry, ml_result["score"], rule_violations, severity, explanation)
        send_alert(entry, ml_result["score"], rule_violations, severity, explanation)
        if severity == "HIGH":
            remediate(entry, anomaly_id, severity)
    else:
        print(f"[{entry['timestamp']}] {entry['server']} - normal")


def ensure_auth_model_exists():
    try:
        return load_auth_model()
    except FileNotFoundError:
        normal = [{
            "failed_attempts_last_minute": random.randint(0, 2),
            "distinct_ips_last_minute": random.randint(1, 2),
            "distinct_usernames_last_minute": random.randint(1, 2),
        } for _ in range(300)]
        return train_auth_model(normal)


def process_auth_entry(entry, model, feature_window):
    features = feature_window.features(entry)
    result = predict_auth(model, features)
    if not result["is_anomaly"]:
        return
    source_ip = entry["source_ip"]
    entry = {
        "timestamp": entry["timestamp"], "server": entry["server"],
        "cpu": 0, "mem": 0, "failed_logins": features["failed_attempts_last_minute"],
        "resp_ms": 0, "error_count": 0,
    }
    violations = check_rules(entry)
    severity = determine_severity(result["is_anomaly"], violations)
    explanation = "Authentication rolling-window anomaly: " + ", ".join(
        f"{name}={value}" for name, value in features.items()
    )
    anomaly_id = save_anomaly(entry, result["score"], violations, severity, explanation, "auth")
    send_alert(entry, result["score"], violations, severity, explanation)
    if severity == "HIGH":
        remediate({**entry, "source_ip": source_ip}, anomaly_id, severity)


def main():
    init_db()
    model = ensure_model_exists()
    auth_model = ensure_auth_model_exists()
    auth_window = RollingFeatureWindow()
    print("Consuming from Kafka and detecting anomalies...")
    threading.Thread(target=lambda: watch(lambda entry: process_entry(entry, model)), daemon=True).start()
    watch_auth(lambda entry: process_auth_entry(entry, auth_model, auth_window))


if __name__ == "__main__":
    main()
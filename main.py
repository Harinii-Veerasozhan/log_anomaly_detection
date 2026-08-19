import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))

from ingestion.kafka_consumer import watch
from detection.isolation_forest_model import load_model, predict, train_model, MODEL_PATH
from detection.rule_engine import check_rules
from storage.postgres_database import init_db, save_anomaly
from alerts.alert_engine import send_alert


def ensure_model_exists():
    if MODEL_PATH.exists():
        return load_model()
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
        save_anomaly(entry, ml_result["score"], rule_violations, severity)
        send_alert(entry, ml_result["score"], rule_violations, severity)
    else:
        print(f"[{entry['timestamp']}] {entry['server']} - normal")


def main():
    init_db()
    model = ensure_model_exists()
    print("Consuming from Kafka and detecting anomalies...")
    watch(lambda entry: process_entry(entry, model))


if __name__ == "__main__":
    main()
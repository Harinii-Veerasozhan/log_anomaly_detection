import random

from sklearn.ensemble import IsolationForest

from detection.isolation_forest_model import entry_to_vector
from detection.rule_engine import check_rules


def test_rule_engine_reports_high_cpu():
    entry = {"cpu": 95}

    violations = check_rules(entry)

    assert len(violations) == 1
    assert "High CPU usage" in violations[0]


def test_rule_engine_accepts_normal_entry():
    entry = {
        "cpu": 35,
        "mem": 45,
        "failed_logins": 1,
        "resp_ms": 120,
        "error_count": 0,
    }

    assert check_rules(entry) == []


def test_isolation_forest_detects_controlled_anomaly():
    rng = random.Random(42)
    normal_entries = [{
        "cpu": rng.uniform(20, 45),
        "mem": rng.uniform(30, 60),
        "failed_logins": rng.randint(0, 2),
        "resp_ms": rng.uniform(80, 200),
        "error_count": rng.randint(0, 1),
    } for _ in range(300)]
    model = IsolationForest(contamination=0.05, random_state=42)
    model.fit([entry_to_vector(entry) for entry in normal_entries])

    anomaly = {"cpu": 98, "mem": 96, "failed_logins": 45, "resp_ms": 4500, "error_count": 90}

    assert model.predict([entry_to_vector(anomaly)])[0] == -1
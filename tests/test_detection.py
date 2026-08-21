import random

from sklearn.ensemble import IsolationForest

from detection.isolation_forest_model import entry_to_vector
from detection.rule_engine import check_rules
from detection.sclad_model import predict as predict_sclad
from detection.sclad_model import train_model as train_sclad_model
from alerts.alert_engine import feature_contributions
from alerts.remediation_engine import determine_action


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


def test_sclad_predict_distinguishes_known_and_unseen_template(tmp_path, monkeypatch):
    normal_lines = [
        f"2025-01-01 00:00:{index:02d} | Server-1 | INFO | heartbeat OK"
        for index in range(6)
    ]
    monkeypatch.setattr("detection.sclad_model.MODEL_PATH", tmp_path / "sclad.pkl")
    model = train_sclad_model(normal_lines, n_clusters=1)

    assert predict_sclad(model, normal_lines[0])["is_anomaly"] is False
    assert predict_sclad(model, "2025-01-01 00:01:00 | Server-1 | ERROR | disk corruption detected")["is_anomaly"] is True


def test_feature_contributions_identifies_largest_z_score():
    entry = {"cpu": 40, "mem": 80, "failed_logins": 1, "resp_ms": 120, "error_count": 0}
    means = {"cpu": 30, "mem": 40, "failed_logins": 1, "resp_ms": 100, "error_count": 0}
    standard_deviations = {"cpu": 10, "mem": 5, "failed_logins": 1, "resp_ms": 20, "error_count": 1}

    contributions = feature_contributions(entry, means, standard_deviations)

    assert contributions["mem"] == 8
    assert max(contributions, key=contributions.get) == "mem"


def test_remediation_decision_is_scoped_to_high_severity():
    cpu_action = determine_action({"server": "Server-1", "cpu": 95}, "HIGH")
    auth_action = determine_action({"server": "Auth-1", "source_ip": "10.0.0.9", "failed_logins": 20}, "HIGH")

    assert cpu_action == {"action_type": "SIMULATED_RESTART", "target": "Server-1"}
    assert auth_action == {"action_type": "SIMULATED_BLOCK", "target": "10.0.0.9"}
    assert determine_action({"cpu": 95}, "MEDIUM") is None
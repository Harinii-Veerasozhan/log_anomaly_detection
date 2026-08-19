"""
Rule-Based Anomaly Filter
----------------------------
Simple threshold checks that run alongside the ML model.
Combining rules + ML reduces false positives and gives clear, explainable reasons.
"""

RULES = {
    "cpu": {"threshold": 90, "label": "High CPU usage"},
    "mem": {"threshold": 90, "label": "High memory usage"},
    "failed_logins": {"threshold": 10, "label": "Excessive failed logins (possible brute force)"},
    "resp_ms": {"threshold": 2000, "label": "Response time degraded"},
    "error_count": {"threshold": 20, "label": "Application error burst"},
}


def check_rules(entry: dict):
    """Returns a list of human-readable reasons this entry violates rule thresholds. Empty list = no rule violations."""
    violations = []
    for field, rule in RULES.items():
        if entry.get(field, 0) > rule["threshold"]:
            violations.append(f"{rule['label']} ({field}={entry[field]}, threshold={rule['threshold']})")
    return violations


if __name__ == "__main__":
    test_entry = {"cpu": 95, "mem": 40, "failed_logins": 30, "resp_ms": 150, "error_count": 2}
    print(check_rules(test_entry))
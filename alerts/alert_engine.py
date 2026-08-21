"""
Alert Engine
--------------
Sends notifications when an anomaly is confirmed. Console alert always works.
Slack webhook is optional - set SLACK_WEBHOOK_URL as an environment variable to enable it.
"""

import os
import json
import urllib.request

FEATURES = ["cpu", "mem", "failed_logins", "resp_ms", "error_count"]

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")


def feature_contributions(entry: dict, training_means: dict, training_stds: dict):
    """Return absolute z-score contributions for the monitored features."""
    contributions = {}
    for feature in FEATURES:
        standard_deviation = max(float(training_stds.get(feature, 0.0)), 1e-9)
        contributions[feature] = abs(
            (float(entry.get(feature, 0.0)) - float(training_means.get(feature, 0.0)))
            / standard_deviation
        )
    return contributions


def build_explanation(entry: dict, training_means: dict, training_stds: dict) -> str:
    contributions = feature_contributions(entry, training_means, training_stds)
    largest = max(contributions.values())
    features = [name for name, value in contributions.items() if abs(value - largest) < 1e-9]
    labels = ", ".join(f"{name} ({contributions[name]:.2f} standard deviations)" for name in features)
    return f"Largest feature deviation: {labels}."


def send_console_alert(entry: dict, ml_score: float, rule_violations, severity: str, explanation: str = ""):
    print("\n" + "=" * 60)
    print(f"🚨 ANOMALY ALERT [{severity}]")
    print(f"Time: {entry['timestamp']} | Server: {entry['server']}")
    print(f"ML anomaly score: {ml_score}")
    if explanation:
        print(f"Explanation: {explanation}")
    if rule_violations:
        print("Rule violations:")
        for v in rule_violations:
            print(f"  - {v}")
    print("=" * 60 + "\n")


def send_slack_alert(entry: dict, ml_score: float, rule_violations, severity: str, explanation: str = ""):
    if not SLACK_WEBHOOK_URL:
        return
    message = {
        "text": (
            f"*🚨 Anomaly Alert [{severity}]*\n"
            f"Server: {entry['server']} | Time: {entry['timestamp']}\n"
            f"ML score: {ml_score}\n"
            f"Explanation: {explanation}\n"
            f"Rules triggered: {'; '.join(rule_violations) if rule_violations else 'None (ML-only detection)'}"
        )
    }
    req = urllib.request.Request(
        SLACK_WEBHOOK_URL,
        data=json.dumps(message).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"Slack alert failed: {e}")


def send_alert(entry: dict, ml_score: float, rule_violations, severity: str = "MEDIUM", explanation: str = ""):
    send_console_alert(entry, ml_score, rule_violations, severity, explanation)
    send_slack_alert(entry, ml_score, rule_violations, severity, explanation)
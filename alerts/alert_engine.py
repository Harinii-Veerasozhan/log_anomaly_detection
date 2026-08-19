"""
Alert Engine
--------------
Sends notifications when an anomaly is confirmed. Console alert always works.
Slack webhook is optional - set SLACK_WEBHOOK_URL as an environment variable to enable it.
"""

import os
import json
import urllib.request

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")


def send_console_alert(entry: dict, ml_score: float, rule_violations, severity: str):
    print("\n" + "=" * 60)
    print(f"🚨 ANOMALY ALERT [{severity}]")
    print(f"Time: {entry['timestamp']} | Server: {entry['server']}")
    print(f"ML anomaly score: {ml_score}")
    if rule_violations:
        print("Rule violations:")
        for v in rule_violations:
            print(f"  - {v}")
    print("=" * 60 + "\n")


def send_slack_alert(entry: dict, ml_score: float, rule_violations, severity: str):
    if not SLACK_WEBHOOK_URL:
        return
    message = {
        "text": (
            f"*🚨 Anomaly Alert [{severity}]*\n"
            f"Server: {entry['server']} | Time: {entry['timestamp']}\n"
            f"ML score: {ml_score}\n"
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


def send_alert(entry: dict, ml_score: float, rule_violations, severity: str = "MEDIUM"):
    send_console_alert(entry, ml_score, rule_violations, severity)
    send_slack_alert(entry, ml_score, rule_violations, severity)
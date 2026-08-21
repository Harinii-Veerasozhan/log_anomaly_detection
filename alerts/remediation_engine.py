"""Scoped, simulated remediation for project-controlled anomaly records."""

import logging

from storage.postgres_database import save_blocked_entity, save_remediation_action

LOGGER = logging.getLogger(__name__)


def determine_action(entry: dict, severity: str):
    """Return the permitted action for an entry, or ``None``."""
    if severity != "HIGH":
        return None
    if entry.get("cpu", 0) > 90 or entry.get("mem", 0) > 90:
        return {"action_type": "SIMULATED_RESTART", "target": entry.get("server", "unknown")}
    if entry.get("failed_logins", 0) > 10:
        return {
            "action_type": "SIMULATED_BLOCK",
            "target": entry.get("source_ip", entry.get("server", "unknown")),
        }
    return None


def remediate(entry: dict, anomaly_id, severity: str):
    """Record simulated remediation against database records only."""
    action = determine_action(entry, severity)
    if action is None or anomaly_id is None:
        return None
    if action["action_type"] == "SIMULATED_RESTART":
        LOGGER.warning("Simulated restart for project-controlled target %s", action["target"])
        save_remediation_action(anomaly_id, action["action_type"], action["target"])
    else:
        reason = "High failed-login anomaly"
        save_blocked_entity(anomaly_id, action["target"], reason)
    return action
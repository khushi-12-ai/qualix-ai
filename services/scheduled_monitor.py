"""
Qualix AI — Scheduled Quality Monitoring & Alert Engine
Evaluates categorized rules (Data Quality, Security, Business Risk), enforces alert cooldowns, and manages alert status lifecycles.
"""

import time
from typing import Dict, Any, List, Optional
from services import notification_service

# Pre-configured Rule Engine database
MONITORING_RULES: List[Dict[str, Any]] = [
    {
        "id": "rule_1",
        "name": "Critical Quality Score Drop",
        "category": "Data Quality",
        "metric": "Overall Quality Score",
        "operator": "<",
        "threshold": 70,
        "severity": "CRITICAL",
        "channels": ["Email", "WhatsApp", "Slack"],
        "frequency": "15 mins",
        "cooldown_minutes": 60,
        "last_triggered_ts": 0,
        "active": True
    },
    {
        "id": "rule_2",
        "name": "Anomaly Count Spike",
        "category": "Data Quality",
        "metric": "Anomaly Count",
        "operator": ">",
        "threshold": 5,
        "severity": "HIGH",
        "channels": ["Slack", "Teams"],
        "frequency": "Hourly",
        "cooldown_minutes": 30,
        "last_triggered_ts": 0,
        "active": True
    },
    {
        "id": "rule_3",
        "name": "Malware & Security Threat Flag",
        "category": "Security",
        "metric": "File Threat / Malware Flag",
        "operator": "==",
        "threshold": "INFECTED",
        "severity": "CRITICAL",
        "channels": ["Email", "WhatsApp", "SMS"],
        "frequency": "Immediate",
        "cooldown_minutes": 15,
        "last_triggered_ts": 0,
        "active": True
    },
    {
        "id": "rule_4",
        "name": "Revenue Anomaly Discrepancy",
        "category": "Business Risk",
        "metric": "Revenue Deviation (%)",
        "operator": ">",
        "threshold": 15.0,
        "severity": "WARNING",
        "channels": ["Email", "Slack"],
        "frequency": "Daily",
        "cooldown_minutes": 120,
        "last_triggered_ts": 0,
        "active": True
    }
]

# Active Alerts Feed with Status Lifecycle: OPEN, ACKNOWLEDGED, RESOLVED
ACTIVE_ALERTS_FEED: List[Dict[str, Any]] = [
    {
        "alert_id": "alt_801",
        "rule_id": "rule_1",
        "rule_name": "Critical Quality Score Drop",
        "category": "Data Quality",
        "severity": "CRITICAL",
        "dataset_target": "retail_sales",
        "triggered_at": "2026-08-23 16:45:10",
        "status": "OPEN",  # OPEN, ACKNOWLEDGED, RESOLVED
        "metric_value": "Quality Score = 64%",
        "message": "Quality Score dropped to 64% (Threshold: <70%). High null rate in customer contact columns.",
        "channels_notified": ["Email", "WhatsApp", "Slack"]
    },
    {
        "alert_id": "alt_802",
        "rule_id": "rule_2",
        "rule_name": "Anomaly Count Spike",
        "category": "Data Quality",
        "severity": "HIGH",
        "dataset_target": "inventory_logistics",
        "triggered_at": "2026-08-23 15:30:00",
        "status": "ACKNOWLEDGED",
        "metric_value": "Anomalies = 9 rows",
        "message": "9 inventory line items flagged with negative stock quantity outliers.",
        "channels_notified": ["Slack", "Teams"]
    }
]

def list_monitoring_rules() -> List[Dict[str, Any]]:
    """Returns list of configured monitoring rules."""
    return MONITORING_RULES

def create_or_update_rule(rule_data: Dict[str, Any]) -> Dict[str, Any]:
    """Creates a new rule or updates existing rule."""
    if "id" not in rule_data or not rule_data["id"]:
        rule_data["id"] = f"rule_{len(MONITORING_RULES) + 1}"
    
    rule_data["last_triggered_ts"] = rule_data.get("last_triggered_ts", 0)
    rule_data["active"] = rule_data.get("active", True)
    
    # Check if exists
    for i, r in enumerate(MONITORING_RULES):
        if r["id"] == rule_data["id"]:
            MONITORING_RULES[i] = rule_data
            return rule_data
            
    MONITORING_RULES.append(rule_data)
    return rule_data

def delete_rule(rule_id: str) -> bool:
    """Deletes a rule by ID."""
    global MONITORING_RULES
    initial_len = len(MONITORING_RULES)
    MONITORING_RULES = [r for r in MONITORING_RULES if r["id"] != rule_id]
    return len(MONITORING_RULES) < initial_len

def get_active_alerts() -> List[Dict[str, Any]]:
    """Returns list of active alerts."""
    return ACTIVE_ALERTS_FEED

def acknowledge_alert(alert_id: str, username: str = "Admin") -> Dict[str, Any]:
    """Updates alert status to ACKNOWLEDGED."""
    for alert in ACTIVE_ALERTS_FEED:
        if alert["alert_id"] == alert_id:
            alert["status"] = "ACKNOWLEDGED"
            alert["acknowledged_by"] = username
            alert["acknowledged_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            return alert
    raise ValueError(f"Alert {alert_id} not found.")

def resolve_alert(alert_id: str, username: str = "Admin") -> Dict[str, Any]:
    """Updates alert status to RESOLVED."""
    for alert in ACTIVE_ALERTS_FEED:
        if alert["alert_id"] == alert_id:
            alert["status"] = "RESOLVED"
            alert["resolved_by"] = username
            alert["resolved_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            return alert
    raise ValueError(f"Alert {alert_id} not found.")

def run_monitoring_check(dataset_id: str = "retail_sales", current_metrics: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Executes scheduled monitoring check against target metrics.
    Evaluates rule criteria and cooldown periods.
    Triggers notification dispatches for breached rules.
    """
    now_ts = time.time()
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    
    if not current_metrics:
        current_metrics = {
            "overall_quality_score": 64.5,
            "anomaly_count": 7,
            "malware_status": "CLEAN",
            "revenue_deviation_pct": 18.2
        }

    triggered_alerts = []
    skipped_cooldown = []

    for rule in MONITORING_RULES:
        if not rule.get("active", True):
            continue

        cooldown_sec = rule.get("cooldown_minutes", 60) * 60
        last_ts = rule.get("last_triggered_ts", 0)

        is_breached = False
        metric_val_str = ""
        msg = ""

        if rule["metric"] == "Overall Quality Score":
            val = current_metrics.get("overall_quality_score", 100)
            if rule["operator"] == "<" and val < float(rule["threshold"]):
                is_breached = True
                metric_val_str = f"Quality Score = {val:.1f}%"
                msg = f"Data Quality Score dropped to {val:.1f}% (Threshold: < {rule['threshold']}%)."

        elif rule["metric"] == "Anomaly Count":
            val = current_metrics.get("anomaly_count", 0)
            if rule["operator"] == ">" and val > float(rule["threshold"]):
                is_breached = True
                metric_val_str = f"Anomalies = {val} rows"
                msg = f"Detected {val} anomalous records exceeding threshold (> {rule['threshold']})."

        elif rule["metric"] == "Revenue Deviation (%)":
            val = current_metrics.get("revenue_deviation_pct", 0)
            if rule["operator"] == ">" and val > float(rule["threshold"]):
                is_breached = True
                metric_val_str = f"Revenue Deviation = {val:.1f}%"
                msg = f"Revenue discrepancy variance of {val:.1f}% flagged between POS & Tally."

        if is_breached:
            if (now_ts - last_ts) < cooldown_sec:
                skipped_cooldown.append({
                    "rule_id": rule["id"],
                    "rule_name": rule["name"],
                    "cooldown_remaining_mins": round((cooldown_sec - (now_ts - last_ts)) / 60, 1)
                })
            else:
                # Update last triggered timestamp
                rule["last_triggered_ts"] = now_ts
                
                alert_obj = {
                    "alert_id": f"alt_{int(now_ts)}",
                    "rule_id": rule["id"],
                    "rule_name": rule["name"],
                    "category": rule["category"],
                    "severity": rule["severity"],
                    "dataset_target": dataset_id,
                    "triggered_at": now_str,
                    "status": "OPEN",
                    "metric_value": metric_val_str,
                    "message": msg,
                    "channels_notified": rule["channels"]
                }
                ACTIVE_ALERTS_FEED.insert(0, alert_obj)
                triggered_alerts.append(alert_obj)

                # Dispatch notifications via multi-channel service
                notification_service.dispatch_multi_channel_alert(
                    channels=rule["channels"],
                    rule_title=f"Qualix Alert: {rule['name']}",
                    severity=rule["severity"],
                    message_body=f"Target: {dataset_id} | {msg}"
                )

    return {
        "timestamp": now_str,
        "evaluated_rules": len(MONITORING_RULES),
        "triggered_count": len(triggered_alerts),
        "skipped_cooldown_count": len(skipped_cooldown),
        "triggered_alerts": triggered_alerts,
        "skipped_cooldown": skipped_cooldown
    }

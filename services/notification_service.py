"""
Qualix AI — Multi-Channel Notification Service Engine
Provides dedicated dispatchers for Email, WhatsApp, Slack, MS Teams, and SMS alerts.
"""

import time
from typing import Dict, Any, List, Optional

DISPATCH_HISTORY: List[Dict[str, Any]] = [
    {
        "id": "notif_201",
        "timestamp": "2026-08-23 16:30:00",
        "rule_title": "Data Quality Drop Warning",
        "severity": "HIGH",
        "channel": "WhatsApp",
        "recipient": "+91-9876543210",
        "status": "DELIVERED",
        "content_snippet": "Qualix AI Alert: Retail Sales Quality Score dropped to 64% (Threshold: <70%). 18% missing contacts detected."
    },
    {
        "id": "notif_202",
        "timestamp": "2026-08-23 15:45:00",
        "rule_title": "Fuzzy Duplicate Vendor Spike",
        "severity": "WARNING",
        "channel": "Slack",
        "recipient": "#qualix-alerts-channel",
        "status": "DELIVERED",
        "content_snippet": "Qualix AI Alert: 24 duplicate vendor name variations detected in Tally ledger register."
    }
]

NOTIFICATION_CHANNEL_CONFIGS = {
    "Email": {
        "enabled": True,
        "recipient": "alerts@qualix.ai",
        "sender": "no-reply@qualix.ai",
        "provider": "SMTP / SendGrid"
    },
    "WhatsApp": {
        "enabled": True,
        "recipient": "+91-9876543210",
        "provider": "Meta WhatsApp Business API"
    },
    "Slack": {
        "enabled": True,
        "webhook_url": "https://hooks.slack.com/services/QUALIX/ALERTS/DEV123",
        "channel": "#qualix-alerts"
    },
    "Teams": {
        "enabled": True,
        "webhook_url": "https://qualix.webhook.office.com/webhookb2/alerts",
        "channel": "Data Operations"
    },
    "SMS": {
        "enabled": True,
        "recipient": "+91-9876543210",
        "provider": "Twilio SMS Gateway"
    }
}

def send_email(to_email: str, subject: str, body: str) -> Dict[str, Any]:
    """Simulates sending an Email notification."""
    entry = {
        "id": f"email_{int(time.time())}",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "rule_title": subject,
        "severity": "INFO",
        "channel": "Email",
        "recipient": to_email,
        "status": "DELIVERED",
        "content_snippet": body[:120] + "..." if len(body) > 120 else body
    }
    DISPATCH_HISTORY.insert(0, entry)
    return {"status": "SUCCESS", "channel": "Email", "recipient": to_email}

def send_whatsapp(phone: str, message: str) -> Dict[str, Any]:
    """Simulates sending a WhatsApp alert message."""
    entry = {
        "id": f"wa_{int(time.time())}",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "rule_title": "WhatsApp Alert Dispatch",
        "severity": "HIGH",
        "channel": "WhatsApp",
        "recipient": phone,
        "status": "DELIVERED",
        "content_snippet": message[:120] + "..." if len(message) > 120 else message
    }
    DISPATCH_HISTORY.insert(0, entry)
    return {"status": "SUCCESS", "channel": "WhatsApp", "recipient": phone}

def send_slack(channel_or_url: str, message: str) -> Dict[str, Any]:
    """Simulates sending a Slack Webhook message."""
    entry = {
        "id": f"slack_{int(time.time())}",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "rule_title": "Slack Alert Dispatch",
        "severity": "HIGH",
        "channel": "Slack",
        "recipient": channel_or_url,
        "status": "DELIVERED",
        "content_snippet": message[:120] + "..." if len(message) > 120 else message
    }
    DISPATCH_HISTORY.insert(0, entry)
    return {"status": "SUCCESS", "channel": "Slack", "recipient": channel_or_url}

def send_teams(webhook_url: str, message: str) -> Dict[str, Any]:
    """Simulates sending a Microsoft Teams incoming webhook alert."""
    entry = {
        "id": f"teams_{int(time.time())}",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "rule_title": "Teams Alert Dispatch",
        "severity": "WARNING",
        "channel": "Teams",
        "recipient": "Data Ops Channel",
        "status": "DELIVERED",
        "content_snippet": message[:120] + "..." if len(message) > 120 else message
    }
    DISPATCH_HISTORY.insert(0, entry)
    return {"status": "SUCCESS", "channel": "Teams", "recipient": "Teams Channel"}

def send_sms(phone: str, message: str) -> Dict[str, Any]:
    """Simulates sending an SMS gateway text alert."""
    entry = {
        "id": f"sms_{int(time.time())}",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "rule_title": "SMS Alert Dispatch",
        "severity": "CRITICAL",
        "channel": "SMS",
        "recipient": phone,
        "status": "DELIVERED",
        "content_snippet": message[:120] + "..." if len(message) > 120 else message
    }
    DISPATCH_HISTORY.insert(0, entry)
    return {"status": "SUCCESS", "channel": "SMS", "recipient": phone}

def dispatch_multi_channel_alert(
    channels: List[str],
    rule_title: str,
    severity: str,
    message_body: str
) -> Dict[str, Any]:
    """
    Dispatches an alert payload across all selected notification channels.
    """
    results = {}
    for ch in channels:
        ch_clean = ch.strip().lower()
        if "whatsapp" in ch_clean:
            results["WhatsApp"] = send_whatsapp(NOTIFICATION_CHANNEL_CONFIGS["WhatsApp"]["recipient"], message_body)
        elif "slack" in ch_clean:
            results["Slack"] = send_slack(NOTIFICATION_CHANNEL_CONFIGS["Slack"]["channel"], message_body)
        elif "email" in ch_clean:
            results["Email"] = send_email(NOTIFICATION_CHANNEL_CONFIGS["Email"]["recipient"], rule_title, message_body)
        elif "teams" in ch_clean:
            results["Teams"] = send_teams(NOTIFICATION_CHANNEL_CONFIGS["Teams"]["webhook_url"], message_body)
        elif "sms" in ch_clean:
            results["SMS"] = send_sms(NOTIFICATION_CHANNEL_CONFIGS["SMS"]["recipient"], message_body)
    
    return {
        "rule_title": rule_title,
        "severity": severity,
        "dispatch_count": len(results),
        "channel_results": results
    }

def get_dispatch_history() -> List[Dict[str, Any]]:
    """Returns alert dispatch history log."""
    return DISPATCH_HISTORY[:15]

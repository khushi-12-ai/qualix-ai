import os
import datetime
from typing import List, Dict, Any

AUDIT_LOG_FILE = "audit.log"

def log_event(user: str, action: str, status: str, details: str = ""):
    """Appends a new audit record to the log file."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"{timestamp}\t{user}\t{action}\t{status}\t{details}\n"
    with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line)

def get_logs(
    search_query: str = "",
    filter_user: str = "",
    filter_action: str = "",
    filter_status: str = ""
) -> List[Dict[str, str]]:
    """Reads, parses, and filters audit log lines."""
    if not os.path.exists(AUDIT_LOG_FILE):
        return []
        
    logs = []
    with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 4:
                timestamp = parts[0]
                user = parts[1]
                action = parts[2]
                status = parts[3]
                details = parts[4] if len(parts) > 4 else ""
                
                # Apply filter matchers
                if search_query and search_query.lower() not in line.lower():
                    continue
                if filter_user and filter_user.lower() != user.lower():
                    continue
                if filter_action and filter_action.lower() != action.lower():
                    continue
                if filter_status and filter_status.lower() != status.lower():
                    continue
                    
                logs.append({
                    "time": timestamp,
                    "user": user,
                    "action": action,
                    "status": status,
                    "details": details
                })
    return logs

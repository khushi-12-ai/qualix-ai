from typing import List, Dict

ROLE_PERMISSIONS: Dict[str, List[str]] = {
    "ADMIN": [
        "view_datasets", "upload_datasets", "delete_datasets",
        "view_audit_logs", "manage_users", "view_security_center",
        "view_reports", "change_permissions", "merge_datasets", "change_scan_scope"
    ],
    "DATA ANALYST": [
        "upload_datasets", "analyze_datasets", "view_quality_reports",
        "run_ai_readiness", "use_ai_doctor", "apply_safe_fixes",
        "export_reports", "merge_datasets", "change_scan_scope"
    ],
    "VIEWER": [
        "view_dashboards", "view_scores", "view_reports", "view_datasets",
        "view_merge_results", "view_scan_scope"
    ]
}

def has_permission(role: str, permission: str) -> bool:
    """Verifies if the given user role possesses permission to execute the action."""
    clean_role = str(role).strip().upper()
    if clean_role not in ROLE_PERMISSIONS:
        return False
    return permission in ROLE_PERMISSIONS[clean_role]

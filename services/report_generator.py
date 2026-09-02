import datetime
from typing import Dict, Any

def compile_text_report(dataset_name: str, score_data: Dict[str, Any], user: str) -> Dict[str, Any]:
    """Generates structured report metadata summarizing dataset analysis, quality scores, and recommendations."""
    report_id = f"REP-{datetime.datetime.now().strftime('%Y%m%d')}-{score_data.get('overallReadiness', 50)}"
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return {
        "reportId": report_id,
        "datasetName": dataset_name,
        "generatedBy": user,
        "timestamp": timestamp,
        "qualityScore": score_data.get("quality", 80),
        "mlReadinessScore": score_data.get("mlReadiness", 80),
        "overallReadinessScore": score_data.get("overallReadiness", 80),
        "securityStatus": "Protected (Encrypted)" if score_data.get("security", 100) >= 95 else "Warning (Local Match)",
        "recommendations": [
            "De-duplicate near customer matches using fuzzy logic matching rules.",
            "Normalize categorical variables to standard casings (Title Case).",
            "Exclude columns containing potential target leakage indicators (e.g. cancellation variables)."
        ]
    }

from typing import Dict, Any

def compile_readiness_score(quality_metrics: Dict[str, Any], ml_suitability: Dict[str, Any], security_status: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes aggregated Qualix AI Readiness score (0-100) based on:
    - Data Quality score (Completeness, Consistency, validity)
    - ML readiness (Target leakage penalties, imbalance skew, card constraints)
    - Security scan status (ClamAV success)
    """
    quality_score = quality_metrics.get("overallQuality", 80)
    
    # ML readiness base & penalty
    ml_ready = quality_score
    if ml_suitability.get("hasTargetLeakage"):
        ml_ready -= 25
    if ml_suitability.get("classImbalance", "").startswith("Severe"):
        ml_ready -= 15
    if ml_suitability.get("highCardinalityCol"):
        ml_ready -= 10
    ml_ready = max(10, min(100, ml_ready))
    
    # Security adjustments (blocked or penalty if scans fail or daemon offline)
    sec_penalty = 0
    if security_status.get("status") == "Infected":
        # Entire pipeline block happens at endpoint layer, but represented here as score = 0
        return {
            "overallReadiness": 0,
            "quality": 0,
            "security": 0,
            "mlReadiness": 0,
            "status": "BLOCKED (INFECTED)"
        }
    elif security_status.get("status") == "Unavailable":
        sec_penalty = 5  # minor penalty if ClamAV daemon is offline
        
    # Aggregate weighted overall score
    overall = int(round(
        quality_score * 0.45 +
        ml_ready * 0.35 +
        (100 - sec_penalty) * 0.20
    ))
    overall = max(0, min(100, overall))
    
    # State label
    status = "AI READY" if overall >= 80 else "NEEDS IMPROVEMENT"
    
    return {
        "overallReadiness": overall,
        "quality": quality_score,
        "security": 100 - sec_penalty,
        "mlReadiness": ml_ready,
        "status": status
    }

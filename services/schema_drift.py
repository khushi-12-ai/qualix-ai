from typing import Dict, Any, List
from rapidfuzz import fuzz

def detect_schema_drift(baseline: List[str], new_cols: List[str]) -> Dict[str, Any]:
    """
    Compares a new dataset schema with a historical baseline column schema.
    Detects:
    - Renamed columns (using token_sort_ratio similarity)
    - Removed columns
    - New columns
    Calculates a Schema Stability Score (0-100%).
    """
    baseline_set = set(baseline)
    new_set = set(new_cols)
    
    unchanged = baseline_set.intersection(new_set)
    removed_candidates = list(baseline_set - unchanged)
    new_candidates = list(new_set - unchanged)
    
    renamed = {}
    removed = []
    
    # Try fuzzy matching to find renames
    matched_new = set()
    for rem in removed_candidates:
        best_match = None
        best_score = -1
        
        for new_col in new_candidates:
            if new_col in matched_new:
                continue
            # Compare lowercase cleaned columns
            score = fuzz.token_sort_ratio(rem.lower().replace("_", ""), new_col.lower().replace("_", ""))
            if score >= 75:
                if score > best_score:
                    best_score = score
                    best_match = new_col
                    
        if best_match:
            renamed[rem] = best_match
            matched_new.add(best_match)
        else:
            removed.append(rem)
            
    added = [c for c in new_candidates if c not in matched_new]
    
    # Schema Stability Score:
    # 1.0 per unchanged column, 0.5 per renamed column, 0.0 per removed or added column
    total_baseline = len(baseline)
    score_val = 0.0
    
    if total_baseline > 0:
        score_val += len(unchanged) * 1.0
        score_val += len(renamed) * 0.5
        stability_score = int(round(score_val / total_baseline * 100))
    else:
        stability_score = 100
        
    return {
        "stability_score": max(0, min(100, stability_score)),
        "unchanged": list(unchanged),
        "renamed": renamed,
        "removed": removed,
        "added": added
    }

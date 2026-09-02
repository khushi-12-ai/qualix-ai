import pandas as pd
from typing import Dict, Any, List

def recommend_scan_scope(df: pd.DataFrame, classifications: Dict[str, str]) -> Dict[str, Any]:
    """
    Analyzes columns to recommend inclusion or exclusion in the active scan scope.
    Heuristics:
    - Include target variables, continuous numbers, dates, identifiers.
    - Exclude unstructured text (e.g. notes), system fields, metadata, or high missingness columns.
    """
    recommendations = {}
    num_rows = len(df)
    null_reps = ['nan', '', 'none', 'n/a', '-', 'null', 'unknown']
    
    for col in df.columns:
        col_lower = col.lower()
        role = classifications.get(col, "Feature")
        
        # Calculate missingness
        series = df[col]
        is_empty = series.astype(str).str.strip().str.lower().isin(null_reps) | series.isna()
        missing_pct = (is_empty.sum() / num_rows) * 100 if num_rows > 0 else 0
        
        # Base settings
        rec = "Include"
        importance = "Medium"
        reason = "Standard business feature."
        
        # 1. High missingness
        if missing_pct > 50:
            rec = "Exclude"
            importance = "Low"
            reason = f"High missingness ({missing_pct:.1f}%). Excluded to prevent noise in ML/quality assessment."
        # 2. Critical variables
        elif any(k in col_lower for k in ['revenue', 'sales', 'bill_amount', 'charges', 'valuation', 'salary']):
            rec = "Include"
            importance = "Critical"
            reason = "Core financial metric. Critical for business impact and quality diagnostics."
        elif role == "Target":
            rec = "Include"
            importance = "Critical"
            reason = "Identified as target outcome variable for ML suitability diagnostics."
        # 3. High-importance identifiers/dates
        elif role == "Identifier" or any(k in col_lower for k in ['customer_id', 'client', 'name', 'party', 'phone', 'mobile', 'email', 'gstin']):
            rec = "Include"
            importance = "High"
            reason = "Entity identifier. Crucial for deduplication and data lineage auditing."
        elif role == "Date" or col_lower in ['orderdate', 'invoice_date', 'cancellationdate']:
            rec = "Include"
            importance = "High"
            reason = "Temporal marker. Required for leakage checks and trend diagnostics."
        # 4. System Metadata/Text
        elif role == "System Field" or role == "Text" or any(k in col_lower for k in ['notes', 'comment', 'created_by', 'last_login', 'updated_by']):
            rec = "Exclude"
            importance = "Low"
            reason = "System metadata or unstructured free-text log. Typically irrelevant to ML suitability."
            
        recommendations[col] = {
            "recommendation": rec,
            "importance": importance,
            "reason": reason,
            "issues_count": int(is_empty.sum())
        }
        
    return recommendations

def validate_scope(df: pd.DataFrame, selected_fields: List[str]) -> Dict[str, Any]:
    """
    Validates selected fields and raises warnings if critical columns
    (like Revenue or Target) are excluded from the active scope.
    """
    warnings = {}
    
    # Identify critical items
    critical_columns = []
    for col in df.columns:
        col_lower = col.lower()
        if any(k in col_lower for k in ['revenue', 'sales', 'bill_amount', 'churn', 'target', 'exited']):
            critical_columns.append(col)
            
    for col in critical_columns:
        if col not in selected_fields:
            warnings[col] = f"Warning: Excluding '{col}' may materially affect the reliability of the AI Readiness assessment."
            
    return {
        "valid": len(warnings) == 0,
        "warnings": warnings
    }

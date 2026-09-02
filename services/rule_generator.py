import re
import pandas as pd
from typing import Dict, Any, List

def generate_suggested_rules(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Scans a dataframe and suggests corporate validation rules based on data characteristics.
    """
    suggestions = []
    
    for col in df.columns:
        col_lower = col.lower()
        series = df[col].dropna()
        if series.empty:
            continue
            
        # 1. GSTIN format check
        if "gstin" in col_lower:
            suggestions.append({
                "column": col,
                "rule_type": "GSTIN_FORMAT",
                "description": "GSTIN must match standard 15-character alphanumeric format.",
                "default_enabled": True,
                "confidence": 98
            })
            
        # 2. Negative check for financial/amount fields
        elif any(k in col_lower for k in ['revenue', 'sales', 'profit', 'amount', 'salary', 'price']):
            # Verify if values are mostly positive
            numeric_vals = pd.to_numeric(series, errors='coerce').dropna()
            if not numeric_vals.empty and (numeric_vals >= 0).all():
                suggestions.append({
                    "column": col,
                    "rule_type": "NON_NEGATIVE",
                    "description": f"Value in '{col}' must be greater than or equal to zero.",
                    "default_enabled": True,
                    "confidence": 95
                })
                
        # 3. Discount cap
        elif "discount" in col_lower:
            suggestions.append({
                "column": col,
                "rule_type": "PERCENTAGE_CAP",
                "description": f"Discount rate in '{col}' cannot exceed 100%.",
                "default_enabled": True,
                "confidence": 99
            })
            
        # 4. Future Date check
        elif any(k in col_lower for k in ['date', 'time', 'timestamp', 'created']):
            suggestions.append({
                "column": col,
                "rule_type": "PAST_DATE_ONLY",
                "description": f"Date in '{col}' cannot represent a future date.",
                "default_enabled": True,
                "confidence": 92
            })
            
    return suggestions

def validate_rules(df: pd.DataFrame, active_rules: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validates a dataframe against a list of active rules.
    Returns details of violations and a rule compliance score.
    """
    violations = []
    total_checks = 0
    passed_checks = 0
    
    for rule in active_rules:
        col = rule["column"]
        if col not in df.columns:
            continue
            
        rule_type = rule["rule_type"]
        series = df[col].dropna()
        
        for idx, val in series.items():
            total_checks += 1
            violates = False
            error_msg = ""
            
            if rule_type == "GSTIN_FORMAT":
                gst_str = str(val).strip()
                # Simple check: must be 15 chars and match alphanumeric format
                if len(gst_str) != 15 or not re.match(r'^[0-9]{2}[a-zA-Z]{5}[0-9]{4}[a-zA-Z]{1}[1-9a-zA-Z]{1}[zZ]{1}[0-9a-zA-Z]{1}$', gst_str):
                    violates = True
                    error_msg = f"Invalid GSTIN format: '{gst_str}'."
            elif rule_type == "NON_NEGATIVE":
                try:
                    num_val = float(val)
                    if num_val < 0:
                        violates = True
                        error_msg = f"Negative value detected: {num_val}."
                except Exception:
                    pass
            elif rule_type == "PERCENTAGE_CAP":
                try:
                    num_val = float(str(val).replace('%', '').strip())
                    if num_val > 100:
                        violates = True
                        error_msg = f"Percentage exceeds limit: {num_val}%."
                except Exception:
                    pass
            elif rule_type == "PAST_DATE_ONLY":
                try:
                    dt = pd.to_datetime(val)
                    now = pd.Timestamp.now()
                    if dt > now + pd.Timedelta(days=1): # allow 1 day buffer for timezone differences
                        violates = True
                        error_msg = f"Future date detected: {dt.strftime('%Y-%m-%d')}."
                except Exception:
                    pass
                    
            if violates:
                violations.append({
                    "row_index": idx,
                    "column": col,
                    "value": val,
                    "rule_type": rule_type,
                    "error_msg": error_msg
                })
            else:
                passed_checks += 1
                
    compliance_score = int(round(passed_checks / total_checks * 100)) if total_checks else 100
    
    return {
        "compliance_score": max(0, min(100, compliance_score)),
        "violations_count": len(violations),
        "violations": violations
    }

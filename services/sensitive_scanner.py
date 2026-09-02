import re
import pandas as pd
from typing import Dict, Any, List

def scan_sensitive_data(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Scans a dataframe's columns for sensitive/PII data.
    Categories:
    - PII: Email, Phone, Name, Address
    - Sensitive: GSTIN, PAN, Aadhaar, Bank Account
    - Financial: Revenue, Sales, Paid Amount, Amount
    - Standard: Other columns
    """
    classifications = {}
    sensitive_columns = []
    
    for col in df.columns:
        col_lower = col.lower()
        
        # 1. Financial check
        if any(k in col_lower for k in ['revenue', 'sales', 'profit', 'amount', 'salary', 'bill', 'paid']):
            classifications[col] = "Financial"
        # 2. Sensitive check
        elif any(k in col_lower for k in ['pan', 'aadhaar', 'ssn', 'bank', 'account', 'gstin', 'tax']):
            classifications[col] = "Sensitive"
            sensitive_columns.append(col)
        # 3. PII check
        elif any(k in col_lower for k in ['email', 'phone', 'mobile', 'address', 'contact', 'customer', 'name', 'client']):
            classifications[col] = "PII"
            sensitive_columns.append(col)
        # 4. Standard check
        else:
            classifications[col] = "Standard"
            
    risk_level = "Low"
    if any(classifications[col] == "Sensitive" for col in df.columns):
        risk_level = "High"
    elif any(classifications[col] == "PII" for col in df.columns):
        risk_level = "Medium"
        
    return {
        "classifications": classifications,
        "sensitive_columns": sensitive_columns,
        "risk_level": risk_level
    }

def mask_pii_value(val: Any, category: str) -> str:
    """Masks values based on category (PII/Sensitive)."""
    s = str(val).strip()
    if not s or s.lower() in ['nan', 'none', 'n/a', '-']:
        return s
        
    if "@" in s:  # Email
        parts = s.split("@")
        username = parts[0]
        domain = parts[1] if len(parts) > 1 else ""
        if len(username) > 2:
            return f"{username[:2]}***@{domain}"
        else:
            return f"***@{domain}"
            
    # Phone or numbers
    digits = re.sub(r'\D', '', s)
    if len(digits) >= 8:
        # e.g., 9876543210 -> 98******10
        return f"{s[:2]}******{s[-2:]}"
        
    # Standard masking for text names or codes
    if len(s) > 4:
        return f"{s[:2]}*****{s[-1:]}"
    return "****"

def mask_dataframe_for_role(df: pd.DataFrame, role: str) -> pd.DataFrame:
    """
    Applies data masking rules based on active RBAC role:
    - ADMIN: Full access, no masking.
    - DATA ANALYST: PII & Sensitive fields are masked in previews.
    - VIEWER: Blocked from raw data previews (returns empty or metadata only).
    """
    df_copy = df.copy()
    if role == "ADMIN":
        return df_copy
        
    if role == "VIEWER":
        # Viewers cannot see raw records; return empty preview or headers only
        return pd.DataFrame(columns=df.columns)
        
    # Analysts get masked PII/Sensitive columns
    scan_res = scan_sensitive_data(df)
    classifications = scan_res["classifications"]
    
    for col in df_copy.columns:
        cat = classifications.get(col, "Standard")
        if cat in ["PII", "Sensitive"]:
            df_copy[col] = df_copy[col].apply(lambda x: mask_pii_value(x, cat))
            
    return df_copy

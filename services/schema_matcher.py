import re
import pandas as pd
from typing import Dict, Any, List
from rapidfuzz import fuzz

def normalize_column_name(name: str) -> str:
    """Normalizes column names by converting to lowercase, stripping punctuation, and spaces."""
    if not isinstance(name, str):
        return ""
    name = name.lower().strip()
    name = re.sub(r'[_\-\s]+', ' ', name)
    return " ".join(name.split())

def calculate_column_similarity(target_name: str, source_col: str, series: pd.Series) -> Dict[str, Any]:
    """
    Computes a multi-signal similarity score between a target field name and a source column:
    1. Column Name Similarity (RapidFuzz token_sort_ratio)
    2. Data Type Compatibility
    3. Value Pattern Similarity
    Returns the combined confidence (0-100) and details of the signals.
    """
    target_norm = normalize_column_name(target_name)
    source_norm = normalize_column_name(source_col)
    
    # 1. Name Similarity
    name_sim = float(fuzz.token_sort_ratio(target_norm, source_norm))
    
    # Extra name keyword matches to boost confidence
    keyword_boosts = {
        "Customer_Name": ["client", "party", "name", "customer", "customer name", "party name"],
        "Phone": ["phone", "mobile", "contact", "cell", "telephone"],
        "Revenue": ["revenue", "sales", "bill", "amount", "price", "charges", "transaction"],
        "Invoice_Date": ["date", "time", "orderdate", "invoice date", "timestamp", "created"],
        "GSTIN": ["gstin", "gst", "tax", "registration"],
        "Customer_ID": ["id", "code", "cust", "party id", "customer_id"],
        "Email": ["email", "e-mail", "mailaddress"],
        "Internal_Notes": ["notes", "comment", "desc", "internal"],
        "Created_By": ["created_by", "creator", "admin", "system"],
        "Last_Login": ["login", "last_login", "lastlogin"]
    }
    
    boost = 0.0
    if target_name in keyword_boosts:
        for kw in keyword_boosts[target_name]:
            if kw in source_norm:
                boost = 15.0
                break
    name_sim = min(100.0, name_sim + boost)
    
    # 2. Data Type Compatibility
    # Determine source type
    source_type = "Categorical"
    non_null = series.dropna()
    if not non_null.empty:
        cleaned = non_null.astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False).str.strip()
        try:
            pd.to_numeric(cleaned, errors='raise')
            source_type = "Numeric"
        except Exception:
            try:
                pd.to_datetime(non_null.head(10).astype(str), errors='raise')
                source_type = "DateTime"
            except Exception:
                source_type = "Categorical"
                
    # Determine target type
    target_types = {
        "Customer_ID": "Categorical",
        "Customer_Name": "Categorical",
        "Phone": "Categorical",
        "Email": "Categorical",
        "GSTIN": "Categorical",
        "Revenue": "Numeric",
        "Invoice_Date": "DateTime",
        "Internal_Notes": "Categorical",
        "Created_By": "Categorical",
        "Last_Login": "DateTime"
    }
    target_type = target_types.get(target_name, "Categorical")
    
    if source_type == target_type:
        type_compat = 100.0
    elif (source_type == "DateTime" and target_type == "Categorical") or (source_type == "Categorical" and target_type == "DateTime"):
        type_compat = 80.0
    elif (source_type == "Numeric" and target_type == "Categorical") or (source_type == "Categorical" and target_type == "Numeric"):
        type_compat = 60.0
    else:
        type_compat = 30.0
        
    # 3. Value Pattern Similarity
    pattern_score = 50.0 # base score
    if not non_null.empty:
        sample_vals = non_null.astype(str).head(50).tolist()
        
        if target_name == "Revenue" or target_type == "Numeric":
            numeric_count = sum(1 for v in sample_vals if re.match(r'^\-?\$?\d+[\d,.]*$', v.strip()))
            pattern_score = (numeric_count / len(sample_vals)) * 100.0 if sample_vals else 20.0
        elif target_name in ["Invoice_Date", "Last_Login"] or target_type == "DateTime":
            date_count = sum(1 for v in sample_vals if any(char in v for char in ['-', '/']) or re.search(r'\b\d{4}\b', v))
            pattern_score = (date_count / len(sample_vals)) * 100.0 if sample_vals else 20.0
        elif target_name == "Phone":
            phone_count = sum(1 for v in sample_vals if len(re.sub(r'\D', '', v)) >= 8)
            pattern_score = (phone_count / len(sample_vals)) * 100.0 if sample_vals else 30.0
        elif target_name == "Email":
            email_count = sum(1 for v in sample_vals if '@' in v)
            pattern_score = (email_count / len(sample_vals)) * 100.0 if sample_vals else 20.0
        elif target_name == "GSTIN":
            gstin_count = sum(1 for v in sample_vals if re.match(r'^\d{2}[a-zA-Z]{5}\d{4}[a-zA-Z]{1}\d{1}[zZ]{1}[a-zA-Z0-9]{1}$', v.strip()) or len(v.strip()) == 15)
            pattern_score = (gstin_count / len(sample_vals)) * 100.0 if sample_vals else 20.0
        elif target_name == "Customer_Name":
            # Names contain spaces and no digits/symbols mostly
            name_pattern_count = sum(1 for v in sample_vals if len(v.strip()) > 3 and not re.search(r'\d', v) and ' ' in v)
            pattern_score = (name_pattern_count / len(sample_vals)) * 100.0 if sample_vals else 50.0
            
    # Combine signals
    if non_null.empty:
        combined_score = (name_sim * 0.6) + (type_compat * 0.4)
    else:
        combined_score = (name_sim * 0.4) + (type_compat * 0.3) + (pattern_score * 0.3)
    
    return {
        "confidence": int(round(combined_score)),
        "signals": {
            "name_similarity": int(round(name_sim)),
            "type_compatibility": int(round(type_compat)),
            "pattern_similarity": int(round(pattern_score))
        }
    }

def suggest_column_mapping(dfs: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
    """
    Given a set of dataframes from different sources, suggests mapping their columns
    to standard corporate target fields.
    """
    target_fields = [
        "Customer_ID", "Customer_Name", "Phone", "Email", "GSTIN",
        "Revenue", "Invoice_Date", "Internal_Notes", "Created_By", "Last_Login"
    ]
    
    mappings = []
    
    for target in target_fields:
        mapped_columns = {}
        confidences = []
        signals_log = {}
        
        for source_id, df in dfs.items():
            best_col = None
            best_score = -1
            best_signals = {}
            
            for col in df.columns:
                res = calculate_column_similarity(target, col, df[col])
                if res["confidence"] > best_score:
                    best_score = res["confidence"]
                    best_col = col
                    best_signals = res["signals"]
                    
            # Only map if confidence is above a minimum threshold (e.g. 50%)
            if best_col and best_score >= 50:
                mapped_columns[source_id] = best_col
                confidences.append(best_score)
                signals_log[source_id] = best_signals
                
        if mapped_columns:
            avg_confidence = int(round(sum(confidences) / len(confidences))) if confidences else 0
            
            # Map average confidence to qualitative levels
            if avg_confidence >= 85:
                level = "HIGH"
                reason = "Name similarity, compatible type, and value pattern match across all sources."
            elif avg_confidence >= 60:
                level = "MEDIUM"
                reason = "Partial match: columns aligned but have type or value pattern variations."
            else:
                level = "LOW"
                reason = "Weak match: names do not align clearly or types are incompatible."
                
            mappings.append({
                "target_field": target,
                "confidence": avg_confidence,
                "confidence_level": level,
                "reason": reason,
                "columns": mapped_columns,
                "signals": signals_log
            })
            
    return mappings

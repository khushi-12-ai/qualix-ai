import pandas as pd
from typing import Dict

def classify_fields(df: pd.DataFrame) -> Dict[str, str]:
    """
    Automatically classifies columns into:
    - Identifier
    - Target
    - Feature
    - Date
    - Numeric
    - Categorical
    - Text
    - Metadata
    - System Field
    """
    classifications = {}
    num_rows = len(df)
    
    for col in df.columns:
        col_lower = col.lower()
        series = df[col].dropna()
        unique_cnt = series.nunique()
        unique_ratio = unique_cnt / num_rows if num_rows > 0 else 0.0
        
        # 1. System/Metadata check
        if any(k in col_lower for k in ['created_by', 'updated_by', 'sys_', 'last_login', 'system', 'createdby']):
            classifications[col] = "System Field"
        # 2. Target check
        elif any(k in col_lower for k in ['churn', 'target', 'label', 'exited', 'outcome', 'status', 'revenue', 'sales', 'profit', 'amount']):
            classifications[col] = "Target"
        # 3. Identifier check
        elif any(k in col_lower for k in ['id', 'code', 'number', 'key', 'no', 'num', 'phone', 'mobile', 'email', 'gstin', 'pan', 'tan', 'name', 'customer']) or (unique_ratio > 0.9 and unique_cnt > 5):
            classifications[col] = "Identifier"
        # 4. Date check
        elif any(k in col_lower for k in ['date', 'time', 'timestamp', 'created', 'updated']):
            classifications[col] = "Date"
        # 5. Text check (e.g. comments, notes)
        elif any(k in col_lower for k in ['note', 'desc', 'comment', 'feedback', 'remark', 'text', 'message']):
            classifications[col] = "Text"
        else:
            # Analyze data characteristics
            source_type = "Categorical"
            if not series.empty:
                cleaned = series.astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False).str.strip()
                try:
                    pd.to_numeric(cleaned, errors='raise')
                    source_type = "Numeric"
                except Exception:
                    try:
                        pd.to_datetime(series.head(10).astype(str), errors='raise')
                        source_type = "DateTime"
                    except Exception:
                        source_type = "Categorical"
                        
            if source_type == "Numeric":
                if unique_cnt < 15:
                    classifications[col] = "Categorical"
                else:
                    classifications[col] = "Numeric"
            elif source_type == "DateTime":
                classifications[col] = "Date"
            else:
                if unique_cnt < 25:
                    classifications[col] = "Categorical"
                else:
                    classifications[col] = "Feature"
                    
    return classifications

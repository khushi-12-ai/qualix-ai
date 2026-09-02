import pandas as pd
from typing import Dict, Any, List

def compile_dataset_profile(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyzes the structure and basic statistics of a dataset, returning metadata:
    - Row and column counts
    - Column type classification (numeric, categorical, date)
    - Null distributions
    - Unique cardinalities
    """
    if df.empty:
        return {}
        
    num_rows, num_cols = df.shape
    columns = list(df.columns)
    
    col_profiles = {}
    type_counts = {"Numeric": 0, "Categorical": 0, "DateTime/Other": 0}
    null_reps = ['nan', '', 'none', 'n/a', '-', 'null', 'unknown']
    
    for col in columns:
        series = df[col]
        # Detect cardinalities
        unique_cnt = series.nunique()
        
        # Detect empty counts
        is_empty = series.astype(str).str.strip().str.lower().isin(null_reps) | series.isna()
        empty_count = int(is_empty.sum())
        
        # Classify data type
        col_type = "Categorical"
        non_null_vals = series.dropna()
        if not non_null_vals.empty:
            cleaned_vals = non_null_vals.astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False).str.strip()
            try:
                pd.to_numeric(cleaned_vals, errors='raise')
                col_type = "Numeric"
            except (ValueError, TypeError):
                try:
                    pd.to_datetime(non_null_vals.head(10).astype(str), errors='raise')
                    col_type = "DateTime/Other"
                except Exception:
                    col_type = "Categorical"
                    
        type_counts[col_type] += 1
        
        # Summary statistics
        stats = {}
        if col_type == "Numeric":
            num_series = pd.to_numeric(cleaned_vals, errors='coerce').dropna()
            if not num_series.empty:
                stats = {
                    "mean": float(round(num_series.mean(), 2)),
                    "min": float(round(num_series.min(), 2)),
                    "max": float(round(num_series.max(), 2)),
                    "std": float(round(num_series.std(), 2))
                }
                
        col_profiles[col] = {
            "type": col_type,
            "cardinality": unique_cnt,
            "missing": empty_count,
            "missing_pct": int(round((empty_count / num_rows) * 100)),
            "stats": stats
        }
        
    # Preview
    preview_df = df.head(10).fillna("")
    preview_records = preview_df.to_dict(orient="records")
    
    return {
        "numRows": num_rows,
        "numCols": num_cols,
        "totalCells": num_rows * num_cols,
        "typeCounts": type_counts,
        "columns": columns,
        "colProfiles": col_profiles,
        "dataPreview": preview_records
    }

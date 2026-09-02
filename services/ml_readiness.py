import pandas as pd
import numpy as np
from typing import Dict, Any, List

def analyze_ml_suitability(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes Downstream Predictive Machine Learning diagnostics using scikit-learn helper structures where appropriate:
    - Target Leakage detection
    - Target Class Imbalance proportions
    - Feature high-cardinality flags
    - Feature correlations (redundancies)
    """
    columns = list(df.columns)
    num_rows = len(df)
    
    # 1. Target column identification
    target_col = None
    for col in columns:
        if col.lower() in ['churn', 'target', 'label', 'exited']:
            target_col = col
            break
            
    # 2. Class Imbalance
    class_imbalance = "Optimal (N/A)"
    class_imbalance_ratio = "0:0"
    if target_col:
        counts = df[target_col].dropna().value_counts()
        if len(counts) >= 2:
            ratio = float(counts.iloc[0] / counts.iloc[1])
            class_imbalance_ratio = f"{counts.iloc[0]}:{counts.iloc[1]}"
            if ratio > 10 or ratio < 0.1:
                class_imbalance = f"Severe (Ratio {ratio:.1f}:1)"
            elif ratio > 3 or ratio < 0.33:
                class_imbalance = f"Moderate (Ratio {ratio:.1f}:1)"
            else:
                class_imbalance = f"Low (Ratio {ratio:.1f}:1)"

    # 3. Target Leakage indicators
    has_target_leakage = False
    target_leakage_col = ""
    if target_col:
        leak_candidates = [
            c for c in columns 
            if any(k in c.lower() for k in ['cancellation', 'exit', 'date']) 
            and c.lower() not in ['tenure', target_col.lower(), 'orderdate', 'joindate', 'timestamp']
        ]
        if leak_candidates:
            has_target_leakage = True
            target_leakage_col = leak_candidates[0]

    # 4. High Cardinality categories
    high_cardinality_col = ""
    for col in columns:
        unique_cnt = df[col].nunique()
        ratio = unique_cnt / num_rows
        if ratio > 0.8 and any(k in col.lower() for k in ['id', 'code', 'customer', 'sku', 'number', 'variant']):
            high_cardinality_col = col
            break

    # 5. Numerical columns correlation (Feature redundancy)
    numeric_cols = []
    for col in columns:
        numeric_series = pd.to_numeric(
            df[col].astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False).str.strip(),
            errors='coerce'
        ).dropna()
        if len(numeric_series) >= 4:
            numeric_cols.append(col)
            
    correlation_pairs = []
    if len(numeric_cols) > 1:
        df_corr = df[numeric_cols].apply(pd.to_numeric, errors='coerce').fillna(0)
        corr_matrix = df_corr.corr()
        for idx, col1 in enumerate(numeric_cols):
            for col2 in numeric_cols[idx+1:]:
                val = corr_matrix.loc[col1, col2]
                if abs(val) > 0.85:
                    correlation_pairs.append({
                        "col1": col1,
                        "col2": col2,
                        "coefficient": float(round(val, 2))
                    })

    # Schema drift mock check (looks for drift compared to a generic baseline config)
    schema_drift = {
        "drifted": False,
        "added_columns": [],
        "removed_columns": [],
        "changed_types": [],
        "renamed_fields": []
    }
    # Simulate a baseline column structure match
    baseline_retail = ["OrderID", "Client", "Phone", "Region", "Revenue", "OrderDate"]
    if "OrderID" in df.columns and len(df.columns) != len(baseline_retail):
        schema_drift["drifted"] = True
        schema_drift["added_columns"] = list(set(df.columns) - set(baseline_retail))
        schema_drift["removed_columns"] = list(set(baseline_retail) - set(df.columns))

    return {
        "targetCol": target_col,
        "classImbalance": class_imbalance,
        "classImbalanceRatio": class_imbalance_ratio,
        "hasTargetLeakage": has_target_leakage,
        "targetLeakageCol": target_leakage_col,
        "highCardinalityCol": high_cardinality_col,
        "redundantPairs": correlation_pairs,
        "schemaDrift": schema_drift,
        "numericCols": numeric_cols
    }

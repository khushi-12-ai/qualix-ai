import pandas as pd
import numpy as np
from typing import Dict, List, Any

def run_statistical_outlier_detection(df: pd.DataFrame, numeric_cols: List[str]) -> Dict[str, Any]:
    """
    Computes statistical anomalies in numeric columns using IQR (Interquartile Range).
    Labelled clearly as 'Statistical Anomaly Detection' to maintain technical realism.
    """
    anomalies = {}
    total_outliers = 0
    
    for col in numeric_cols:
        series = pd.to_numeric(
            df[col].astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False).str.strip(),
            errors='coerce'
        ).dropna()
        
        if len(series) >= 4:
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            outliers = series[(series < lower_bound) | (series > upper_bound)]
            anomalies[col] = {
                "outliers_count": len(outliers),
                "lower_bound": float(lower_bound),
                "upper_bound": float(upper_bound),
                "outliers_indices": list(outliers.index)
            }
            total_outliers += len(outliers)
        else:
            anomalies[col] = {
                "outliers_count": 0,
                "lower_bound": 0.0,
                "upper_bound": 0.0,
                "outliers_indices": []
            }
            
    return {
        "engine": "Statistical Anomaly Detection (IQR Method)",
        "total_anomalies": total_outliers,
        "col_details": anomalies
    }

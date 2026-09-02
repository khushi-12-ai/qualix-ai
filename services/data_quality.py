import pandas as pd
from typing import Dict, Any, List

def calculate_data_quality_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes data quality dimension sub-scores:
    - Completeness
    - Consistency
    - Validity
    - Duplicates
    - Structure
    - Anomalies
    """
    if df.empty:
        return {
            "completeness": 100,
            "consistency": 100,
            "validity": 100,
            "duplicates": 100,
            "structure": 100,
            "anomalies": 100,
            "issues": []
        }
        
    num_rows, num_cols = df.shape
    total_cells = num_rows * num_cols
    columns = list(df.columns)
    
    null_reps = ['nan', '', 'none', 'n/a', '-', 'null', 'unknown']
    issues = []
    
    # 1. Completeness Score
    empty_cells_per_col = {}
    total_empty_cells = 0
    for col in columns:
        is_empty = df[col].astype(str).str.strip().str.lower().isin(null_reps) | df[col].isna()
        empty_count = int(is_empty.sum())
        empty_cells_per_col[col] = empty_count
        total_empty_cells += empty_count
        
        if empty_count > 0:
            pct = int(round((empty_count / num_rows) * 100))
            issues.append({
                "id": f"missing_{col}",
                "column": col,
                "severity": "Critical" if pct > 20 else "High",
                "type": "Completeness",
                "title": f"Missing values in column \"{col}\"",
                "description": f"{empty_count} cells ({pct}%) are empty or null.",
                "impact": "Downstream pipelines and model learning cannot impute value parameters.",
                "action": "Impute missing elements using category mode or median numbers."
            })
            
    completeness_score = int(round(((total_cells - total_empty_cells) / total_cells) * 100))

    # Tiered Business-Aware Completeness
    critical_cols = []
    standard_cols = []
    optional_cols = []
    
    for col in columns:
        col_lower = col.lower()
        if any(k in col_lower for k in ['revenue', 'sales', 'invoice', 'gstin', 'amount', 'id', 'cust']):
            critical_cols.append(col)
        elif any(k in col_lower for k in ['phone', 'email', 'name', 'date', 'contact', 'mobile']):
            standard_cols.append(col)
        else:
            optional_cols.append(col)
            
    def get_completeness_for_cols(cols_list):
        if not cols_list or num_rows == 0:
            return 100
        tot_cells = len(cols_list) * num_rows
        empty_count = sum(empty_cells_per_col[c] for c in cols_list)
        return int(round(((tot_cells - empty_count) / tot_cells) * 100))
        
    critical_comp = get_completeness_for_cols(critical_cols)
    standard_comp = get_completeness_for_cols(standard_cols)
    optional_comp = get_completeness_for_cols(optional_cols)

    # 2. Consistency Score (casing check)
    inconsistency_count = 0
    for col in columns:
        series_str = df[col].astype(str).str.strip()
        non_empty = series_str[~series_str.str.lower().isin(null_reps)]
        if len(non_empty) > 0:
            grouped = non_empty.groupby(non_empty.str.lower())
            vars_list = []
            for _, group in grouped:
                unique_vars = group.unique()
                if len(unique_vars) > 1:
                    inconsistency_count += (len(unique_vars) - 1)
                    vars_list.append(list(unique_vars))
            if vars_list:
                issues.append({
                    "id": f"consistent_{col}",
                    "column": col,
                    "severity": "Medium",
                    "type": "Consistency",
                    "title": f"Capitalization inconsistency in \"{col}\"",
                    "description": f"Different spelling/casing variations detected (e.g. {', '.join(vars_list[0])}).",
                    "impact": "Group-by aggregations and categorical encoding steps treat these as unique labels.",
                    "action": "Normalize spelling text to Title Case."
                })
                
    consistency_score = int(max(20, min(100, round(100 - (inconsistency_count / num_rows) * 100))))

    # 3. Validity Score (e.g. negative numbers in expected positive ranges, phone structure matching)
    invalid_count = 0
    for col in columns:
        if any(k in col.lower() for k in ['revenue', 'cost', 'stock', 'quantity', 'charges', 'salary', 'rate', 'balance', 'gpa', 'price', 'valuation', 'palletcount']):
            numeric_vals = pd.to_numeric(df[col].astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False).str.strip(), errors='coerce')
            negs = numeric_vals[numeric_vals < 0]
            if not negs.empty:
                invalid_count += len(negs)
                issues.append({
                    "id": f"invalid_neg_{col}",
                    "column": col,
                    "severity": "Critical",
                    "type": "Validity",
                    "title": f"Negative metrics in positive field \"{col}\"",
                    "description": f"Found {len(negs)} negative records (e.g., negative revenues or warehouse count).",
                    "impact": "Distorts analytical totals and causes invalid schema validation assertions.",
                    "action": "Set negative outliers to zero or replace with absolute values."
                })
                
    validity_score = int(max(30, min(100, round(100 - (invalid_count / num_rows) * 100))))

    # 4. Duplicate Score
    exact_duplicates = int(df.duplicated().sum())
    if exact_duplicates > 0:
        issues.append({
            "id": "duplicate_rows",
            "column": "All Columns",
            "severity": "High",
            "type": "Duplicates",
            "title": "Exact duplicate rows",
            "description": f"Found {exact_duplicates} duplicate records in dataset.",
            "impact": "Overstates transaction parameters and skews model class balances.",
            "action": "Apply deduplication and keep unique items."
        })
    duplicate_score = int(round(((num_rows - exact_duplicates) / num_rows) * 100))

    # 5. Structure Score (mixed type detection)
    structural_issues = 0
    for col in columns:
        types = {'num': 0, 'text': 0, 'date': 0}
        series = df[col].dropna()
        for val in series:
            val_str = str(val).strip()
            if val_str.lower() in null_reps:
                continue
            cleaned = val_str.replace('$', '').replace(',', '').strip()
            try:
                float(cleaned)
                types['num'] += 1
            except ValueError:
                try:
                    pd.to_datetime(val_str, errors='raise')
                    if '-' in val_str or '/' in val_str:
                        types['date'] += 1
                    else:
                        types['text'] += 1
                except Exception:
                    types['text'] += 1
                    
        total_typed = sum(types.values())
        if total_typed > 0:
            dominant = max(types.values())
            ratio = dominant / total_typed
            if ratio < 0.95 and ratio > 0.05:
                structural_issues += 1
                issues.append({
                    "id": f"structure_{col}",
                    "column": col,
                    "severity": "Medium",
                    "type": "Structure",
                    "title": f"Mixed data types in \"{col}\"",
                    "description": f"Column contains mixed string and numeric inputs (e.g. numeric metrics containing string format units).",
                    "impact": "Fails standard schema validation assertions and causes calculations to crash.",
                    "action": "Clean column characters and convert to uniform data type."
                })
                
    structure_score = int(max(30, round(100 - (structural_issues / num_cols) * 50)))

    # 6. Anomaly Score
    anomaly_count = 0
    for col in columns:
        series_num = pd.to_numeric(
            df[col].astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False).str.strip(),
            errors='coerce'
        ).dropna()
        if len(series_num) >= 4:
            q1 = series_num.quantile(0.25)
            q3 = series_num.quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            outliers = series_num[(series_num < lower_bound) | (series_num > upper_bound)]
            anomaly_count += len(outliers)
            
            if len(outliers) > 0 and col.lower() in ['revenue', 'palletcount', 'monthlycharges']:
                issues.append({
                    "id": f"outlier_{col}",
                    "column": col,
                    "severity": "High",
                    "type": "Anomaly",
                    "title": f"Extreme numeric outliers in \"{col}\"",
                    "description": f"Detected {len(outliers)} statistical outlier elements.",
                    "impact": "Skews mean and variance parameters, confusing downstream prediction regressions.",
                    "action": "Cap outliers at IQR threshold boundaries or remove extreme rows."
                })
                
    anomaly_score = int(max(40, round(100 - (anomaly_count / num_rows) * 80)))

    # Overall Score
    overall_quality_score = int(round(
        completeness_score * 0.20 +
        consistency_score * 0.20 +
        validity_score * 0.20 +
        duplicate_score * 0.15 +
        structure_score * 0.15 +
        anomaly_score * 0.10
    ))
    
    return {
        "completeness": completeness_score,
        "critical_completeness": critical_comp,
        "standard_completeness": standard_comp,
        "optional_completeness": optional_comp,
        "consistency": consistency_score,
        "validity": validity_score,
        "duplicates": duplicate_score,
        "structure": structure_score,
        "anomalies": anomaly_score,
        "overallQuality": overall_quality_score,
        "issues": issues
    }

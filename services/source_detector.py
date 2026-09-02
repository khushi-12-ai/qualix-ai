import os
from typing import List, Dict, Any

def detect_source_type(filename: str, columns: List[str]) -> Dict[str, Any]:
    """
    Analyzes file names and column schemas to recommend a source type:
    - Spreadsheet
    - POS Export
    - Tally
    - CRM
    Returns detected source, confidence (0-100), and match reason.
    """
    fn = filename.lower()
    cols = [c.lower() for c in columns]
    
    # 1. Look for keyword matches in filename
    file_signals = {
        "CRM": ["crm", "customer", "contact", "lead", "opp"],
        "Tally": ["tally", "ledger", "purchase", "vendor", "accounting"],
        "POS Export": ["pos", "pointofsale", "receipt", "bill", "invoice_export"],
        "Spreadsheet": ["spreadsheet", "excel", "sales", "inventory", "stock", "manually"]
    }
    
    # 2. Look for keyword matches in column headers
    col_signals = {
        "CRM": ["customer_id", "email", "last_login", "cancellationdate", "churn", "opportunity"],
        "Tally": ["party_name", "gstin", "sales", "ledger", "mobile", "party_id"],
        "POS Export": ["pos_id", "bill_amount", "invoice_date", "contact", "customer", "pos"],
        "Spreadsheet": ["orderid", "client", "phone", "region", "revenue", "orderdate", "internal_notes", "created_by"]
    }
    
    source_scores = {k: 0.0 for k in file_signals.keys()}
    
    # Filename match gives a heavy weight
    for source, keywords in file_signals.items():
        for kw in keywords:
            if kw in fn:
                source_scores[source] += 50.0
                break
                
    # Column match adds to score
    for source, keywords in col_signals.items():
        matched_cols = 0
        for kw in keywords:
            if any(kw in c for c in cols):
                matched_cols += 1
        if len(cols) > 0:
            source_scores[source] += (matched_cols / len(cols)) * 100.0
            
    # Boost if both file name and column signal matches
    for source in source_scores:
        if any(kw in fn for kw in file_signals[source]) and any(any(kw in c for c in cols) for kw in col_signals[source]):
            source_scores[source] += 15.0

    # Determine best match
    best_source = "Spreadsheet"
    best_score = 40.0 # baseline default
    reason = "Fallback default spreadsheet"
    
    sorted_sources = sorted(source_scores.items(), key=lambda x: x[1], reverse=True)
    if sorted_sources[0][1] > 0:
        best_source, score_val = sorted_sources[0]
        # Normalize score to max 100, min 50 for any matched
        best_score = min(99.0, max(50.0, score_val))
        reason = f"Detected via filename keywords and schema column signature matches."
        
    return {
        "detected_source": best_source,
        "confidence": int(round(best_score)),
        "reason": reason
    }

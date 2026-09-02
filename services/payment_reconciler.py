import re
import pandas as pd
from typing import Dict, Any, List
from rapidfuzz import fuzz

def _clean_float(val: Any, default: float = 0.0) -> float:
    if val is None or pd.isna(val):
        return default
    if isinstance(val, (int, float)):
        return float(val) if not (pd.isna(val) or val != val) else default
    try:
        cleaned = re.sub(r'[^\d.-]', '', str(val)).strip()
        if not cleaned or cleaned == '-' or cleaned == '.':
            return default
        return float(cleaned)
    except Exception:
        return default

def _find_column(cols: List[str], candidate_keywords: List[str], fallback_idx: int = 0) -> str:
    cols_map = {c.lower().strip().replace(" ", "_"): c for c in cols}
    for kw in candidate_keywords:
        kw_clean = kw.lower().strip().replace(" ", "_")
        for c_lower, orig in cols_map.items():
            if kw_clean == c_lower or kw_clean in c_lower:
                return orig
    if cols:
        return cols[min(fallback_idx, len(cols) - 1)]
    return ""

def reconcile_payments(invoices: pd.DataFrame, payments: pd.DataFrame) -> Dict[str, Any]:
    """
    Reconciles invoice records with payment records.
    Supports matching by Invoice Reference, Fuzzy Customer Name, and Amount discrepancy analysis.
    Classifications: Matched, Partial, Unmatched, Duplicate, Conflict.
    """
    if invoices is None or invoices.empty or payments is None or payments.empty:
        return {
            "stats": {
                "matched_pct": 0.0,
                "partial_pct": 0.0,
                "unmatched_pct": 100.0 if (invoices is not None and not invoices.empty) or (payments is not None and not payments.empty) else 0.0,
                "duplicate_pct": 0.0,
                "conflict_pct": 0.0,
                "counts": {
                    "matched": 0,
                    "partial": 0,
                    "unmatched": len(invoices) if invoices is not None else 0 + (len(payments) if payments is not None else 0),
                    "duplicate": 0,
                    "conflict": 0
                }
            },
            "details": []
        }

    matched_count = 0
    partial_count = 0
    duplicate_count = 0
    conflict_count = 0
    unmatched_invoices_count = 0
    unmatched_payments_count = 0
    
    reconciliation_details = []
    
    # Robust column discovery
    inv_cols = list(invoices.columns)
    pay_cols = list(payments.columns)
    
    inv_no_col = _find_column(inv_cols, ["invoice_no", "invoice_num", "invoice", "inv_no", "orderid", "order_id", "bill_no", "id", "ref"], 0)
    inv_cust_col = _find_column(inv_cols, ["customer_name", "customer", "client", "client_name", "party_name", "party", "name", "account"], 1)
    inv_amt_col = _find_column(inv_cols, ["amount", "invoice_amount", "paid_amount", "revenue", "total", "net_amount", "grand_total", "price", "val"], 2)
    
    pay_ref_col = _find_column(pay_cols, ["payment_ref", "invoice_ref", "invoice_no", "invoice", "inv_no", "ref", "order_id", "orderid", "id"], 0)
    pay_cust_col = _find_column(pay_cols, ["customer_name", "customer", "client", "client_name", "party_name", "party", "name", "account"], 1)
    pay_amt_col = _find_column(pay_cols, ["paid_amount", "amount", "payment_amount", "revenue", "total", "net_amount", "val"], 2)
    
    matched_payment_indices = set()
    
    for idx, inv in invoices.iterrows():
        inv_no = str(inv.get(inv_no_col, "")).strip()
        inv_cust = str(inv.get(inv_cust_col, "")).strip()
        inv_amt = _clean_float(inv.get(inv_amt_col, 0.0))
        
        # Look for payments matching invoice number
        candidate_payments = []
        for p_idx, pay in payments.iterrows():
            if p_idx in matched_payment_indices:
                continue
            pay_ref = str(pay.get(pay_ref_col, "")).strip()
            
            # Match directly on invoice reference (stripping dashes)
            inv_no_clean = inv_no.replace("-", "").replace(" ", "").lower()
            pay_ref_clean = pay_ref.replace("-", "").replace(" ", "").lower()
            
            if inv_no_clean and pay_ref_clean:
                if inv_no_clean == pay_ref_clean or (len(inv_no_clean) > 3 and inv_no_clean in pay_ref_clean) or (len(pay_ref_clean) > 3 and pay_ref_clean in inv_no_clean):
                    candidate_payments.append((p_idx, pay))
                
        # If no reference match, try fuzzy customer + amount match (missing ref)
        if not candidate_payments:
            for p_idx, pay in payments.iterrows():
                if p_idx in matched_payment_indices:
                    continue
                pay_cust = str(pay.get(pay_cust_col, "")).strip()
                pay_amt = _clean_float(pay.get(pay_amt_col, 0.0))
                
                # Check fuzzy name similarity
                name_sim = fuzz.token_sort_ratio(inv_cust.lower(), pay_cust.lower()) if (inv_cust and pay_cust) else 0
                amt_diff = abs(inv_amt - pay_amt)
                
                if name_sim >= 80 and (amt_diff <= 10 or (inv_amt > 0 and amt_diff / inv_amt <= 0.05)):
                    candidate_payments.append((p_idx, pay))
                    break # matched
                    
        if not candidate_payments:
            unmatched_invoices_count += 1
            reconciliation_details.append({
                "invoice_no": inv_no or f"INV-{idx}",
                "customer": inv_cust or "Unknown Customer",
                "invoice_amount": round(inv_amt, 2),
                "paid_amount": 0.0,
                "status": "Unmatched",
                "details": "No matching payment record found."
            })
        elif len(candidate_payments) > 1:
            duplicate_count += 1
            # Mark all candidates as matched/processed
            total_paid = 0.0
            for p_idx, pay in candidate_payments:
                matched_payment_indices.add(p_idx)
                total_paid += _clean_float(pay.get(pay_amt_col, 0.0))
                
            reconciliation_details.append({
                "invoice_no": inv_no or f"INV-{idx}",
                "customer": inv_cust or "Unknown Customer",
                "invoice_amount": round(inv_amt, 2),
                "paid_amount": round(total_paid, 2),
                "status": "Duplicate",
                "details": f"Multiple payments found referencing this invoice: {len(candidate_payments)} records."
            })
        else:
            p_idx, pay = candidate_payments[0]
            matched_payment_indices.add(p_idx)
            pay_cust = str(pay.get(pay_cust_col, "")).strip()
            pay_amt = _clean_float(pay.get(pay_amt_col, 0.0))
            
            # Check for conflict or partial or exact match
            name_sim = fuzz.token_sort_ratio(inv_cust.lower(), pay_cust.lower()) if (inv_cust and pay_cust) else 100
            
            if name_sim < 60 and inv_cust and pay_cust:
                conflict_count += 1
                reconciliation_details.append({
                    "invoice_no": inv_no or f"INV-{idx}",
                    "customer": inv_cust or "Unknown Customer",
                    "invoice_amount": round(inv_amt, 2),
                    "paid_amount": round(pay_amt, 2),
                    "status": "Conflict",
                    "details": f"Name mismatch: Invoice customer '{inv_cust}' vs Payment customer '{pay_cust}'."
                })
            elif abs(inv_amt - pay_amt) > 10:
                # Partial payment or overpayment
                partial_count += 1
                diff = abs(inv_amt - pay_amt)
                reconciliation_details.append({
                    "invoice_no": inv_no or f"INV-{idx}",
                    "customer": inv_cust or "Unknown Customer",
                    "invoice_amount": round(inv_amt, 2),
                    "paid_amount": round(pay_amt, 2),
                    "status": "Partial",
                    "details": f"Discrepancy: ₹{diff:,.2f} difference (Invoice: ₹{inv_amt:,.2f}, Paid: ₹{pay_amt:,.2f})."
                })
            else:
                matched_count += 1
                reconciliation_details.append({
                    "invoice_no": inv_no or f"INV-{idx}",
                    "customer": inv_cust or "Unknown Customer",
                    "invoice_amount": round(inv_amt, 2),
                    "paid_amount": round(pay_amt, 2),
                    "status": "Matched",
                    "details": "Payment matches invoice reference and amount."
                })
                
    unmatched_payments_count = len(payments) - len(matched_payment_indices)
    
    # Append unmatched payments to details
    for p_idx, pay in payments.iterrows():
        if p_idx not in matched_payment_indices:
            pay_amt = _clean_float(pay.get(pay_amt_col, 0.0))
            reconciliation_details.append({
                "invoice_no": str(pay.get(pay_ref_col, f"PAY-{p_idx}")),
                "customer": str(pay.get(pay_cust_col, "Unknown")),
                "invoice_amount": 0.0,
                "paid_amount": round(pay_amt, 2),
                "status": "Unmatched Payment",
                "details": "Payment received without corresponding invoice record."
            })
            
    total_records = len(reconciliation_details)
    stats = {
        "matched_pct": round(matched_count / total_records * 100, 1) if total_records else 0.0,
        "partial_pct": round(partial_count / total_records * 100, 1) if total_records else 0.0,
        "unmatched_pct": round((unmatched_invoices_count + unmatched_payments_count) / total_records * 100, 1) if total_records else 0.0,
        "duplicate_pct": round(duplicate_count / total_records * 100, 1) if total_records else 0.0,
        "conflict_pct": round(conflict_count / total_records * 100, 1) if total_records else 0.0,
        "counts": {
            "matched": matched_count,
            "partial": partial_count,
            "unmatched": unmatched_invoices_count + unmatched_payments_count,
            "duplicate": duplicate_count,
            "conflict": conflict_count
        }
    }
    
    return {
        "stats": stats,
        "details": reconciliation_details
    }

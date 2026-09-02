import json
import pandas as pd
from typing import Dict, Any, List
from services.entity_resolver import resolve_entities
from services.conflict_detector import detect_conflicts
from rapidfuzz import fuzz

def recommend_merge_strategy(dfs: Dict[str, pd.DataFrame], schema_mapping: List[Dict[str, Any]]) -> Dict[str, str]:
    """Recommends the safest entity matching key and merge strategy based on columns available."""
    # Check for GSTIN
    gstin_sources = []
    id_sources = []
    
    for mapping in schema_mapping:
        tf = mapping["target_field"]
        if tf == "GSTIN":
            gstin_sources = list(mapping["columns"].keys())
        elif tf == "Customer_ID":
            id_sources = list(mapping["columns"].keys())
            
    if len(gstin_sources) >= 2:
        return {
            "key": "GSTIN",
            "strategy": "Entity Resolution",
            "reason": "GSTIN is available in Tally and CRM and provides a stronger, government-verified entity identifier than Customer Name."
        }
    elif len(id_sources) >= 2:
        return {
            "key": "Customer_ID",
            "strategy": "Entity Resolution",
            "reason": "Customer ID is available across sources and provides a unique numeric key."
        }
    else:
        return {
            "key": "Customer_Name",
            "strategy": "Entity Resolution",
            "reason": "Fuzzy Customer Name matching is recommended because structured identifiers (GSTIN/ID) are missing or incomplete."
        }

def preview_merge(
    dfs: Dict[str, pd.DataFrame],
    schema_mapping: List[Dict[str, Any]],
    strategy: str,
    matching_key: str,
    conflict_resolutions: Dict[str, Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Computes preview statistics and Plotly chart data before applying the merge.
    """
    if conflict_resolutions is None:
        conflict_resolutions = {}
        
    resolver_res = resolve_entities(dfs, schema_mapping, matching_key)
    entity_groups = resolver_res["entity_groups"]
    records = resolver_res["records"]
    
    # 1. Row counts
    total_input_rows = len(records)
    unique_entities = len(entity_groups)
    
    # Matched vs unmatched counts
    matched_records = sum(len(g) for g in entity_groups if len(g) > 1)
    unmatched_records = sum(1 for g in entity_groups if len(g) == 1)
    duplicates_resolved = total_input_rows - unique_entities
    
    # 2. Count actual conflicts
    all_conflicts = detect_conflicts(dfs, schema_mapping, matching_key)
    conflicts_count = len(all_conflicts)
    
    # Source Contribution breakdown
    source_counts = {sid: 0 for sid in dfs.keys()}
    for r in records:
        source_counts[r["source_id"]] += 1
        
    # Standard columns added + 6 provenance columns
    new_columns = 10 + 6
    
    return {
        "unique_entities": unique_entities,
        "matched_records": matched_records,
        "unmatched_records": unmatched_records,
        "duplicates_resolved": duplicates_resolved,
        "conflicts_detected": conflicts_count,
        "new_columns": new_columns,
        "source_contributions": source_counts
    }

def apply_merge(
    dfs: Dict[str, pd.DataFrame],
    schema_mapping: List[Dict[str, Any]],
    strategy: str,
    matching_key: str,
    conflict_resolutions: Dict[str, Dict[str, str]] = None
) -> pd.DataFrame:
    """
    Performs the final merge of all sources.
    Resolves duplicates, handles conflicts using user choices,
    and appends explicit row-level provenance columns.
    """
    if conflict_resolutions is None:
        conflict_resolutions = {}
        
    resolver_res = resolve_entities(dfs, schema_mapping, matching_key)
    entity_groups = resolver_res["entity_groups"]
    records = resolver_res["records"]
    
    # Mappings
    column_maps = {} # target_field -> { source_id -> source_col }
    target_fields = [
        "Customer_ID", "Customer_Name", "Phone", "Email", "GSTIN",
        "Revenue", "Invoice_Date", "Internal_Notes", "Created_By", "Last_Login"
    ]
    for mapping in schema_mapping:
        column_maps[mapping["target_field"]] = mapping["columns"]
        
    merged_rows = []
    
    # Sort out first source ID for Left Join
    first_source_id = list(dfs.keys())[0] if dfs else None
    
    for group_idx, group in enumerate(entity_groups):
        # 1. Handle Join Strategies
        group_source_ids = set(records[m]["source_id"] for m in group)
        
        if strategy == "Left Join" and first_source_id not in group_source_ids:
            continue
        elif strategy == "Inner Join" and len(group_source_ids) < len(dfs):
            continue
            
        lead_record = records[group[0]]
        entity_name = lead_record["name"]
        
        # 2. Build the unified row
        row_data = {}
        
        for target in target_fields:
            col_map = column_maps.get(target, {})
            
            # Check for conflict resolution override
            res_key = f"{entity_name}_{target}"
            if conflict_resolutions and res_key in conflict_resolutions:
                row_data[target] = conflict_resolutions[res_key]
                continue
                
            # Otherwise, pick first non-empty value
            val = ""
            for m in group:
                r = records[m]
                sid = r["source_id"]
                col_name = col_map.get(sid)
                if col_name and col_name in r["original_data"]:
                    curr_val = str(r["original_data"][col_name]).strip()
                    if curr_val and curr_val.lower() not in ['nan', 'none', 'n/a', '-', '', 'null']:
                        val = curr_val
                        break
            row_data[target] = val
            
        # 3. Populate Provenance Columns
        # Source type flags based on source IDs/types
        crm_flag = 1 if any("crm" in records[m]["source_id"].lower() or "crm" in str(records[m].get("source_id")).lower() for m in group) else 0
        tally_flag = 1 if any("tally" in records[m]["source_id"].lower() or "tally" in str(records[m].get("source_id")).lower() for m in group) else 0
        pos_flag = 1 if any("pos" in records[m]["source_id"].lower() or "pos" in str(records[m].get("source_id")).lower() for m in group) else 0
        excel_flag = 1 if any("spreadsheet" in records[m]["source_id"].lower() or "sales" in records[m]["source_id"].lower() or "inventory" in records[m]["source_id"].lower() or "excel" in records[m]["source_id"].lower() for m in group) else 0
        
        # Calculate entity similarity confidence
        max_sim = 100
        if len(group) > 1:
            max_sim = 0
            for m in group[1:]:
                max_sim = max(max_sim, float(fuzz.token_sort_ratio(lead_record["name"], records[m]["name"])))
            if max_sim == 0:
                max_sim = 90 # fallback
                
        row_data["_source_crm"] = crm_flag
        row_data["_source_tally"] = tally_flag
        row_data["_source_pos"] = pos_flag
        row_data["_source_excel"] = excel_flag
        row_data["_merge_confidence"] = int(round(max_sim))
        row_data["_entity_match_id"] = entity_name
        
        # Add metadata for provenance data lineage
        provenance_metadata = []
        for m in group:
            r = records[m]
            provenance_metadata.append({
                "source": r["source_id"],
                "row_idx": r["row_idx"],
                "original_name": r["name"]
            })
        row_data["_provenance_log"] = json.dumps(provenance_metadata)
        
        merged_rows.append(row_data)
        
    return pd.DataFrame(merged_rows)

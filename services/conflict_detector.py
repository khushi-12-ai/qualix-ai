import pandas as pd
from typing import Dict, Any, List
from services.entity_resolver import resolve_entities

def detect_conflicts(dfs: Dict[str, pd.DataFrame], schema_mapping: List[Dict[str, Any]], matching_key: str) -> List[Dict[str, Any]]:
    """
    Identifies conflicts where multiple sources have different non-empty values
    for the same field on the same resolved entity.
    """
    # 1. Resolve entities first to get groups
    resolver_res = resolve_entities(dfs, schema_mapping, matching_key)
    entity_groups = resolver_res["entity_groups"]
    records = resolver_res["records"]
    
    # 2. Extract mappings for columns
    column_maps = {} # target_field -> { source_id -> source_col }
    for mapping in schema_mapping:
        column_maps[mapping["target_field"]] = mapping["columns"]
        
    conflicts = []
    
    for group in entity_groups:
        if len(group) < 2:
            continue
            
        lead_record = records[group[0]]
        entity_name = lead_record["name"]
        
        # Check all target fields for conflicts in this group
        for target_field, source_col_map in column_maps.items():
            if target_field == matching_key:
                continue
                
            # Collect values across sources in this entity group
            field_values = {} # source_id -> value
            for m in group:
                r = records[m]
                sid = r["source_id"]
                col_name = source_col_map.get(sid)
                if col_name and col_name in r["original_data"]:
                    val = str(r["original_data"][col_name]).strip()
                    # Skip empty representations
                    if val and val.lower() not in ['nan', 'none', 'n/a', '-', '', 'null']:
                        field_values[sid] = val
                        
            # If we have at least 2 sources and they differ, we have a conflict
            unique_vals = set(field_values.values())
            if len(unique_vals) > 1:
                conflicts.append({
                    "entity_id": entity_name,
                    "field": target_field,
                    "values": field_values,
                    "status": "CONFLICT"
                })
                
    return conflicts

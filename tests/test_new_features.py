import os
import sys
import unittest
import pandas as pd

# Ensure services directory is in search path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import (
    source_detector,
    schema_matcher,
    entity_resolver,
    conflict_detector,
    merge_engine,
    field_classifier,
    scan_scope
)

class TestNewFeatures(unittest.TestCase):
    
    def test_source_detection(self):
        cols = ["GSTIN", "customer", "invoice_no", "total_amt"]
        res = source_detector.detect_source_type("tally_export_2026.xlsx", cols)
        self.assertEqual(res["detected_source"], "Tally")
        self.assertGreaterEqual(res["confidence"], 80)
        
    def test_schema_matching(self):
        dfs = {
            "src1": pd.DataFrame(columns=["customer_name", "phone_num", "revenue"]),
            "src2": pd.DataFrame(columns=["cust_name", "tel", "sales"])
        }
        mappings = schema_matcher.suggest_column_mapping(dfs)
        cust_mapping = next(m for m in mappings if m["target_field"] == "Customer_Name")
        self.assertEqual(cust_mapping["columns"]["src1"], "customer_name")
        self.assertEqual(cust_mapping["columns"]["src2"], "cust_name")
        self.assertEqual(cust_mapping["confidence_level"], "HIGH")
        
    def test_entity_resolution_and_conflicts(self):
        df_crm = pd.DataFrame([
            {"crm_cust": "Rahul Patel", "crm_phone": "9876543210", "crm_rev": 1000},
            {"crm_cust": "Alice Green", "crm_phone": "8888888888", "crm_rev": 2000}
        ])
        df_tally = pd.DataFrame([
            {"tally_cust": "Rahul K Patel", "tally_phone": "9876543210", "tally_sales": 1100},
            {"tally_cust": "Bob Brown", "tally_phone": "7777777777", "tally_sales": 1500}
        ])
        
        dfs = {"crm": df_crm, "tally": df_tally}
        schema_mapping = [
            {"target_field": "Customer_Name", "columns": {"crm": "crm_cust", "tally": "tally_cust"}},
            {"target_field": "Phone", "columns": {"crm": "crm_phone", "tally": "tally_phone"}},
            {"target_field": "Revenue", "columns": {"crm": "crm_rev", "tally": "tally_sales"}}
        ]
        
        match_res = entity_resolver.resolve_entities(dfs, schema_mapping, "Customer_Name")
        self.assertEqual(len(match_res["duplicates"]), 1)
        self.assertEqual(match_res["duplicates"][0]["primary"], "Rahul Patel")
        
        conflicts = conflict_detector.detect_conflicts(dfs, schema_mapping, "Customer_Name")
        rev_conflicts = [c for c in conflicts if c["field"] == "Revenue"]
        self.assertEqual(len(rev_conflicts), 1)
        self.assertEqual(rev_conflicts[0]["entity_id"], "Rahul Patel")
        
    def test_merge_engine_apply(self):
        df_crm = pd.DataFrame([
            {"crm_cust": "Rahul Patel", "crm_phone": "9876543210", "crm_rev": 1000}
        ])
        df_tally = pd.DataFrame([
            {"tally_cust": "Rahul K Patel", "tally_phone": "9876543210", "tally_sales": 1100}
        ])
        
        dfs = {"crm": df_crm, "tally": df_tally}
        schema_mapping = [
            {"target_field": "Customer_Name", "columns": {"crm": "crm_cust", "tally": "tally_cust"}},
            {"target_field": "Phone", "columns": {"crm": "crm_phone", "tally": "tally_phone"}},
            {"target_field": "Revenue", "columns": {"crm": "crm_rev", "tally": "tally_sales"}}
        ]
        
        conflict_resolutions = {"Rahul Patel_Revenue": "1100"}
        
        df_merged = merge_engine.apply_merge(dfs, schema_mapping, "Entity Resolution", "Customer_Name", conflict_resolutions)
        self.assertEqual(len(df_merged), 1)
        self.assertEqual(df_merged.iloc[0]["Customer_Name"], "Rahul Patel")
        self.assertEqual(float(df_merged.iloc[0]["Revenue"]), 1100.0)
        self.assertIn("_entity_match_id", df_merged.columns)
        self.assertIn("_merge_confidence", df_merged.columns)
        self.assertIn("_source_crm", df_merged.columns)
        self.assertIn("_source_tally", df_merged.columns)
        
    def test_field_classifier_and_scan_scope(self):
        df = pd.DataFrame([
            {"Customer_Name": "Rahul Patel", "Revenue": 1000, "Date": "2026-08-23", "System_Id": "SYS001"}
        ])
        classifications = field_classifier.classify_fields(df)
        self.assertEqual(classifications["Customer_Name"], "Identifier")
        self.assertEqual(classifications["Revenue"], "Target")
        self.assertEqual(classifications["System_Id"], "System Field")
        
        recs = scan_scope.recommend_scan_scope(df, classifications)
        self.assertEqual(recs["Revenue"]["recommendation"], "Include")
        self.assertEqual(recs["System_Id"]["recommendation"], "Exclude")
        
        val_res = scan_scope.validate_scope(df, ["Customer_Name", "System_Id"])
        self.assertFalse(val_res["valid"])
        self.assertIn("Revenue", val_res["warnings"])

if __name__ == "__main__":
    unittest.main()

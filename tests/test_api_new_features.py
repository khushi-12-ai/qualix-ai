import os
import sys
import unittest
import pandas as pd
from fastapi.testclient import TestClient

# Ensure services directory is in search path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app, ACTIVE_DATASETS, UPLOADED_SOURCES

class TestAPINewFeatures(unittest.TestCase):
    
    def setUp(self):
        self.client = TestClient(app)
        ACTIVE_DATASETS.clear()
        UPLOADED_SOURCES.clear()
        
    def test_merge_upload_permissions(self):
        # Viewer should be blocked from uploading
        r_viewer = self.client.post(
            "/api/merge/upload",
            files=[("files", ("test.csv", b"a,b\n1,2\n", "text/csv"))],
            data={"role": "VIEWER", "username": "viewer@qualix.ai"}
        )
        self.assertEqual(r_viewer.status_code, 403)
        
    def test_merge_workflow_endpoints(self):
        # 1. Ingest/Upload files as Analyst
        crm_data = b"crm_cust,crm_phone,crm_rev\nRahul Patel,9876543210,1000\n"
        tally_data = b"tally_cust,tally_phone,tally_sales\nRahul K Patel,9876543210,1100\n"
        
        files = [
            ("files", ("CRM.csv", crm_data, "text/csv")),
            ("files", ("Tally.csv", tally_data, "text/csv"))
        ]
        
        r_upload = self.client.post(
            "/api/merge/upload",
            files=files,
            data={"role": "DATA ANALYST", "username": "analyst@qualix.ai"}
        )
        self.assertEqual(r_upload.status_code, 200)
        res = r_upload.json()
        self.assertEqual(res["status"], "success")
        self.assertEqual(len(res["files"]), 2)
        
        source_ids = [f["id"] for f in res["files"]]
        
        # 2. Match Schema
        r_match = self.client.post(
            "/api/merge/schema-match",
            json={"source_ids": source_ids, "role": "DATA ANALYST", "username": "analyst@qualix.ai"}
        )
        self.assertEqual(r_match.status_code, 200)
        mappings = r_match.json()["mappings"]
        self.assertTrue(len(mappings) > 0)
        
        # 3. Entity Match
        r_entity = self.client.post(
            "/api/merge/entity-match",
            json={
                "source_ids": source_ids,
                "schema_mapping": [
                    {"target_field": "Customer_Name", "columns": {source_ids[0]: "crm_cust", source_ids[1]: "tally_cust"}},
                    {"target_field": "Phone", "columns": {source_ids[0]: "crm_phone", source_ids[1]: "tally_phone"}},
                    {"target_field": "Revenue", "columns": {source_ids[0]: "crm_rev", source_ids[1]: "tally_sales"}}
                ],
                "matching_key": "Customer_Name",
                "role": "DATA ANALYST",
                "username": "analyst@qualix.ai"
            }
        )
        self.assertEqual(r_entity.status_code, 200)
        self.assertTrue(len(r_entity.json()["duplicates"]) > 0)
        
        # 4. Conflicts
        r_conf = self.client.post(
            "/api/merge/conflicts",
            json={
                "source_ids": source_ids,
                "schema_mapping": [
                    {"target_field": "Customer_Name", "columns": {source_ids[0]: "crm_cust", source_ids[1]: "tally_cust"}},
                    {"target_field": "Phone", "columns": {source_ids[0]: "crm_phone", source_ids[1]: "tally_phone"}},
                    {"target_field": "Revenue", "columns": {source_ids[0]: "crm_rev", source_ids[1]: "tally_sales"}}
                ],
                "matching_key": "Customer_Name",
                "role": "DATA ANALYST",
                "username": "analyst@qualix.ai"
            }
        )
        self.assertEqual(r_conf.status_code, 200)
        
        # 5. Apply Merge
        r_apply = self.client.post(
            "/api/merge/apply",
            json={
                "source_ids": source_ids,
                "schema_mapping": [
                    {"target_field": "Customer_Name", "columns": {source_ids[0]: "crm_cust", source_ids[1]: "tally_cust"}},
                    {"target_field": "Phone", "columns": {source_ids[0]: "crm_phone", source_ids[1]: "tally_phone"}},
                    {"target_field": "Revenue", "columns": {source_ids[0]: "crm_rev", source_ids[1]: "tally_sales"}}
                ],
                "matching_key": "Customer_Name",
                "merge_strategy": "Entity Resolution",
                "conflict_resolutions": {"Rahul Patel_Revenue": "1100"},
                "role": "DATA ANALYST",
                "username": "analyst@qualix.ai"
            }
        )
        self.assertEqual(r_apply.status_code, 200)
        dataset_id = r_apply.json()["dataset_id"]
        
        # 6. Scope recommend
        r_rec = self.client.post(
            "/api/scope/recommend",
            json={"dataset_id": dataset_id, "role": "DATA ANALYST", "username": "analyst@qualix.ai"}
        )
        self.assertEqual(r_rec.status_code, 200)
        
        # 7. Scope apply
        r_scope = self.client.post(
            "/api/scope/apply",
            json={
                "dataset_id": dataset_id,
                "selected_fields": ["Customer_Name", "Phone", "Revenue"],
                "classifications": {"Customer_Name": "Identifier", "Phone": "Identifier", "Revenue": "Target"},
                "role": "DATA ANALYST",
                "username": "analyst@qualix.ai"
            }
        )
        self.assertEqual(r_scope.status_code, 200)

    def test_system_integrations_and_webhooks(self):
        # 1. List integrations
        r_list = self.client.get("/api/integrations")
        self.assertEqual(r_list.status_code, 200)
        data = r_list.json()
        self.assertIn("connectors", data)
        self.assertIn("recent_payloads", data)
        self.assertTrue(len(data["connectors"]) > 0)
        self.assertTrue(len(data["recent_payloads"]) > 0)

        # 2. Trigger sync
        r_sync = self.client.post("/api/integrations/shopify_pos/sync")
        self.assertEqual(r_sync.status_code, 200)
        res_sync = r_sync.json()
        self.assertEqual(res_sync["status"], "SUCCESS")
        self.assertEqual(res_sync["connector_id"], "shopify_pos")

        # 3. Fire Webhook
        r_wh = self.client.post("/api/integrations/webhook/shopify_pos", json={"Transaction_ID": "POS-9999", "Amount": 100})
        self.assertEqual(r_wh.status_code, 200)
        res_wh = r_wh.json()
        self.assertEqual(res_wh["status"], "ACCEPTED")

        # 4. Check updated payload log
        r_list_updated = self.client.get("/api/integrations")
        self.assertEqual(r_list_updated.status_code, 200)
        updated_payloads = r_list_updated.json()["recent_payloads"]
        self.assertEqual(updated_payloads[0]["system_id"], "shopify_pos")

if __name__ == "__main__":
    unittest.main()

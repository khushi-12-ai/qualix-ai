import unittest
import pandas as pd
import json
from fastapi.testclient import TestClient
from backend.main import app, ACTIVE_DATASETS
from services import (
    payment_reconciler,
    inventory_reconciler,
    schema_drift,
    sensitive_scanner,
    rule_generator
)

class TestHackathonFeatures(unittest.TestCase):
    
    def setUp(self):
        self.client = TestClient(app)
        
    def test_payment_reconciliation(self):
        # Create mock invoices & payments dataframes
        invoices = pd.DataFrame([
            {"Invoice_No": "INV-101", "Customer_Name": "Rahul Patel", "Amount": 10000},
            {"Invoice_No": "INV-102", "Customer_Name": "Alice Smith", "Amount": 15000}
        ])
        payments = pd.DataFrame([
            {"Payment_Ref": "INV-101", "Customer": "Rahul Patel", "Paid_Amount": 10000},
            {"Payment_Ref": "INV-102", "Customer": "Alice Smith", "Paid_Amount": 14950}  # Partial payment
        ])
        
        res = payment_reconciler.reconcile_payments(invoices, payments)
        stats = res["stats"]
        self.assertEqual(stats["counts"]["matched"], 1)
        self.assertEqual(stats["counts"]["partial"], 1)
        
    def test_inventory_reconciliation(self):
        pos = pd.DataFrame([
            {"SKU": "SKU_A", "Product_Name": "S24 Phone", "Quantity_Sold": 10}
        ])
        inventory = pd.DataFrame([
            {"SKU": "SKU_A", "Product_Name": "S24 Phone", "Stock_Remaining": -5}  # Negative Stock
        ])
        
        res = inventory_reconciler.reconcile_inventory(pos, inventory)
        self.assertEqual(res["stats"]["negative_stock_skus"], 1)
        self.assertEqual(res["anomalies"][0]["anomaly_type"], "Negative Stock Balance")
        
    def test_schema_drift_detection(self):
        baseline = ["Customer_Name", "Phone", "Revenue"]
        new_cols = ["CustomerName", "Mobile", "SalesAmount", "Extra_Col"]
        
        res = schema_drift.detect_schema_drift(baseline, new_cols)
        self.assertLess(res["stability_score"], 100)
        self.assertIn("Customer_Name", res["renamed"])
        self.assertIn("Extra_Col", res["added"])
        
    def test_sensitive_data_scanner_and_masking(self):
        df = pd.DataFrame([
            {"Email": "rahul@gmail.com", "Phone": "9876543210", "Revenue": 5000, "Notes": "Test notes"}
        ])
        
        scan_res = sensitive_scanner.scan_sensitive_data(df)
        self.assertEqual(scan_res["classifications"]["Email"], "PII")
        self.assertEqual(scan_res["classifications"]["Revenue"], "Financial")
        self.assertEqual(scan_res["risk_level"], "Medium")
        
        # Test masking for Analyst
        masked_df = sensitive_scanner.mask_dataframe_for_role(df, "DATA ANALYST")
        self.assertTrue(masked_df.iloc[0]["Email"].startswith("ra"))
        self.assertIn("***", masked_df.iloc[0]["Email"])
        self.assertIn("******", masked_df.iloc[0]["Phone"])
        
        # Test mask/block for Viewer
        viewer_df = sensitive_scanner.mask_dataframe_for_role(df, "VIEWER")
        self.assertTrue(viewer_df.empty) # blocked raw preview
        
    def test_rule_generator_and_validator(self):
        df_for_suggest = pd.DataFrame([
            {"GSTIN": "24AAAAP1234F1Z9", "Revenue": 500}
        ])
        
        rules = rule_generator.generate_suggested_rules(df_for_suggest)
        self.assertTrue(any(r["rule_type"] == "GSTIN_FORMAT" for r in rules))
        self.assertTrue(any(r["rule_type"] == "NON_NEGATIVE" for r in rules))
        
        df_for_val = pd.DataFrame([
            {"GSTIN": "24AAAAP1234F1Z9", "Revenue": -500}
        ])
        active_rules = [
            {"column": "Revenue", "rule_type": "NON_NEGATIVE", "description": "Cannot be negative."}
        ]
        val_res = rule_generator.validate_rules(df_for_val, active_rules)
        self.assertEqual(val_res["compliance_score"], 0)
        self.assertEqual(val_res["violations_count"], 1)
        self.assertEqual(val_res["violations"][0]["column"], "Revenue")
        
    def test_reconciliation_api_endpoints(self):
        # Insert datasets into ACTIVE_DATASETS cache
        ACTIVE_DATASETS["t_inv"] = pd.DataFrame([
            {"Invoice_No": "INV1001", "Customer_Name": "Rahul Patel", "Amount": 10000}
        ])
        ACTIVE_DATASETS["t_pay"] = pd.DataFrame([
            {"Payment_Ref": "INV1001", "Customer": "Rahul Patel", "Paid_Amount": 10000}
        ])
        
        # Run Payment API
        r = self.client.post("/api/reconcile/payments", json={
            "invoice_dataset_id": "t_inv",
            "payment_dataset_id": "t_pay",
            "role": "ADMIN",
            "username": "admin@qualix.ai"
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["stats"]["counts"]["matched"], 1)
        
        # Run Schema Drift API
        r_drift = self.client.post("/api/drift/detect", json={
            "baseline_dataset_id": "t_inv",
            "new_dataset_id": "t_pay",
            "role": "ADMIN",
            "username": "admin@qualix.ai"
        })
        self.assertEqual(r_drift.status_code, 200)
        
        # Run Rule Validation API
        r_rule = self.client.post("/api/rules/validate", json={
            "dataset_id": "t_inv",
            "active_rules": [
                {"column": "Amount", "rule_type": "NON_NEGATIVE", "description": "Cannot be negative."}
            ],
            "role": "ADMIN",
            "username": "admin@qualix.ai"
        })
        self.assertEqual(r_rule.status_code, 200)

    def test_user_management_lifecycle(self):
        # 1. Test listing users with VIEWER role -> must be 403 Forbidden
        r = self.client.get("/api/users?role=VIEWER&username=viewer@qualix.ai")
        self.assertEqual(r.status_code, 403)

        # 2. Test listing users with ADMIN role -> 200 OK
        r = self.client.get("/api/users?role=ADMIN&username=admin@qualix.ai")
        self.assertEqual(r.status_code, 200)
        users = r.json()["users"]
        self.assertTrue(any(u["email"] == "admin@qualix.ai" for u in users))
        
        # Verify passwords are never returned in response list
        for u in users:
            self.assertNotIn("password", u)

        # 3. Test adding a user as Admin
        r = self.client.post("/api/users/add", json={
            "email": "colleague@qualix.ai",
            "name": "Colleague",
            "role": "DATA ANALYST",
            "password": "colleague123",
            "admin_role": "ADMIN",
            "admin_username": "admin@qualix.ai"
        })
        self.assertEqual(r.status_code, 200)

        # 4. Test logging in as the newly added user
        r_login = self.client.post("/api/auth/login", json={
            "username": "colleague@qualix.ai",
            "password": "colleague123"
        })
        self.assertEqual(r_login.status_code, 200)
        self.assertEqual(r_login.json()["role"], "DATA ANALYST")

        # 5. Test updating the user's role to VIEWER
        r_update = self.client.put("/api/users/colleague@qualix.ai", json={
            "role": "VIEWER",
            "admin_role": "ADMIN",
            "admin_username": "admin@qualix.ai"
        })
        self.assertEqual(r_update.status_code, 200)
        
        # Verify role updated successfully
        r = self.client.get("/api/users?role=ADMIN&username=admin@qualix.ai")
        users = r.json()["users"]
        target = next((u for u in users if u["email"] == "colleague@qualix.ai"), None)
        self.assertIsNotNone(target)
        self.assertEqual(target["role"], "VIEWER")

        # 6. Test deactivating/revoking the user's access
        r_deact = self.client.post("/api/users/deactivate", json={
            "email": "colleague@qualix.ai",
            "admin_role": "ADMIN",
            "admin_username": "admin@qualix.ai"
        })
        self.assertEqual(r_deact.status_code, 200)

        # 7. Test logging in as the deactivated user -> must fail (401 Unauthorized)
        r_login_fail = self.client.post("/api/auth/login", json={
            "username": "colleague@qualix.ai",
            "password": "colleague123"
        })
        self.assertEqual(r_login_fail.status_code, 401)
        self.assertIn("deactivated", r_login_fail.json()["detail"].lower())

        # 8. Test protecting the root Admin account from role modifications or deactivations
        r_admin_role = self.client.put("/api/users/admin@qualix.ai", json={
            "role": "VIEWER",
            "admin_role": "ADMIN",
            "admin_username": "admin@qualix.ai"
        })
        self.assertEqual(r_admin_role.status_code, 400)
        
        r_admin_deact_put = self.client.put("/api/users/admin@qualix.ai", json={
            "active": False,
            "admin_role": "ADMIN",
            "admin_username": "admin@qualix.ai"
        })
        self.assertEqual(r_admin_deact_put.status_code, 400)
        
        r_admin_deact_post = self.client.post("/api/users/deactivate", json={
            "email": "admin@qualix.ai",
            "admin_role": "ADMIN",
            "admin_username": "admin@qualix.ai"
        })
        self.assertEqual(r_admin_deact_post.status_code, 400)

    def test_dataset_download(self):
        # 1. Test downloading public preset 'retail_sales' as Admin
        r = self.client.get("/api/datasets/retail_sales/download?role=ADMIN&username=admin@qualix.ai")
        self.assertEqual(r.status_code, 200)
        csv_content = r.json()["csv_content"]
        self.assertTrue(len(csv_content) > 0)

        # 2. Test downloading an invalid dataset ID -> must fail (404 Not Found)
        r_fail = self.client.get("/api/datasets/invalid_ds_id/download?role=ADMIN&username=admin@qualix.ai")
        self.assertEqual(r_fail.status_code, 404)



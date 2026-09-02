import os
import sys
import unittest
import requests
import pandas as pd

# Ensure services directory is in search path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import (
    encryption,
    clamav_scanner,
    rbac,
    duplicate_detector,
    data_quality,
    readiness_score
)

BACKEND_URL = "http://127.0.0.1:8000"

class TestQualixAI(unittest.TestCase):
    
    def test_encryption_decryption(self):
        original = b"Secure corporate spreadsheet data payload"
        token = encryption.encrypt_data(original)
        decrypted = encryption.decrypt_data(token)
        self.assertEqual(decrypted, original)
        
    def test_clamav_malware_detection(self):
        # Test simulated infected EICAR string
        eicar_string = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
        scan1 = clamav_scanner.scan_file_malware(eicar_string)
        self.assertEqual(scan1["status"], "Infected")
        
        # Test clean string
        clean_string = b"OrderID,Client,Revenue\nORD-001,Rahul,500"
        scan2 = clamav_scanner.scan_file_malware(clean_string)
        self.assertIn(scan2["status"], ["Clean", "Unavailable"])
        
    def test_rbac_rules(self):
        self.assertTrue(rbac.has_permission("ADMIN", "view_audit_logs"))
        self.assertTrue(rbac.has_permission("DATA ANALYST", "apply_safe_fixes"))
        self.assertFalse(rbac.has_permission("VIEWER", "apply_safe_fixes"))
        self.assertFalse(rbac.has_permission("VIEWER", "upload_datasets"))
        
    def test_fuzzy_duplicate_clustering(self):
        names = ["Rahul Patel", "Rahul K Patel", "R Patel", "Rahulk Patel", "Alice Wilson", "Alice Wilson"]
        clusters = duplicate_detector.find_duplicate_names(names)
        
        # We expect a cluster containing the Rahul Patel variations
        self.assertTrue(len(clusters) >= 1)
        cluster_primaries = [c["primary"] for c in clusters]
        self.assertTrue(any("Rahul" in p for p in cluster_primaries))
        
    def test_readiness_scoring_delta(self):
        # 1. Base messy data
        df = pd.DataFrame([
            {"col1": "A", "col2": 10},
            {"col1": "A", "col2": 10},  # duplicate
            {"col1": None, "col2": 15}  # missing
        ])
        
        quality_before = data_quality.calculate_data_quality_metrics(df)
        sec_status = {"status": "Clean"}
        ml_suitability = {"hasTargetLeakage": False, "classImbalance": "Optimal", "highCardinalityCol": ""}
        
        score_before = readiness_score.compile_readiness_score(quality_before, ml_suitability, sec_status)
        
        # 2. Cleaned data
        df_cleaned = df.drop_duplicates().dropna()
        quality_after = data_quality.calculate_data_quality_metrics(df_cleaned)
        score_after = readiness_score.compile_readiness_score(quality_after, ml_suitability, sec_status)
        
        self.assertTrue(score_after["overallReadiness"] > score_before["overallReadiness"])

    def test_api_authentication(self):
        # Admin Login
        r_admin = requests.post(f"{BACKEND_URL}/api/auth/login", json={
            "username": "admin@qualix.ai",
            "password": "admin123"
        })
        self.assertEqual(r_admin.status_code, 200)
        self.assertEqual(r_admin.json()["role"], "ADMIN")

        # Invalid Login
        r_fail = requests.post(f"{BACKEND_URL}/api/auth/login", json={
            "username": "admin@qualix.ai",
            "password": "wrongpassword"
        })
        self.assertEqual(r_fail.status_code, 401)

    def test_api_rbac_audit_logs(self):
        # Admin Request -> Allowed
        r_admin = requests.get(f"{BACKEND_URL}/api/audit-logs", params={
            "role": "ADMIN",
            "username": "admin@qualix.ai"
        })
        self.assertEqual(r_admin.status_code, 200)
        self.assertIn("logs", r_admin.json())

        # Analyst Request -> Blocked (403)
        r_analyst = requests.get(f"{BACKEND_URL}/api/audit-logs", params={
            "role": "DATA ANALYST",
            "username": "analyst@qualix.ai"
        })
        self.assertEqual(r_analyst.status_code, 403)

        # Viewer Request -> Blocked (403)
        r_viewer = requests.get(f"{BACKEND_URL}/api/audit-logs", params={
            "role": "VIEWER",
            "username": "viewer@qualix.ai"
        })
        self.assertEqual(r_viewer.status_code, 403)

if __name__ == "__main__":
    unittest.main()

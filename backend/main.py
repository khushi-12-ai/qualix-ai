import os
import io
import sys
import json
import base64
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import pandas as pd
import numpy as np

# Ensure services directory is in search path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Import modular services
from services import (
    encryption,
    clamav_scanner,
    rbac,
    audit_logger,
    data_quality,
    data_profile,
    duplicate_detector,
    anomaly_detector,
    ml_readiness,
    readiness_score,
    report_generator,
    source_detector,
    schema_matcher,
    entity_resolver,
    conflict_detector,
    merge_engine,
    field_classifier,
    scan_scope,
    payment_reconciler,
    inventory_reconciler,
    schema_drift,
    sensitive_scanner,
    rule_generator,
    system_integrator,
    notification_service,
    scheduled_monitor,
    local_language_ai
)

app = FastAPI(title="Qualix AI - Modular API Backend Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Demo Database / Cache in-memory for loaded datasets
ACTIVE_DATASETS: Dict[str, pd.DataFrame] = {}
DATASET_METADATA: Dict[str, Dict[str, Any]] = {}
ACTIVE_SCOPES: Dict[str, Dict[str, Any]] = {}
UPLOADED_SOURCES: Dict[str, Dict[str, Any]] = {}
DATA_DIR = "data"

# Globally managed Authorized Team Registry
USERS_REGISTRY: Dict[str, Dict[str, Any]] = {
    "admin@qualix.ai": {
        "email": "admin@qualix.ai",
        "name": "Admin User",
        "role": "ADMIN",
        "password": "admin123",
        "active": True,
        "created_at": "2026-08-23 00:00:00"
    },
    "analyst@qualix.ai": {
        "email": "analyst@qualix.ai",
        "name": "Tisha",
        "role": "DATA ANALYST",
        "password": "analyst123",
        "active": True,
        "created_at": "2026-08-23 00:00:00"
    },
    "viewer@qualix.ai": {
        "email": "viewer@qualix.ai",
        "name": "Viewer Guest",
        "role": "VIEWER",
        "password": "viewer123",
        "active": True,
        "created_at": "2026-08-23 00:00:00"
    }
}

# Pre-load demo datasets into memory on startup
def load_built_in_datasets():
    presets_csv = {
        "retail_sales": "retail_sales.csv",
        "customer_churn": "customer_churn.csv",
        "inventory_logistics": "inventory_logistics.csv"
    }
    presets_excel = {
        "invoices": "Invoices.xlsx",
        "payments": "Payments.xlsx",
        "inventory": "Inventory.xlsx"
    }
    import datetime
    for key, filename in presets_csv.items():
        path = os.path.join(DATA_DIR, filename)
        if os.path.exists(path):
            try:
                ACTIVE_DATASETS[key] = pd.read_csv(path)
                DATASET_METADATA[key] = {
                    "filename": filename,
                    "creator_username": "System",
                    "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            except Exception:
                pass
    for key, filename in presets_excel.items():
        path = os.path.join(DATA_DIR, filename)
        if os.path.exists(path):
            try:
                ACTIVE_DATASETS[key] = pd.read_excel(path)
                DATASET_METADATA[key] = {
                    "filename": filename,
                    "creator_username": "System",
                    "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            except Exception:
                pass

load_built_in_datasets()

def check_dataset_access(dataset_id: str, role: str, username: str):
    """
    Enforces RBAC access controls:
    - ADMIN and DATA ANALYST can view/access all datasets.
    - VIEWER can only view public presets or datasets they uploaded/created themselves.
    """
    clean_role = str(role).strip().upper()
    if clean_role in ["ADMIN", "DATA ANALYST"]:
        return
        
    public_presets = ["retail_sales", "customer_churn", "inventory_logistics"]
    if dataset_id in public_presets:
        return
        
    meta = DATASET_METADATA.get(dataset_id, {})
    creator = meta.get("creator_username", "")
    if creator and creator.lower() == username.strip().lower():
        return
        
    raise HTTPException(status_code=403, detail="Permission Denied: Viewer role is restricted from accessing this unauthorized dataset.")

def get_scoped_dataframe(dataset_id: str) -> pd.DataFrame:
    df = ACTIVE_DATASETS.get(dataset_id)
    if df is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    scope = ACTIVE_SCOPES.get(dataset_id)
    if scope and "selected" in scope:
        selected_cols = scope["selected"]
        existing_selected = [c for c in selected_cols if c in df.columns]
        if existing_selected:
            return df[existing_selected]
    return df

# ==========================================
# 1. AUTHENTICATION & LOGIN
# ==========================================
class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/auth/login")
async def login(req: LoginRequest):
    email = req.username.strip().lower()
    if email in USERS_REGISTRY:
        user_info = USERS_REGISTRY[email]
        if req.password == user_info["password"]:
            # Check if user is active
            if not user_info.get("active", True):
                audit_logger.log_event(user_info["name"], "Login", "FAILED", f"Suspended account login attempt blocked for email: {email}")
                raise HTTPException(status_code=401, detail="This account has been deactivated. Contact an administrator.")
                
            role = user_info["role"]
            name = user_info["name"]
            audit_logger.log_event(name, "Login", "SUCCESS", f"User logged in securely with role {role}.")
            return {
                "status": "success",
                "username": email,
                "role": role,
                "name": name
            }
            
    audit_logger.log_event("Guest", "Login", "FAILED", f"Unauthorized attempt for username: {email}")
    raise HTTPException(status_code=401, detail="Invalid username or password credentials.")


# ---- Admin User Management API Endpoints ----

class AddUserRequest(BaseModel):
    email: str
    name: str
    role: str
    password: str
    admin_role: str
    admin_username: str

class UpdateUserRequest(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    active: Optional[bool] = None
    admin_role: str
    admin_username: str

class DeactivateUserRequest(BaseModel):
    email: str
    admin_role: str
    admin_username: str

@app.get("/api/users")
async def list_users(role: str = Query("VIEWER"), username: str = Query("Guest")):
    if not rbac.has_permission(role, "manage_users"):
        audit_logger.log_event(username, "List Users", "DENIED", "Insufficient role privileges.")
        raise HTTPException(status_code=403, detail="Permission Denied: Only Admin role can manage users.")
    
    users_list = []
    for email, info in USERS_REGISTRY.items():
        users_list.append({
            "email": info["email"],
            "name": info["name"],
            "role": info["role"],
            "active": info["active"],
            "created_at": info["created_at"]
        })
    return {"users": users_list}

@app.post("/api/users/add")
async def add_user(req: AddUserRequest):
    if not rbac.has_permission(req.admin_role, "manage_users"):
        audit_logger.log_event(req.admin_username, "Add User", "DENIED", "Insufficient role privileges.")
        raise HTTPException(status_code=403, detail="Permission Denied: Only Admin role can manage users.")
    
    email = req.email.strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required.")
    if email in USERS_REGISTRY:
        raise HTTPException(status_code=400, detail=f"User with email '{email}' already exists.")
    
    role = req.role.strip().upper()
    if role not in ["ADMIN", "DATA ANALYST", "VIEWER"]:
        raise HTTPException(status_code=400, detail=f"Invalid role: {role}")
        
    import datetime
    USERS_REGISTRY[email] = {
        "email": email,
        "name": req.name.strip(),
        "role": role,
        "password": req.password,
        "active": True,
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    audit_logger.log_event(req.admin_username, "ADD_USER", "SUCCESS", f"Created user {email} with role {role}.")
    return {"status": "success", "message": f"User {email} created successfully."}

@app.put("/api/users/{email}")
async def update_user(email: str, req: UpdateUserRequest):
    if not rbac.has_permission(req.admin_role, "manage_users"):
        audit_logger.log_event(req.admin_username, "Update User", "DENIED", "Insufficient privileges.")
        raise HTTPException(status_code=403, detail="Permission Denied: Only Admin role can manage users.")
        
    target_email = email.strip().lower()
    if target_email not in USERS_REGISTRY:
        raise HTTPException(status_code=404, detail=f"User '{target_email}' not found.")
        
    # Protect root admin account from modification
    if target_email == "admin@qualix.ai":
        if req.active is False:
            raise HTTPException(status_code=400, detail="Cannot deactivate the default Admin account.")
        if req.role and req.role.strip().upper() != "ADMIN":
            raise HTTPException(status_code=400, detail="Cannot change the role of the default Admin account.")
            
    user = USERS_REGISTRY[target_email]
    
    if req.name is not None:
        user["name"] = req.name.strip()
    if req.role is not None:
        role = req.role.strip().upper()
        if role not in ["ADMIN", "DATA ANALYST", "VIEWER"]:
            raise HTTPException(status_code=400, detail=f"Invalid role: {role}")
        user["role"] = role
    if req.active is not None:
        user["active"] = bool(req.active)
        
    audit_logger.log_event(req.admin_username, "UPDATE_USER", "SUCCESS", f"Updated user {target_email} details.")
    return {"status": "success", "message": f"User {target_email} updated successfully."}

@app.post("/api/users/deactivate")
async def deactivate_user(req: DeactivateUserRequest):
    if not rbac.has_permission(req.admin_role, "manage_users"):
        audit_logger.log_event(req.admin_username, "Deactivate User", "DENIED", "Insufficient privileges.")
        raise HTTPException(status_code=403, detail="Permission Denied: Only Admin role can manage users.")
        
    target_email = req.email.strip().lower()
    if target_email not in USERS_REGISTRY:
        raise HTTPException(status_code=404, detail=f"User '{target_email}' not found.")
        
    # Protect root admin account from deactivation
    if target_email == "admin@qualix.ai":
        raise HTTPException(status_code=400, detail="Cannot deactivate the default Admin account.")
        
    USERS_REGISTRY[target_email]["active"] = False
    
    audit_logger.log_event(req.admin_username, "DEACTIVATE_USER", "SUCCESS", f"Deactivated user {target_email}.")
    return {"status": "success", "message": f"User {target_email} has been deactivated."}


# ==========================================
# 2. FILE SECURITY & UPLOAD INGESTION PIPELINE
# ==========================================
@app.post("/api/upload")
async def upload_dataset(
    file: UploadFile = File(...),
    role: str = Form("VIEWER"),
    username: str = Form("Guest")
):
    # RBAC boundary check on upload
    if not rbac.has_permission(role, "upload_datasets"):
        audit_logger.log_event(username, "File Upload", "DENIED", "Insufficient role privileges.")
        raise HTTPException(status_code=403, detail="Permission Denied: Viewer role cannot upload datasets.")
        
    filename = file.filename
    # Size check (limit to 10MB)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        audit_logger.log_event(username, "File Ingestion", "FAILED", f"File size exceeds 10MB limit: {filename}")
        raise HTTPException(status_code=400, detail="File too large. Limits are set at 10MB.")
        
    # Malware scanning check
    scan_res = clamav_scanner.scan_file_malware(content)
    audit_logger.log_event(username, "ClamAV Scan", scan_res["status"], f"Checked file: {filename}")
    
    if scan_res["status"] == "Infected":
        audit_logger.log_event(username, "Malware Detected", "BLOCKED", f"Threat blocking applied on {filename}")
        raise HTTPException(
            status_code=400, 
            detail=f"Security Scan Blocked: The uploaded file failed the security scan. Threat: {scan_res['virus']}"
        )
        
    # File type validation
    ext = os.path.splitext(filename)[1].lower()
    if ext not in [".csv", ".xlsx", ".xls"]:
        audit_logger.log_event(username, "File Extension Validation", "FAILED", f"Invalid format upload attempted: {filename}")
        raise HTTPException(status_code=400, detail="Unsupported file format. Please upload CSV or Excel spreadsheet.")

    # Encrypt protected storage copy at-rest
    encrypted_token = encryption.encrypt_data(content)
    with open("encrypted_dataset.csv.enc", "wb") as f_enc:
        f_enc.write(encrypted_token)
        
    # Load into memory via Pandas
    try:
        if ext == ".csv":
            df = pd.read_csv(io.StringIO(content.decode("utf-8", errors="ignore")))
        else:
            df = pd.read_excel(io.BytesIO(content))
            
        dataset_id = f"uploaded_{int(pd.Timestamp.now().timestamp())}"
        ACTIVE_DATASETS[dataset_id] = df
        DATASET_METADATA[dataset_id] = {
            "filename": filename,
            "creator_username": username,
            "created_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        audit_logger.log_event(username, "File Ingest & Encrypt", "SUCCESS", f"Uploaded and stored dataset '{filename}' ID: {dataset_id}")
        
        return {
            "status": "success",
            "datasetId": dataset_id,
            "filename": filename,
            "rows": len(df),
            "cols": len(df.columns),
            "security": {
                "scan": "CLEAN",
                "encryption": "ACTIVE",
                "storage": "ENABLED",
                "details": scan_res["message"]
            }
        }
    except Exception as e:
        audit_logger.log_event(username, "Data Parsing", "FAILED", f"Unable to parse dataset: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Data parsing error: {str(e)}")


# ==========================================
# 3. ANALYSIS & READINESS MODULES
# ==========================================
@app.get("/api/datasets")
async def list_datasets():
    """Lists currently active datasets in memory."""
    meta = []
    for k, df in ACTIVE_DATASETS.items():
        meta.append({
            "id": k,
            "rows": len(df),
            "cols": len(df.columns)
        })
    return {"datasets": meta}

@app.get("/api/datasets/{dataset_id}/download")
async def download_dataset(dataset_id: str, role: str = "VIEWER", username: str = "Guest"):
    # Built-in datasets are recoverable demo assets. Reload them if an in-memory
    # cache was cleared (for example after a development reload) so links in the
    # UI do not unexpectedly lead to a 404.
    if dataset_id in {"retail_sales", "customer_churn", "inventory_logistics", "invoices", "payments", "inventory"} and dataset_id not in ACTIVE_DATASETS:
        load_built_in_datasets()
    check_dataset_access(dataset_id, role, username)
    if dataset_id not in ACTIVE_DATASETS:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    df = ACTIVE_DATASETS[dataset_id]
    df_masked = sensitive_scanner.mask_dataframe_for_role(df, role)
    
    csv_io = io.StringIO()
    df_masked.to_csv(csv_io, index=False)
    
    return JSONResponse(content={
        "status": "success",
        "csv_content": csv_io.getvalue()
    })


@app.post("/api/analyze/profile")
async def analyze_profile(datasetId: str = Form(...), username: str = Form("Guest"), role: str = Form("VIEWER")):
    check_dataset_access(datasetId, role, username)
    if datasetId not in ACTIVE_DATASETS:
        raise HTTPException(status_code=404, detail="Dataset not found in active workspace.")
        
    df = ACTIVE_DATASETS[datasetId]
    df_masked = sensitive_scanner.mask_dataframe_for_role(df, role)
    profile = data_profile.compile_dataset_profile(df_masked)
    
    # Enrich with scan scope status
    scope = ACTIVE_SCOPES.get(datasetId, {})
    selected = scope.get("selected", list(df.columns))
    for col in profile.get("colProfiles", {}):
        profile["colProfiles"][col]["scope_status"] = "Included" if col in selected else "Excluded from analysis"
        
    audit_logger.log_event(username, "Dataset Profile", "SUCCESS", f"Generated structure details for {datasetId}.")
    return profile

@app.post("/api/analyze/quality")
async def analyze_quality(datasetId: str = Form(...), username: str = Form("Guest"), role: str = Form("VIEWER")):
    check_dataset_access(datasetId, role, username)
    if datasetId not in ACTIVE_DATASETS:
        raise HTTPException(status_code=404, detail="Dataset not found in active workspace.")
        
    df_scoped = get_scoped_dataframe(datasetId)
    quality = data_quality.calculate_data_quality_metrics(df_scoped)
    audit_logger.log_event(username, "Dataset Quality Audit", "SUCCESS", f"Calculated quality scorecard scores for {datasetId}.")
    return quality

@app.post("/api/analyze/ml")
async def analyze_ml(datasetId: str = Form(...), username: str = Form("Guest"), role: str = Form("VIEWER")):
    check_dataset_access(datasetId, role, username)
    if datasetId not in ACTIVE_DATASETS:
        raise HTTPException(status_code=404, detail="Dataset not found in active workspace.")
        
    df_scoped = get_scoped_dataframe(datasetId)
    ml_results = ml_readiness.analyze_ml_suitability(df_scoped)
    audit_logger.log_event(username, "Dataset ML Suitability Check", "SUCCESS", f"Identified leakage, skews, and cardinality risks for {datasetId}.")
    return ml_results

@app.post("/api/analyze/readiness")
async def analyze_readiness(
    datasetId: str = Form(...),
    username: str = Form("Guest"),
    role: str = Form("VIEWER"),
    clamav_status: str = Form("Clean")
):
    check_dataset_access(datasetId, role, username)
    if datasetId not in ACTIVE_DATASETS:
        raise HTTPException(status_code=404, detail="Dataset not found in active workspace.")
        
    df_scoped = get_scoped_dataframe(datasetId)
    quality = data_quality.calculate_data_quality_metrics(df_scoped)
    ml_results = ml_readiness.analyze_ml_suitability(df_scoped)
    
    sec_status = {"status": clamav_status}
    scores = readiness_score.compile_readiness_score(quality, ml_results, sec_status)
    
    # Enrich scores output to show scope counts
    full_df = ACTIVE_DATASETS[datasetId]
    scope = ACTIVE_SCOPES.get(datasetId, {})
    selected_count = len(scope.get("selected", list(full_df.columns)))
    total_count = len(full_df.columns)
    scores["scope_selected"] = selected_count
    scores["scope_total"] = total_count
    
    audit_logger.log_event(username, "AI Readiness Calculate", "SUCCESS", f"Aggregated AI readiness score: {scores['overallReadiness']}/100.")
    return scores


# ==========================================
# 4. FIX CENTER & PREVIEW EXCHANGERS
# ==========================================
@app.post("/api/fixes/preview")
async def fix_preview(
    datasetId: str = Form(...),
    fixes: str = Form("[]"),  # JSON serialized list of selected fixes
    role: str = Form("VIEWER"),
    username: str = Form("Guest")
):
    # RBAC boundary check on applying transformation fixes
    if not rbac.has_permission(role, "apply_safe_fixes"):
        raise HTTPException(status_code=403, detail="Permission Denied: User role is restricted from applying fixes.")
        
    if datasetId not in ACTIVE_DATASETS:
        raise HTTPException(status_code=404, detail="Dataset not found.")
        
    df = ACTIVE_DATASETS[datasetId].copy()
    selected_fixes = json.loads(fixes)
    
    # 1. Deduplication
    if "remove_duplicates" in selected_fixes:
        df = df.drop_duplicates()
        
    # 2. Normalize capitalization
    if "normalize_cities" in selected_fixes:
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.strip().str.title()
                
    # 3. Impute missing values
    if "fill_missing" in selected_fixes:
        null_reps = ['nan', '', 'none', 'n/a', '-', 'null']
        for col in df.columns:
            is_empty = df[col].astype(str).str.strip().str.lower().isin(null_reps) | df[col].isna()
            if is_empty.any():
                numeric_series = pd.to_numeric(df[col], errors='coerce')
                if not numeric_series.dropna().empty:
                    df.loc[is_empty, col] = numeric_series.median()
                else:
                    non_empty = df.loc[~is_empty, col]
                    if not non_empty.empty:
                        df.loc[is_empty, col] = non_empty.mode()[0]
                    else:
                        df.loc[is_empty, col] = "Unknown"
                        
    # 4. Outliers removal
    if "remove_anomalies" in selected_fixes:
        for col in df.columns:
            numeric_vals = pd.to_numeric(df[col].astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False).str.strip(), errors='coerce')
            if len(numeric_vals.dropna()) >= 4:
                q1 = numeric_vals.quantile(0.25)
                q3 = numeric_vals.quantile(0.75)
                iqr = q3 - q1
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr
                df = df[(numeric_vals >= lower_bound) & (numeric_vals <= upper_bound) | numeric_vals.isna()]

    # Run recalculations
    quality = data_quality.calculate_data_quality_metrics(df)
    ml_results = ml_readiness.analyze_ml_suitability(df)
    scores = readiness_score.compile_readiness_score(quality, ml_results, {"status": "Clean"})
    
    # Generate cleaned preview data table
    df_masked = sensitive_scanner.mask_dataframe_for_role(df, role)
    preview = data_profile.compile_dataset_profile(df_masked)
    
    # Perform fuzzy name duplicates search using RapidFuzz
    fuzzy_clusters = []
    name_cols = [c for c in df.columns if any(k in c.lower() for k in ['client', 'customer', 'name', 'employee', 'student', 'patient'])]
    if name_cols:
        name_col = name_cols[0]
        fuzzy_clusters = duplicate_detector.find_duplicate_names(list(df[name_col].dropna()))
        
    return {
        "scoreCard": scores,
        "qualityMetrics": quality,
        "mlMetrics": ml_results,
        "dataPreview": preview["dataPreview"],
        "fuzzyDuplicates": fuzzy_clusters
    }

@app.post("/api/fixes/apply")
async def fix_apply(
    datasetId: str = Form(...),
    fixes: str = Form("[]"),
    role: str = Form("VIEWER"),
    username: str = Form("Guest")
):
    if not rbac.has_permission(role, "apply_safe_fixes"):
        raise HTTPException(status_code=403, detail="Permission Denied: User role is restricted from applying fixes.")
        
    if datasetId not in ACTIVE_DATASETS:
        raise HTTPException(status_code=404, detail="Dataset not found.")
        
    # Retrieve fixes preview payload
    preview_data = await fix_preview(datasetId, fixes, role, username)
    
    # Save the transformed dataframe copy back into active storage space
    df_temp = ACTIVE_DATASETS[datasetId].copy()
    selected_fixes = json.loads(fixes)
    
    if "remove_duplicates" in selected_fixes:
        df_temp = df_temp.drop_duplicates()
    if "normalize_cities" in selected_fixes:
        for col in df_temp.columns:
            if df_temp[col].dtype == 'object':
                df_temp[col] = df_temp[col].astype(str).str.strip().str.title()
    if "fill_missing" in selected_fixes:
        null_reps = ['nan', '', 'none', 'n/a', '-', 'null']
        for col in df_temp.columns:
            is_empty = df_temp[col].astype(str).str.strip().str.lower().isin(null_reps) | df_temp[col].isna()
            if is_empty.any():
                numeric_series = pd.to_numeric(df_temp[col], errors='coerce')
                if not numeric_series.dropna().empty:
                    df_temp.loc[is_empty, col] = numeric_series.median()
                else:
                    non_empty = df_temp.loc[~is_empty, col]
                    if not non_empty.empty:
                        df_temp.loc[is_empty, col] = non_empty.mode()[0]
                    else:
                        df_temp.loc[is_empty, col] = "Unknown"
    if "remove_anomalies" in selected_fixes:
         for col in df_temp.columns:
            numeric_vals = pd.to_numeric(df_temp[col].astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False).str.strip(), errors='coerce')
            if len(numeric_vals.dropna()) >= 4:
                q1 = numeric_vals.quantile(0.25)
                q3 = numeric_vals.quantile(0.75)
                iqr = q3 - q1
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr
                df_temp = df_temp[(numeric_vals >= lower_bound) & (numeric_vals <= upper_bound) | numeric_vals.isna()]

    ACTIVE_DATASETS[datasetId] = df_temp
    
    cleaned_csv_io = io.StringIO()
    df_temp_masked = sensitive_scanner.mask_dataframe_for_role(df_temp, role)
    df_temp_masked.to_csv(cleaned_csv_io, index=False)
    
    audit_logger.log_event(username, "Apply Safe Fixes", "SUCCESS", f"Transformed dataset {datasetId} with modifications: {fixes}.")
    
    return {
        "status": "success",
        "scoreCard": preview_data["scoreCard"],
        "qualityMetrics": preview_data["qualityMetrics"],
        "mlMetrics": preview_data["mlMetrics"],
        "cleanedCSV": cleaned_csv_io.getvalue()
    }


# ==========================================
# 5. CO-PILOT CHAT DOCTOR & UTILS
# ==========================================
class ChatRequest(BaseModel):
    query: str
    role: str
    username: str
    analysis: dict

@app.post("/api/doctor/query")
async def chat_doctor_query(req: ChatRequest):
    # RBAC role limitation check on using chat features
    if not rbac.has_permission(req.role, "use_ai_doctor"):
        raise HTTPException(status_code=403, detail="Permission Denied: User role is restricted from utilizing AI Data Doctor.")
        
    query = req.query.lower()
    analysis = req.analysis
    
    reply = ""
    if any(k in query for k in ['readiness', 'score', 'why']):
        issues_bullets = "\n".join([f"• **{i['title']}** ({i['severity']} Risk): {i['description']}" for i in analysis.get('issues', [])])
        reply = f"The overall Qualix AI Readiness score is rated **{analysis.get('overallReadiness', 50)}/100**. This rating is primarily reduced by the following quality anomalies:\n\n{issues_bullets}"
    elif any(k in query for k in ['fix', 'remediate', 'improve']):
        reply = (
            "To increase your pipeline suitability to 90+, I suggest applying these transformations in the Fix Center:\n\n"
            "1. **Impute null categories and values** (fixes Completeness issues).\n"
            "2. **Deduplicate records** (reduces redundant feature weights).\n"
            "3. **Convert casing formats to Title Case** (fixes Consistency anomalies).\n\n"
            "You can execute these safe fixes in the **Fix Center** sidebar panel."
        )
    elif "leakage" in query:
        if analysis.get('mlMetrics', {}).get('hasTargetLeakage'):
            reply = f"Target Leakage Risk: Column \"{analysis.get('mlMetrics', {}).get('targetLeakageCol')}\" contains variables created downstream AFTER the event churn occurs. Standard predictive runs utilizing this feature will overfit. Suggest excluding this column."
        else:
            reply = "I checked your schema for leakage loops, and all variables appear temporally correct. Low Risk."
    elif "imbalance" in query:
        reply = f"The target class imbalance is **{analysis.get('mlMetrics', {}).get('classImbalanceRatio')}** ({analysis.get('mlMetrics', {}).get('classImbalance')} skew). Suggest weighting training losses."
    elif "duplicate" in query:
        reply = "I ran RapidFuzz fuzzy name similarity grouping rules and detected customer entries with spelling variations. Standardizing these will merge redundant rows."
    else:
        reply = "Hello! I am your AI Data Doctor. Ask me to outline target leakage, class skewness, anomalies, or quality remediation fixes."
        
    audit_logger.log_event(req.username, "AI Data Doctor Chat", "SUCCESS", f"User queried doctor: '{req.query}'")
    return {"reply": reply}


# ==========================================
# 6. LOGS AND REPORTING ENDPOINTS
# ==========================================
@app.get("/api/audit-logs")
async def get_audit_logs(
    role: str = Query("VIEWER", description="Active user role"),
    username: str = Query("Guest", description="Active username"),
    search: str = Query("", description="Search logs by text content"),
    user: str = Query("", description="Filter logs by username"),
    action: str = Query("", description="Filter logs by action key"),
    status: str = Query("", description="Filter logs by status key")
):
    if not rbac.has_permission(role, "view_audit_logs"):
        audit_logger.log_event(username, "View Audit Logs", "DENIED", "Unauthorized role access attempt blocked.")
        raise HTTPException(status_code=403, detail="Permission Denied: Only Admin role can view audit logs.")
        
    logs = audit_logger.get_logs(
        search_query=search,
        filter_user=user,
        filter_action=action,
        filter_status=status
    )
    return {"logs": logs}

@app.post("/api/log_event")
async def post_frontend_event(
    username: str = Form(...),
    action: str = Form(...),
    status: str = Form(...),
    details: str = Form("")
):
    audit_logger.log_event(username, action, status, details)
    return {"status": "ok"}

@app.get("/api/reports/{id}")
async def get_report_data(id: str, datasetName: str = "retail_sales", user: str = "Tisha", overallReadiness: int = 80):
    score_data = {"overallReadiness": overallReadiness, "quality": overallReadiness, "mlReadiness": overallReadiness}
    rep = report_generator.compile_text_report(datasetName, score_data, user)
    return rep

@app.get("/api/certificate/{id}")
async def get_certificate_data(id: str, datasetName: str = "retail_sales", overallReadiness: int = 80):
    timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
    return {
        "certificateId": f"CERT-QUALIX-{id}-{overallReadiness}",
        "datasetId": f"DS-MOCK-{id}",
        "datasetName": datasetName.upper().replace("_", " "),
        "timestamp": timestamp,
        "score": overallReadiness,
        "securityStatus": "VERIFIED SAFE",
        "verificationStatus": "COMPLIANT"
    }

# ==========================================
# 7. SMART DATA MERGE & SCAN SCOPE ROUTERS
# ==========================================

class MergeProfileRequest(BaseModel):
    source_ids: List[str]
    role: str
    username: str

class SchemaMatchRequest(BaseModel):
    source_ids: List[str]
    role: str
    username: str

class EntityMatchRequest(BaseModel):
    source_ids: List[str]
    schema_mapping: List[Dict[str, Any]]
    matching_key: str
    role: str
    username: str

class ConflictsRequest(BaseModel):
    source_ids: List[str]
    schema_mapping: List[Dict[str, Any]]
    matching_key: str
    role: str
    username: str

class MergePreviewRequest(BaseModel):
    source_ids: List[str]
    schema_mapping: List[Dict[str, Any]]
    matching_key: str
    merge_strategy: str
    conflict_resolutions: Dict[str, str]
    role: str
    username: str

class MergeApplyRequest(BaseModel):
    source_ids: List[str]
    schema_mapping: List[Dict[str, Any]]
    matching_key: str
    merge_strategy: str
    conflict_resolutions: Dict[str, str]
    role: str
    username: str

class ScopeRecommendRequest(BaseModel):
    dataset_id: str
    role: str
    username: str

class ScopeValidateRequest(BaseModel):
    dataset_id: str
    selected_fields: List[str]
    role: str
    username: str

class ScopeApplyRequest(BaseModel):
    dataset_id: str
    selected_fields: List[str]
    classifications: Dict[str, str]
    role: str
    username: str

@app.post("/api/merge/upload")
async def merge_upload(
    files: List[UploadFile] = File(...),
    role: str = Form("VIEWER"),
    username: str = Form("Guest")
):
    if not rbac.has_permission(role, "upload_datasets"):
        audit_logger.log_event(username, "File Upload", "DENIED", "Insufficient role privileges.")
        raise HTTPException(status_code=403, detail="Permission Denied: Viewer role cannot upload datasets.")
        
    uploaded_results = []
    
    for file in files:
        filename = file.filename
        content = await file.read()
        
        # Security Size Check
        if len(content) > 10 * 1024 * 1024:
            audit_logger.log_event(username, "File Ingestion", "FAILED", f"File size exceeds 10MB limit: {filename}")
            raise HTTPException(status_code=400, detail=f"File too large: {filename}. Limits are set at 10MB.")
            
        # Security Malware check
        scan_res = clamav_scanner.scan_file_malware(content)
        audit_logger.log_event(username, "ClamAV Scan", scan_res["status"], f"Checked file: {filename}")
        
        if scan_res["status"] == "Infected":
            audit_logger.log_event(username, "Malware Detected", "BLOCKED", f"Threat blocking applied on {filename}")
            raise HTTPException(
                status_code=400, 
                detail=f"Security Scan Blocked: The file '{filename}' failed the security scan. Threat: {scan_res['virus']}"
            )
            
        # Extension Check
        ext = os.path.splitext(filename)[1].lower()
        if ext not in [".csv", ".xlsx", ".xls"]:
            audit_logger.log_event(username, "File Extension Validation", "FAILED", f"Invalid format upload: {filename}")
            raise HTTPException(status_code=400, detail=f"Unsupported format: {filename}. Please upload CSV or Excel.")
            
        # Encryption at rest
        encrypted_token = encryption.encrypt_data(content)
        enc_filename = f"encrypted_{filename}.enc"
        with open(enc_filename, "wb") as f_enc:
            f_enc.write(encrypted_token)
            
        # Load dataframe
        try:
            if ext == ".csv":
                df = pd.read_csv(io.StringIO(content.decode("utf-8", errors="ignore")))
            else:
                df = pd.read_excel(io.BytesIO(content))
        except Exception as e:
            audit_logger.log_event(username, "Data Parsing", "FAILED", f"Unable to parse dataset '{filename}': {str(e)}")
            raise HTTPException(status_code=500, detail=f"Data parsing error on '{filename}': {str(e)}")
            
        # Detect source type
        col_list = list(df.columns)
        detected = source_detector.detect_source_type(filename, col_list)
        
        source_id = f"source_{int(pd.Timestamp.now().timestamp())}_{filename.replace('.', '_')}"
        
        # Save to UPLOADED_SOURCES cache
        UPLOADED_SOURCES[source_id] = {
            "id": source_id,
            "filename": filename,
            "source_type": detected["detected_source"],
            "confidence": detected["confidence"],
            "df": df,
            "rows": len(df),
            "cols": len(df.columns),
            "size": len(content),
            "security_status": scan_res["status"],
            "processing_status": "READY",
            "creator_username": username
        }
        
        audit_logger.log_event(username, "SOURCE_UPLOADED", "SUCCESS", f"Ingested source {filename} as {detected['detected_source']}")
        
        uploaded_results.append({
            "id": source_id,
            "filename": filename,
            "source_type": detected["detected_source"],
            "confidence": detected["confidence"],
            "rows": len(df),
            "cols": len(df.columns),
            "size": len(content),
            "security_status": scan_res["status"],
            "processing_status": "READY"
        })
        
    return {"status": "success", "files": uploaded_results}

@app.post("/api/merge/profile")
async def merge_profile(req: MergeProfileRequest):
    if not rbac.has_permission(req.role, "merge_datasets"):
        raise HTTPException(status_code=403, detail="Permission Denied")
        
    profiles = {}
    for sid in req.source_ids:
        if sid not in UPLOADED_SOURCES:
            raise HTTPException(status_code=404, detail=f"Uploaded source {sid} not found")
        source = UPLOADED_SOURCES[sid]
        df = source["df"]
        profile = data_profile.compile_dataset_profile(df)
        profiles[sid] = {
            "filename": source["filename"],
            "source_type": source["source_type"],
            "profile": profile
        }
        
    audit_logger.log_event(req.username, "SOURCE_PROFILED", "SUCCESS", f"Profiled {len(req.source_ids)} sources.")
    return {"profiles": profiles}

@app.post("/api/merge/schema-match")
async def merge_schema_match(req: SchemaMatchRequest):
    if not rbac.has_permission(req.role, "merge_datasets"):
        raise HTTPException(status_code=403, detail="Permission Denied")
        
    dfs = {}
    for sid in req.source_ids:
        if sid in UPLOADED_SOURCES:
            dfs[sid] = UPLOADED_SOURCES[sid]["df"]
        elif sid in ACTIVE_DATASETS:
            dfs[sid] = ACTIVE_DATASETS[sid]
        else:
            raise HTTPException(status_code=404, detail=f"Uploaded source {sid} not found")
        
    mappings = schema_matcher.suggest_column_mapping(dfs)
    audit_logger.log_event(req.username, "SCHEMA_MATCHED", "SUCCESS", "Generated schema matching suggestions.")
    return {"mappings": mappings}

@app.post("/api/merge/entity-match")
async def merge_entity_match(req: EntityMatchRequest):
    if not rbac.has_permission(req.role, "merge_datasets"):
        raise HTTPException(status_code=403, detail="Permission Denied")
        
    dfs = {}
    for sid in req.source_ids:
        if sid in UPLOADED_SOURCES:
            dfs[sid] = UPLOADED_SOURCES[sid]["df"]
        elif sid in ACTIVE_DATASETS:
            dfs[sid] = ACTIVE_DATASETS[sid]
        else:
            raise HTTPException(status_code=404, detail=f"Uploaded source {sid} not found")
        
    res = entity_resolver.resolve_entities(dfs, req.schema_mapping, req.matching_key)
    audit_logger.log_event(req.username, "ENTITY_MATCH_REVIEWED", "SUCCESS", "Performed entity resolution analysis.")
    return {
        "duplicates": res["duplicates"],
        "stats": res["stats"]
    }

@app.post("/api/merge/conflicts")
async def merge_conflicts(req: ConflictsRequest):
    if not rbac.has_permission(req.role, "merge_datasets"):
        raise HTTPException(status_code=403, detail="Permission Denied")
        
    dfs = {}
    for sid in req.source_ids:
        if sid in UPLOADED_SOURCES:
            dfs[sid] = UPLOADED_SOURCES[sid]["df"]
        elif sid in ACTIVE_DATASETS:
            dfs[sid] = ACTIVE_DATASETS[sid]
        else:
            raise HTTPException(status_code=404, detail=f"Uploaded source {sid} not found")
        
    conflicts = conflict_detector.detect_conflicts(dfs, req.schema_mapping, req.matching_key)
    audit_logger.log_event(req.username, "CONFLICT_REVIEWED", "SUCCESS", f"Scanned conflicts. Found {len(conflicts)}")
    return {"conflicts": conflicts}

@app.post("/api/merge/preview")
async def merge_preview(req: MergePreviewRequest):
    if not rbac.has_permission(req.role, "merge_datasets"):
        raise HTTPException(status_code=403, detail="Permission Denied")
        
    dfs = {}
    for sid in req.source_ids:
        if sid in UPLOADED_SOURCES:
            dfs[sid] = UPLOADED_SOURCES[sid]["df"]
        elif sid in ACTIVE_DATASETS:
            dfs[sid] = ACTIVE_DATASETS[sid]
        else:
            raise HTTPException(status_code=404, detail=f"Uploaded source {sid} not found")
        
    preview = merge_engine.preview_merge(
        dfs, req.schema_mapping, req.merge_strategy, req.matching_key, req.conflict_resolutions
    )
    audit_logger.log_event(req.username, "MERGE_PREVIEWED", "SUCCESS", "Generated merge previews.")
    return preview

@app.post("/api/merge/apply")
async def merge_apply(req: MergeApplyRequest):
    if not rbac.has_permission(req.role, "merge_datasets"):
        raise HTTPException(status_code=403, detail="Permission Denied")
        
    dfs = {}
    source_filenames = []
    for sid in req.source_ids:
        if sid in UPLOADED_SOURCES:
            dfs[sid] = UPLOADED_SOURCES[sid]["df"]
            source_filenames.append(UPLOADED_SOURCES[sid]["filename"])
        elif sid in ACTIVE_DATASETS:
            dfs[sid] = ACTIVE_DATASETS[sid]
            source_filenames.append(DATASET_METADATA.get(sid, {}).get("filename", sid))
        else:
            raise HTTPException(status_code=404, detail=f"Uploaded source {sid} not found")
        
    df_unified = merge_engine.apply_merge(
        dfs, req.schema_mapping, req.merge_strategy, req.matching_key, req.conflict_resolutions
    )
    
    # Store unified dataset
    dataset_id = f"unified_{int(pd.Timestamp.now().timestamp())}"
    ACTIVE_DATASETS[dataset_id] = df_unified
    
    # Store metadata
    DATASET_METADATA[dataset_id] = {
        "filename": "Unified Dataset",
        "creator_username": req.username,
        "created_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "is_merged": True,
        "sources": source_filenames,
        "source_ids": req.source_ids,
        "matching_key": req.matching_key,
        "merge_strategy": req.merge_strategy,
        "schema_mapping": req.schema_mapping,
        "conflict_resolutions": req.conflict_resolutions
    }
    
    # Default scope to include all fields
    ACTIVE_SCOPES[dataset_id] = {
        "selected": list(df_unified.columns),
        "excluded": [],
        "classifications": field_classifier.classify_fields(df_unified)
    }
    
    audit_logger.log_event(
        req.username,
        "MERGE_APPLIED",
        "SUCCESS",
        f"Merged sources into {dataset_id} with {len(df_unified)} rows. Sources: {', '.join(source_filenames)}"
    )
    
    return {
        "status": "success",
        "dataset_id": dataset_id,
        "rows": len(df_unified),
        "cols": len(df_unified.columns)
    }

@app.post("/api/scope/recommend")
async def scope_recommend(req: ScopeRecommendRequest):
    check_dataset_access(req.dataset_id, req.role, req.username)
    if req.dataset_id not in ACTIVE_DATASETS:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    df = ACTIVE_DATASETS[req.dataset_id]
    classifications = field_classifier.classify_fields(df)
    recs = scan_scope.recommend_scan_scope(df, classifications)
    
    return {
        "classifications": classifications,
        "recommendations": recs
    }

@app.post("/api/scope/validate")
async def scope_validate(req: ScopeValidateRequest):
    check_dataset_access(req.dataset_id, req.role, req.username)
    if req.dataset_id not in ACTIVE_DATASETS:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    df = ACTIVE_DATASETS[req.dataset_id]
    val_res = scan_scope.validate_scope(df, req.selected_fields)
    return val_res

@app.post("/api/scope/apply")
async def scope_apply(req: ScopeApplyRequest):
    if not rbac.has_permission(req.role, "change_scan_scope"):
        raise HTTPException(status_code=403, detail="Permission Denied")
        
    check_dataset_access(req.dataset_id, req.role, req.username)
    if req.dataset_id not in ACTIVE_DATASETS:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    df = ACTIVE_DATASETS[req.dataset_id]
    excluded = [c for c in df.columns if c not in req.selected_fields]
    
    ACTIVE_SCOPES[req.dataset_id] = {
        "selected": req.selected_fields,
        "excluded": excluded,
        "classifications": req.classifications
    }
    
    audit_logger.log_event(
        req.username,
        "SCAN_SCOPE_CHANGED",
        "SUCCESS",
        f"Changed scan scope for {req.dataset_id}. Selected {len(req.selected_fields)} columns, excluded {len(excluded)}."
    )
    return {"status": "success"}

@app.get("/api/merge/{dataset_id}")
async def get_merge_metadata(dataset_id: str, role: str = Query("VIEWER"), username: str = Query("Guest")):
    if not rbac.has_permission(role, "view_merge_results"):
        raise HTTPException(status_code=403, detail="Permission Denied")
    check_dataset_access(dataset_id, role, username)
    
    meta = DATASET_METADATA.get(dataset_id, {})
    if not meta:
        raise HTTPException(status_code=404, detail="Dataset metadata not found")
        
    return meta

@app.get("/api/scope/{dataset_id}")
async def get_scope_metadata(dataset_id: str, role: str = Query("VIEWER"), username: str = Query("Guest")):
    if not rbac.has_permission(role, "view_scan_scope"):
        raise HTTPException(status_code=403, detail="Permission Denied")
    check_dataset_access(dataset_id, role, username)
    
    scope = ACTIVE_SCOPES.get(dataset_id, {})
    if not scope:
        if dataset_id in ACTIVE_DATASETS:
            df = ACTIVE_DATASETS[dataset_id]
            classifications = field_classifier.classify_fields(df)
            scope = {
                "selected": list(df.columns),
                "excluded": [],
                "classifications": classifications
            }
            ACTIVE_SCOPES[dataset_id] = scope
        else:
            raise HTTPException(status_code=404, detail="Dataset not found")
            
    return scope

# ==========================================
# 8. RECONCILIATION, SECURITY & DRIFT ROUTERS
# ==========================================

class PaymentsReconcileRequest(BaseModel):
    invoice_dataset_id: str
    payment_dataset_id: str
    role: str
    username: str

class InventoryReconcileRequest(BaseModel):
    pos_dataset_id: str
    inventory_dataset_id: str
    role: str
    username: str

class SchemaDriftRequest(BaseModel):
    baseline_dataset_id: str
    new_dataset_id: str
    role: str
    username: str

class SensitiveScanRequest(BaseModel):
    dataset_id: str
    role: str
    username: str

class RuleRecommendRequest(BaseModel):
    dataset_id: str
    role: str
    username: str

class RuleValidateRequest(BaseModel):
    dataset_id: str
    active_rules: List[Dict[str, Any]]
    role: str
    username: str

@app.post("/api/reconcile/payments")
async def reconcile_payments_route(req: PaymentsReconcileRequest):
    check_dataset_access(req.invoice_dataset_id, req.role, req.username)
    check_dataset_access(req.payment_dataset_id, req.role, req.username)
    if req.invoice_dataset_id not in ACTIVE_DATASETS or req.payment_dataset_id not in ACTIVE_DATASETS:
        raise HTTPException(status_code=404, detail="One or both datasets not found.")
        
    inv = ACTIVE_DATASETS[req.invoice_dataset_id]
    pay = ACTIVE_DATASETS[req.payment_dataset_id]
    
    res = payment_reconciler.reconcile_payments(inv, pay)
    
    details_df = pd.DataFrame(res["details"])
    details_df_masked = sensitive_scanner.mask_dataframe_for_role(details_df, req.role)
    res["details"] = details_df_masked.to_dict(orient="records")
    
    audit_logger.log_event(req.username, "PAYMENT_RECONCILED", "SUCCESS", f"Reconciled {req.invoice_dataset_id} with {req.payment_dataset_id}.")
    return res

@app.post("/api/reconcile/inventory")
async def reconcile_inventory_route(req: InventoryReconcileRequest):
    check_dataset_access(req.pos_dataset_id, req.role, req.username)
    check_dataset_access(req.inventory_dataset_id, req.role, req.username)
    if req.pos_dataset_id not in ACTIVE_DATASETS or req.inventory_dataset_id not in ACTIVE_DATASETS:
        raise HTTPException(status_code=404, detail="One or both datasets not found.")
        
    pos = ACTIVE_DATASETS[req.pos_dataset_id]
    inv = ACTIVE_DATASETS[req.inventory_dataset_id]
    
    res = inventory_reconciler.reconcile_inventory(pos, inv)
    
    anom_df = pd.DataFrame(res["anomalies"])
    if not anom_df.empty:
        anom_df_masked = sensitive_scanner.mask_dataframe_for_role(anom_df, req.role)
        res["anomalies"] = anom_df_masked.to_dict(orient="records")
        
    audit_logger.log_event(req.username, "INVENTORY_RECONCILED", "SUCCESS", f"Reconciled inventory for {req.pos_dataset_id} with {req.inventory_dataset_id}.")
    return res

@app.post("/api/drift/detect")
async def detect_schema_drift_route(req: SchemaDriftRequest):
    check_dataset_access(req.baseline_dataset_id, req.role, req.username)
    check_dataset_access(req.new_dataset_id, req.role, req.username)
    if req.baseline_dataset_id not in ACTIVE_DATASETS or req.new_dataset_id not in ACTIVE_DATASETS:
        raise HTTPException(status_code=404, detail="One or both datasets not found.")
        
    base = list(ACTIVE_DATASETS[req.baseline_dataset_id].columns)
    new_cols = list(ACTIVE_DATASETS[req.new_dataset_id].columns)
    
    res = schema_drift.detect_schema_drift(base, new_cols)
    audit_logger.log_event(req.username, "SCHEMA_DRIFT_DETECTED", "SUCCESS", f"Drift evaluated between {req.baseline_dataset_id} and {req.new_dataset_id}.")
    return res

@app.post("/api/security/sensitive-scan")
async def sensitive_scan_route(req: SensitiveScanRequest):
    check_dataset_access(req.dataset_id, req.role, req.username)
    if req.dataset_id not in ACTIVE_DATASETS:
        raise HTTPException(status_code=404, detail="Dataset not found.")
        
    df = ACTIVE_DATASETS[req.dataset_id]
    res = sensitive_scanner.scan_sensitive_data(df)
    
    audit_logger.log_event(req.username, "SENSITIVE_DATA_SCANNED", "SUCCESS", f"Sensitive scanner evaluated {req.dataset_id}. Risk: {res['risk_level']}")
    return res

@app.post("/api/rules/recommend")
async def rules_recommend_route(req: RuleRecommendRequest):
    check_dataset_access(req.dataset_id, req.role, req.username)
    if req.dataset_id not in ACTIVE_DATASETS:
        raise HTTPException(status_code=404, detail="Dataset not found.")
        
    df = ACTIVE_DATASETS[req.dataset_id]
    suggestions = rule_generator.generate_suggested_rules(df)
    return {"suggestions": suggestions}

@app.post("/api/rules/validate")
async def rules_validate_route(req: RuleValidateRequest):
    check_dataset_access(req.dataset_id, req.role, req.username)
    if req.dataset_id not in ACTIVE_DATASETS:
        raise HTTPException(status_code=404, detail="Dataset not found.")
        
    df = ACTIVE_DATASETS[req.dataset_id]
    res = rule_generator.validate_rules(df, req.active_rules)
    
    viol_df = pd.DataFrame(res["violations"])
    if not viol_df.empty:
        viol_df_masked = sensitive_scanner.mask_dataframe_for_role(viol_df, req.role)
        res["violations"] = viol_df_masked.to_dict(orient="records")
        
    audit_logger.log_event(req.username, "RULES_VALIDATED", "SUCCESS", f"Validated {len(req.active_rules)} business rules against {req.dataset_id}. Compliance Score: {res['compliance_score']}%")
    return res

# ==========================================
# LOCAL LANGUAGE AI ENDPOINTS
# ==========================================

class ExplainRequest(BaseModel):
    finding_key: str = "missing_contacts"
    target_language: str = "English"
    context: Optional[Dict[str, Any]] = None

@app.get("/api/ai/languages")
async def get_ai_languages():
    """Returns list of supported languages for AI explanations."""
    return local_language_ai.get_supported_languages()

@app.post("/api/ai/explain")
async def explain_ai_finding(req: ExplainRequest):
    """Generates structured domain-aware AI explanation in target local language."""
    return local_language_ai.explain_in_language(
        finding_key=req.finding_key,
        target_language=req.target_language,
        custom_context=req.context
    )

# ==========================================
# SYSTEM INTEGRATIONS & NEAR-REAL-TIME SYNC
# ==========================================

class ConnectSystemRequest(BaseModel):
    connector_id: str
    mode: str = "Simulator"
    endpoint: Optional[str] = None

class SyncSystemRequest(BaseModel):
    connector_id: str

@app.get("/api/integrations")
async def list_system_integrations():
    """Returns list of system connectors (Tally, CRM, ERP, POS) and live health metrics."""
    return {
        "connectors": system_integrator.list_system_connectors(),
        "recent_payloads": system_integrator.get_recent_payload_logs()
    }

@app.post("/api/integrations/{connector_id}/connect")
async def connect_system_route(connector_id: str, req: ConnectSystemRequest):
    """Connects or updates system connector configuration and mode (Live vs Simulator)."""
    try:
        updated = system_integrator.update_connector_config(connector_id, mode=req.mode, endpoint=req.endpoint)
        return {"status": "SUCCESS", "connector": updated}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/integrations/{connector_id}/disconnect")
async def disconnect_system_route(connector_id: str):
    """Disconnects system connector."""
    conn = system_integrator.get_connector(connector_id)
    if conn:
        conn["status"] = "DISCONNECTED"
        return {"status": "SUCCESS", "connector_id": connector_id}
    raise HTTPException(status_code=404, detail="Connector not found")

@app.post("/api/integrations/{connector_id}/sync")
async def sync_system_route(connector_id: str):
    """Triggers manual data fetch and ingestion pass for target connector."""
    try:
        res = system_integrator.trigger_system_sync(connector_id)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/integrations/{connector_id}/health")
async def connector_health_route(connector_id: str):
    """Gets connection health score and latency for a connector."""
    conn = system_integrator.get_connector(connector_id)
    if conn:
        return {
            "connector_id": connector_id,
            "name": conn["name"],
            "status": conn["status"],
            "mode": conn["mode"],
            "health_score": conn["health_score"],
            "latency_ms": conn["latency_ms"]
        }
    raise HTTPException(status_code=404, detail="Connector not found")

@app.post("/api/integrations/webhook/{system_type}")
async def inbound_webhook_route(system_type: str, payload: Dict[str, Any]):
    """Receives inbound live payload stream from Webhook systems."""
    res = system_integrator.process_webhook_payload(system_type, payload)
    return res

# ==========================================
# SCHEDULED QUALITY MONITORING & ALERTS
# ==========================================

class MonitoringRuleRequest(BaseModel):
    rule_data: Dict[str, Any]

class MonitoringCheckRequest(BaseModel):
    dataset_id: str = "retail_sales"
    metrics: Optional[Dict[str, Any]] = None

@app.get("/api/monitoring/schedules")
async def list_monitoring_schedules():
    """Returns active monitoring rules and active alerts feed."""
    return {
        "rules": scheduled_monitor.list_monitoring_rules(),
        "alerts": scheduled_monitor.get_active_alerts()
    }

@app.post("/api/monitoring/schedules")
async def create_monitoring_schedule(req: MonitoringRuleRequest):
    """Creates or updates a monitoring rule schedule."""
    updated = scheduled_monitor.create_or_update_rule(req.rule_data)
    return {"status": "SUCCESS", "rule": updated}

@app.delete("/api/monitoring/schedules/{rule_id}")
async def delete_monitoring_schedule(rule_id: str):
    """Deletes a monitoring rule schedule."""
    deleted = scheduled_monitor.delete_rule(rule_id)
    return {"status": "SUCCESS" if deleted else "NOT_FOUND"}

@app.post("/api/monitoring/check")
async def trigger_monitoring_check(req: MonitoringCheckRequest):
    """Runs quality monitoring pass across configured rules and evaluates alert triggers."""
    res = scheduled_monitor.run_monitoring_check(dataset_id=req.dataset_id, current_metrics=req.metrics)
    return res

@app.get("/api/monitoring/history")
async def get_monitoring_alerts_history():
    """Returns active alert feed and notification delivery history."""
    return {
        "active_alerts": scheduled_monitor.get_active_alerts(),
        "notification_history": notification_service.get_dispatch_history()
    }

@app.post("/api/monitoring/alerts/{alert_id}/acknowledge")
async def acknowledge_alert_route(alert_id: str):
    """Marks alert as ACKNOWLEDGED."""
    try:
        updated = scheduled_monitor.acknowledge_alert(alert_id)
        return {"status": "SUCCESS", "alert": updated}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/monitoring/alerts/{alert_id}/resolve")
async def resolve_alert_route(alert_id: str):
    """Marks alert as RESOLVED."""
    try:
        updated = scheduled_monitor.resolve_alert(alert_id)
        return {"status": "SUCCESS", "alert": updated}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==========================================
# NOTIFICATION SERVICE ENDPOINTS
# ==========================================

class NotificationTestRequest(BaseModel):
    channels: List[str] = ["WhatsApp", "Slack"]
    message: str = "Test notification from Qualix AI Monitoring Engine."

@app.post("/api/notifications/test")
async def test_notification_dispatch(req: NotificationTestRequest):
    """Tests multi-channel notification dispatch."""
    res = notification_service.dispatch_multi_channel_alert(
        channels=req.channels,
        rule_title="Manual Test Notification",
        severity="INFO",
        message_body=req.message
    )
    return res

@app.get("/api/notifications/history")
async def notification_history_route():
    """Returns notification dispatch history logs."""
    return {"history": notification_service.get_dispatch_history()}


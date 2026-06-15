from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from passlib.context import CryptContext
import pandas as pd
import joblib
import os
import subprocess
import warnings
import sys
from google import genai
import numpy as np
from groq import Groq

from dotenv import load_dotenv

# 1. INITIALIZATION
load_dotenv()
warnings.filterwarnings('ignore')
from . import models, schemas
from .database import get_db

app = FastAPI(title="Retention OS | Final Project Build")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# 2. ML ASSETS LOADING
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
try:
    model = joblib.load(os.path.join(BASE_DIR, 'churn_model.pkl'))
    scaler = joblib.load(os.path.join(BASE_DIR, 'scaler.pkl'))
    model_columns = joblib.load(os.path.join(BASE_DIR, 'model_columns.pkl'))
    print(f"✅ DEBUG: ML Assets Ready ({len(model_columns)} features)")
except Exception as e:
    print(f"❌ DEBUG: ML Load Error: {e}")

# 3. GEMINI AI CLIENT
# try:
#     gemini_client = genai.Client()
# except Exception:
#     gemini_client = None

# 3. GROQ AI CLIENT (Replaces Gemini to avoid quota limits)
try:
    # This reads 'GROQ_API_KEY' from your .env file
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    print("✅ DEBUG: Groq AI Client Ready")
except Exception as e:
    print(f"❌ DEBUG: Groq Initialization Error: {e}")
    groq_client = None

# ==========================================
# 4. AUTHENTICATION & REGISTRATION
# ==========================================
class LoginRequest(BaseModel):
    email: str
    password: str

# ==========================================
# 4. HARDENED AUTHENTICATION (Master Email)
# ==========================================
@app.post("/api/register")
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == user.email).first()
    if existing: return {"error": "Email already registered."}
    
    # MASTER ADMIN CHECK: Hardcoded secure email
    is_master = True if user.email.strip().lower() == "admin@churn.os" else False
    
    new_user = models.User(
        email=user.email,
        full_name=user.full_name,
        hashed_password=pwd_context.hash(user.password),
        is_active=True,
        is_admin=is_master
    )
    db.add(new_user); db.commit(); db.refresh(new_user)
    return {"message": "Success"}

@app.post("/api/login")
def login_user(req: schemas.LoginRequest, db: Session = Depends(get_db)):
    u = db.query(models.User).filter(models.User.email == req.email).first()
    if not u or not pwd_context.verify(req.password, u.hashed_password):
        return {"error": "Invalid credentials."}
    
    return {
        "user_id": u.id, 
        "full_name": u.full_name,
        "email": u.email, 
        "is_admin": u.is_admin
    }


# ==========================================
# 5. DASHBOARD (FIXES 'UNDEFINED' & BLANK CHARTS)
# ==========================================
@app.get("/api/dashboard")
def get_dashboard(db: Session = Depends(get_db)):
    recs = db.query(models.Customer, models.ChurnPrediction).join(
        models.ChurnPrediction, models.Customer.id == models.ChurnPrediction.customer_id
    ).filter(models.Customer.Status == 'Active').all()

    if not recs: return {"error": "No data"}

    high_risk_count, total_rev_at_risk, total_tenure = 0, 0.0, 0
    risk_tiers, drivers, contracts = {"High Risk": 0, "Medium Risk": 0, "Low Risk": 0}, {}, {}
    critical_list = []

    for c, p in recs:
        total_tenure += c.tenure
        risk_tiers[p.risk_tier] = risk_tiers.get(p.risk_tier, 0) + 1
        contracts[c.Contract] = contracts.get(c.Contract, 0) + 1
        d1 = getattr(p, 'top_driver_1', 'Other')
        drivers[d1] = drivers.get(d1, 0) + 1

        if p.risk_tier == "High Risk":
            high_risk_count += 1
            total_rev_at_risk += c.MonthlyCharges
            critical_list.append({
                "customerID": c.customerID,
                "risk_score": round(p.risk_score * 100, 1),
                "top_driver": d1,
                "monthly_charge": c.MonthlyCharges, # MATCHES dashboard.html line 265
                "contract": c.Contract
            })

    critical_list = sorted(critical_list, key=lambda x: x['risk_score'], reverse=True)[:10]

    return {
        "kpis": {
            "total_active_customers": len(recs),
            "predicted_churn_rate": round((high_risk_count/len(recs))*100, 1),
            "revenue_at_risk": round(total_rev_at_risk, 2),
            "avg_tenure": round(total_tenure/len(recs), 1),
            "high_risk_accounts": high_risk_count
        },
        "charts": { 
            "risk_tiers": risk_tiers, 
            "top_churn_drivers": dict(sorted(drivers.items(), key=lambda x: x[1], reverse=True)[:5]),
            "contract_breakdown": contracts 
        },
        "critical_customers": critical_list
    }

# ==========================================
# 6. SIMULATOR (LOAD-OVERWRITE-TRANSFORM)
# ==========================================
class SimulatorPayload(BaseModel):
    customerID: str
    InternetService: str = None
    OnlineSecurity: str = None
    OnlineBackup: str = None
    DeviceProtection: str = None
    TechSupport: str = None
    StreamingTV: str = None
    StreamingMovies: str = None
    Contract: str = None
    MonthlyCharges: float = None

# ==========================================
# 7. THE SIMULATOR (SYNCHRONIZED SCALING)
# ==========================================

@app.post("/api/simulate")
def simulate(data: SimulatorPayload, db: Session = Depends(get_db)):
    try:
        # A. LOAD: Get baseline from DB
        db_cust = db.query(models.Customer).filter(models.Customer.customerID == data.customerID).first()
        if not db_cust: raise HTTPException(404)
        
        # Capture DB state
        full_data = {col.name: getattr(db_cust, col.name) for col in db_cust.__table__.columns}

        # B. OVERWRITE: Apply changes from UI Sliders/Dropdowns
        ui_updates = data.dict(exclude={'customerID'}, exclude_none=True)
        full_data.update(ui_updates)
        
        # C. TRANSFORM: Build the 48-column vector
        input_dict = {col: 0 for col in model_columns}
        
        # Numeric Mapping
        input_dict['tenure'] = float(full_data.get('tenure', 0))
        input_dict['MonthlyCharges'] = float(full_data.get('MonthlyCharges', 0))
        
        # REFINEMENT 1: Logical TotalCharges Sync
        # Without this, high price slider = low risk (The "New Customer" Paradox)
        input_dict['TotalCharges'] = input_dict['MonthlyCharges'] * input_dict['tenure']

        # Categorical Manual Mapping (Handles _Yes and _No columns)
        for col in model_columns:
            if '_' in col:
                feat, val = col.rsplit('_', 1)
                if str(full_data.get(feat)) == str(val):
                    input_dict[col] = 1

        # Engineered Features (Calculated AFTER the overwrite)
        input_dict['Has_securityBundle'] = 1 if full_data.get('OnlineSecurity') == 'Yes' and full_data.get('OnlineBackup') == 'Yes' else 0
        premium_list = ['OnlineSecurity', 'OnlineBackup', 'DeviceProtection', 'TechSupport', 'StreamingTV', 'StreamingMovies']
        input_dict['Premium_services'] = sum(1 for k in premium_list if full_data.get(k) == 'Yes')

        # D. ALIGN & SCALE
        final_df = pd.DataFrame([input_dict])[model_columns]
        final_scaled = scaler.transform(final_df)
        
        # E. PREDICT
        new_score = model.predict_proba(final_scaled)[0][1]

        # F. LLM STRATEGY (Updated to use Groq)
        changes = [f"{k} changed to {v}" for k, v in ui_updates.items()]
        change_text = ", ".join(changes) if changes else "No plan changes were made."
        
        # Get the top 3 drivers for explainable AI context
        importances = model.feature_importances_
        indices = np.argsort(importances)[-3:][::-1]
        top_3 = [model_columns[i].replace('_', ' ') for i in indices]

        # Default fallback script in case of API issues
        strat = "Standard Protocol: Offer a loyalty discount and 12-month contract extension."
        
        # F. LLM STRATEGY (Updated for Groq Llama 3.3)
        # F. LLM STRATEGY (Corrected for "Expert Offer" Tone)
        if groq_client:
            try:
                risk_val = int(round(float(new_score) * 100))
                drivers_text = ", ".join([str(d) for d in top_3])

                chat_completion = groq_client.chat.completions.create(
                    messages=[
                        {
                            "role": "system", 
                            "content": """You are a Senior Retention Strategist. 
                            Your goal is to provide a specific, high-pressure retention OFFER. 
                            Rules: 
                            1. Be direct. 
                            2. Propose a specific incentive (e.g., 10% discount, free month, or speed upgrade). 
                            3. Use the 'Plan Changes' to justify the offer. 
                            4. Output ONLY the offer script. No intro fluff."""
                        },
                        {
                            "role": "user", 
                            "content": f"Customer {data.customerID} (Risk: {risk_val}%) just added {change_text}. Drivers: {drivers_text}. Propose an expert-level offer to keep them."
                        }
                    ],
                    model="llama-3.3-70b-versatile",
                )
                strat = chat_completion.choices[0].message.content.strip().replace('"', '')
            except Exception as e:
                print(f"⚠️ GROQ FAIL: {e}")

        return {
            "simulated_risk_score": float(new_score), 
            "prescriptive_strategy": strat
        }
    
    except Exception as e:
        # This block catches any errors in the math or database logic
        print(f"❌ CRITICAL DEBUG ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 6. SEARCH & PROFILE (FIXES THE 404 ERROR)
# ==========================================
@app.get("/api/search")
def search(query: str, db: Session = Depends(get_db)):
    res = db.query(models.Customer).filter(models.Customer.customerID.ilike(f"%{query}%")).limit(5).all()
    return [{"id": c.id, "customerID": c.customerID} for c in res]

@app.get("/api/customer/details/{id}")
def get_customer_details(id: str, db: Session = Depends(get_db)):
    """Used by Simulator to load data via Customer ID string (e.g., 5192-EBGOV)"""
    res = db.query(models.Customer).filter(models.Customer.customerID == id).first()
    if not res: raise HTTPException(status_code=404, detail="Customer not found")
    return {col.name: getattr(res, col.name) for col in res.__table__.columns}

@app.get("/api/customer/{id}")
def get_profile(id: int, db: Session = Depends(get_db)):
    """Used by Dashboard and Search results via Integer ID"""
    res = db.query(models.Customer, models.ChurnPrediction).join(models.ChurnPrediction).filter(models.Customer.id == id).first()
    if not res: raise HTTPException(404)
    c, p = res
    return {
        "profile": {col.name: getattr(c, col.name) for col in c.__table__.columns},
        "prediction": {
            "risk_score": p.risk_score, "risk_tier": p.risk_tier, 
            "top_driver_1": getattr(p, 'top_driver_1', '--'),
            "top_driver_2": getattr(p, 'top_driver_2', '--'),
            "top_driver_3": "--"
        }
    }

# ==========================================
# ADMIN MANAGEMENT
# ==========================================
@app.get("/api/admin/users")
def get_all_users(db: Session = Depends(get_db)):
    users = db.query(models.User).all()
    return [{"id": u.id, "email": u.email, "full_name": u.full_name, "is_admin": u.is_admin} for u in users]

# ==========================================
# 8. HIERARCHICAL ADMIN MANAGEMENT
# ==========================================
@app.post("/api/admin/promote/{target_id}")
def promote_user(target_id: int, admin_id: int, db: Session = Depends(get_db)):
    actor = db.query(models.User).filter(models.User.id == admin_id).first()
    if not actor or not actor.is_admin:
        raise HTTPException(status_code=403, detail="Unauthorized")

    target = db.query(models.User).filter(models.User.id == target_id).first()
    if target:
        target.is_admin = True
        db.commit()
    return {"message": f"User {target.full_name} promoted."}

@app.post("/api/admin/demote/{target_id}")
def demote_user(target_id: int, admin_id: int, db: Session = Depends(get_db)):
    actor = db.query(models.User).filter(models.User.id == admin_id).first()
    target = db.query(models.User).filter(models.User.id == target_id).first()
    
    if not actor or not actor.is_admin:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # MASTER PROTECTION: Prevents demoting the primary admin email
    if target.email.lower() == "admin@churn.os":
        return {"error": "Master Admin account cannot be demoted."}

    target.is_admin = False
    db.commit()
    return {"message": f"User {target.full_name} demoted to Staff."}

# UPDATED: Professional Pipeline Endpoint
@app.post("/api/admin/retrain")
def update_pipeline():
    # Define path to your XGBoost retraining script
    pipeline_path = os.path.join(BASE_DIR, "run_pipeline.py")
    
    # Verify script existence before attempting execution
    if not os.path.exists(pipeline_path):
        return {"error": "Pipeline script 'run_pipeline.py' not found in project root."}, 404

    try:
        # sys.executable ensures we use your project's 'venv'
        # Popen runs this in the background so the UI doesn't hang
        process = subprocess.Popen(
            [sys.executable, pipeline_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Return a success message that the frontend 'Toast' will display
        return {
            "status": "success", 
            "message": "Update Pipeline: Update started in background."
        }
        
    except Exception as e:
        print(f"❌ PIPELINE FAILURE: {str(e)}")
        return {"error": f"Failed to initialize pipeline: {str(e)}"}, 500
    
@app.get("/api/admin/pipeline-status")
def get_pipeline_status():
    status_path = os.path.join(BASE_DIR, "pipeline_status.txt")
    if not os.path.exists(status_path):
        return {"status": "IDLE", "message": "No pipeline runs recorded."}
    
    try:
        with open(status_path, "r") as f:
            content = f.read().strip()
            # If the file is being written but not finished, handle the split carefully
            parts = content.split("|")
            if len(parts) < 3:
                return {"status": "PROCESSING", "message": "Updating status file..."}
                
            return {
                "status": parts[0],
                "timestamp": parts[1],
                "message": parts[2]
            }
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}
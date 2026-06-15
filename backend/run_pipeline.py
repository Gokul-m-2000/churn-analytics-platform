import pandas as pd
import joblib
import shap
import os
import warnings
from datetime import datetime
from sqlalchemy.orm import Session

# Import your database connections
from app.database import SessionLocal
from app import models

# Suppress warnings for a clean terminal
warnings.filterwarnings('ignore')

# 1. SETUP: Locate the Machine Learning files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, 'churn_model.pkl')
SCALER_PATH = os.path.join(BASE_DIR, 'scaler.pkl')
COLUMNS_PATH = os.path.join(BASE_DIR, 'model_columns.pkl')

print("🧠 Loading Machine Learning Models...")
model = joblib.load(MODEL_PATH)
scaler = joblib.load(SCALER_PATH)
model_columns = joblib.load(COLUMNS_PATH)

print("🔍 Initializing SHAP Explainer (This takes a few seconds)...")
explainer = shap.TreeExplainer(model)

def run_etl_pipeline():
    print("🔌 Connecting to MariaDB...")
    db: Session = SessionLocal()
    
    try:
        # ==========================================
        # PHASE 1: EXTRACT
        # ==========================================
        print("📥 Extracting active customer data...")
        # Only pull people who are still paying us!
        customers = db.query(models.Customer).filter(models.Customer.Status == "Active").all()
        if not customers:
            print("❌ No customers found in database.")
            return

        # Convert SQL data to Pandas DataFrame instantly
        data = [{c.name: getattr(cust, c.name) for c in cust.__table__.columns} for cust in customers]
        raw_df = pd.DataFrame(data)
        
        # Save the database IDs so we know who to attach predictions to
        id_mapping = raw_df[['id']].copy()

        # ==========================================
        # PHASE 2: TRANSFORM (Feature Engineering)
        # ==========================================
        print("⚙️ Transforming data (Applying business logic)...")
        
        # Drop columns the ML model doesn't need (Notice we drop 'Status' now!)
        df_ml = raw_df.drop(columns=['id', 'customerID', 'Status'], errors='ignore')
        
        # 1. Recreate your custom business features from your Jupyter Notebook
        df_ml['Has_securityBundle'] = ((df_ml['OnlineSecurity'] == 'Yes') & (df_ml['OnlineBackup'] == 'Yes')).astype(int)
        
        premium_cols = ['OnlineSecurity', 'OnlineBackup', 'DeviceProtection', 'TechSupport', 'StreamingTV', 'StreamingMovies']
        df_ml['Premium_services'] = (df_ml[premium_cols] == "Yes").sum(axis=1)

        # 2. Convert text to 0s and 1s
        df_encoded = pd.get_dummies(df_ml, dtype=int)
        
        # 3. Align columns EXACTLY to how XGBoost was trained
        df_aligned = df_encoded.reindex(columns=model_columns, fill_value=0)
        
        # 4. Mathematical Scaling
        scaled_data = scaler.transform(df_aligned)
        df_scaled = pd.DataFrame(scaled_data, columns=df_aligned.columns)

        # ==========================================
        # PHASE 3: PREDICT & EXPLAIN
        # ==========================================
        print("🎯 Running XGBoost Predictions...")
        probabilities = model.predict_proba(df_scaled)[:, 1] 
        
        print("📊 Calculating SHAP values for Explainable AI...")
        shap_values = explainer.shap_values(df_scaled)

        # ==========================================
        # PHASE 4: LOAD (Save to Database)
        # ==========================================
        print(f"💾 Saving {len(raw_df)} predictions to the AI Vault...")
        
        new_count = 0
        update_count = 0

        for index, row in id_mapping.iterrows():
            db_id = row['id']
            risk_score = float(probabilities[index])
            
            # Categorize the Risk
            if risk_score > 0.70:
                tier = "High Risk"
            elif risk_score > 0.40:
                tier = "Medium Risk"
            else:
                tier = "Low Risk"
                
            # Extract the top 2 SHAP drivers for this specific person
            customer_shap = shap_values[index]
            feature_impacts = list(zip(df_scaled.columns, customer_shap))
            feature_impacts.sort(key=lambda x: x[1], reverse=True) 
            
            top_1 = feature_impacts[0][0]
            top_2 = feature_impacts[1][0]

            # Check if this customer already has a prediction in the vault
            existing_pred = db.query(models.ChurnPrediction).filter(models.ChurnPrediction.customer_id == db_id).first()
            
            if existing_pred:
                # Update existing score
                existing_pred.risk_score = risk_score
                existing_pred.risk_tier = tier
                existing_pred.top_driver_1 = top_1
                existing_pred.top_driver_2 = top_2
                update_count += 1
            else:
                # Create brand new score
                new_pred = models.ChurnPrediction(
                    customer_id=db_id,
                    risk_score=risk_score,
                    risk_tier=tier,
                    top_driver_1=top_1,
                    top_driver_2=top_2
                )
                db.add(new_pred)
                new_count += 1

        # === PHASE 5: UI SYNC (Add this right after db.commit) ===
        db.commit()
        
        # Define the status file path in your project root
        status_path = os.path.join(BASE_DIR, "pipeline_status.txt")
        
        with open(status_path, "w") as f:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # Format: STATUS | TIMESTAMP | MESSAGE
            f.write(f"SUCCESS|{now}|{new_count + update_count} Customers Processed")

        print(f"\n✅ PIPELINE SUCCESS! Status logged at {now}")

    except Exception as e:
        # Log the failure so the Admin UI doesn't spin forever
        status_path = os.path.join(BASE_DIR, "pipeline_status.txt")
        with open(status_path, "w") as f:
            f.write(f"FAILED|{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}|Error: {str(e)}")
            
        print(f"\n❌ PIPELINE FAILED: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run_etl_pipeline()
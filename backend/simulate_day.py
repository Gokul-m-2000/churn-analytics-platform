import pandas as pd
import random
import os
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app import models

def simulate_business_day():
    db: Session = SessionLocal()
    try:
        print("🌅 Starting Daily Business Simulation...")

        # 1. Get all currently active customers
        active_customers = db.query(models.Customer).filter(models.Customer.Status == "Active").all()
        
        if len(active_customers) < 10:
            print("❌ Not enough customers to simulate.")
            return

        # ==========================================
        # ACTION 1: PRICE HIKES & DOWNGRADES
        # ==========================================
        print("📉 Simulating 5 customers downgrading to Month-to-Month and getting price hikes...")
        to_modify = random.sample(active_customers, 5)
        for cust in to_modify:
            cust.Contract = "Month-to-month"
            cust.MonthlyCharges += 20.0  # Jack up the price
            cust.TotalCharges += cust.MonthlyCharges
        
        # ==========================================
        # ACTION 2: CANCELLATIONS (CHURN)
        # ==========================================
        # Pick 3 DIFFERENT customers who decided to leave today
        remaining_actives = [c for c in active_customers if c not in to_modify]
        print("❌ Simulating 3 customers cancelling their service today...")
        to_cancel = random.sample(remaining_actives, 3)
        for cust in to_cancel:
            cust.Status = "Cancelled" # They drop off the active list!

        # ==========================================
        # ACTION 3: NEW SIGNUPS
        # ==========================================
        print("🎉 Simulating 5 brand new customers signing up...")
        PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        csv_path = os.path.join(PROJECT_ROOT, 'data', 'WA_Fn-UseC_-Telco-Customer-Churn.csv')
        df = pd.read_csv(csv_path)
        df['TotalCharges'] = pd.to_numeric(df['TotalCharges'], errors='coerce').fillna(0.0)

        # Get list of existing IDs in DB to avoid duplicates
        existing_ids = [c.customerID for c in db.query(models.Customer).all()]
        
        # Filter CSV for people NOT in the database yet and grab the first 5
        new_prospects = df[~df['customerID'].isin(existing_ids)].head(5)

        new_customers_to_insert = []
        for _, row in new_prospects.iterrows():
            new_cust = models.Customer(
                customerID=row['customerID'],
                gender=row['gender'],
                SeniorCitizen=row['SeniorCitizen'],
                Partner=row['Partner'],
                Dependents=row['Dependents'],
                tenure=0, # Brand new, 0 months tenure!
                PhoneService=row['PhoneService'],
                MultipleLines=row['MultipleLines'],
                InternetService=row['InternetService'],
                OnlineSecurity=row['OnlineSecurity'],
                OnlineBackup=row['OnlineBackup'],
                DeviceProtection=row['DeviceProtection'],
                TechSupport=row['TechSupport'],
                StreamingTV=row['StreamingTV'],
                StreamingMovies=row['StreamingMovies'],
                Contract=row['Contract'],
                PaperlessBilling=row['PaperlessBilling'],
                PaymentMethod=row['PaymentMethod'],
                MonthlyCharges=float(row['MonthlyCharges']),
                TotalCharges=float(row['MonthlyCharges']), # First month bill
                Status="Active" 
            )
            new_customers_to_insert.append(new_cust)
        
        db.bulk_save_objects(new_customers_to_insert)
        
        # Save all changes to MariaDB
        db.commit()
        print("\n✅ SIMULATION COMPLETE! The live database has been updated.")
        print("Next step: Run 'python run_pipeline.py' to see how the AI reacts to these changes!")

    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    simulate_business_day()
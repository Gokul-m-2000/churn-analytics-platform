import pandas as pd
import os
from sqlalchemy.orm import Session

# Import engine as well as SessionLocal
from app.database import SessionLocal, engine
from app import models

def reset_and_seed_database():
    db: Session = SessionLocal()
    
    try:
        print("🏗️ Rebuilding database tables...")
        # 1. DROP the old tables completely (Destroys the old schema with 'Churn')
        models.ChurnPrediction.__table__.drop(engine, checkfirst=True)
        models.Customer.__table__.drop(engine, checkfirst=True)
        
        # 2. RECREATE the tables using the new blueprint (Creates the 'Status' column)
        models.Base.metadata.create_all(engine)
        print("✅ Tables rebuilt successfully!")
        
        # 3. Load the CSV 
        PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        csv_path = os.path.join(PROJECT_ROOT, 'data', 'WA_Fn-UseC_-Telco-Customer-Churn.csv')
        
        print(f"📖 Reading dataset from {csv_path}...")
        df = pd.read_csv(csv_path)
        
        # Convert TotalCharges safely
        df['TotalCharges'] = pd.to_numeric(df['TotalCharges'], errors='coerce').fillna(0.0)
        
        # Take ONLY the first 1,000 rows
        df_starting_state = df.head(1000)
        
        print(f"🌱 Seeding MariaDB with {len(df_starting_state)} starting customers...")
        
        customers_to_insert = []
        for _, row in df_starting_state.iterrows():
            customer = models.Customer(
                customerID=row['customerID'],
                gender=row['gender'],
                SeniorCitizen=row['SeniorCitizen'],
                Partner=row['Partner'],
                Dependents=row['Dependents'],
                tenure=row['tenure'],
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
                TotalCharges=float(row['TotalCharges']),
                Status="Active" # Our new column!
            )
            customers_to_insert.append(customer)
            
        db.bulk_save_objects(customers_to_insert)
        db.commit()
        
        print("✅ DATABASE RESET SUCCESSFUL!")
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    reset_and_seed_database()
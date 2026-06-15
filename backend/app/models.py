from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

# ==========================================
# TABLE 1: THE EMPLOYEES (Your existing auth system)
# ==========================================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    full_name = Column(String(255)) 
    hashed_password = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)

# ==========================================
# TABLE 2: THE REAL WORLD (Raw CRM Data)
# ==========================================
class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    customerID = Column(String(255), unique=True, index=True) 
    gender = Column(String(50)) 
    SeniorCitizen = Column(Integer)
    Partner = Column(String(50))
    Dependents = Column(String(50))
    tenure = Column(Integer)
    PhoneService = Column(String(50))
    MultipleLines = Column(String(50))
    InternetService = Column(String(50))
    OnlineSecurity = Column(String(50))
    OnlineBackup = Column(String(50))
    DeviceProtection = Column(String(50))
    TechSupport = Column(String(50))
    StreamingTV = Column(String(50))
    StreamingMovies = Column(String(50))
    Contract = Column(String(50))
    PaperlessBilling = Column(String(50))
    PaymentMethod = Column(String(50))
    MonthlyCharges = Column(Float)
    TotalCharges = Column(Float)
    
    # Live Account Status ("Active" or "Cancelled")
    Status = Column(String(50), default="Active")

    # Link to the AI Predictions table (One-to-One relationship)
    prediction = relationship("ChurnPrediction", back_populates="customer", uselist=False)

# ==========================================
# TABLE 3: THE ML VAULT (AI Predictions)
# ==========================================
class ChurnPrediction(Base):
    __tablename__ = "churn_predictions"

    id = Column(Integer, primary_key=True, index=True)
    
    # Connects exactly to one customer row
    customer_id = Column(Integer, ForeignKey("customers.id"), unique=True)
    
    # AI Outputs
    risk_score = Column(Float) # e.g., 0.85
    risk_tier = Column(String(50)) # "High Risk", "Medium Risk", "Low Risk"
    
    # Explainable AI (SHAP)
    top_driver_1 = Column(String(255)) 
    top_driver_2 = Column(String(255)) 
    
    # Tracks when the pipeline last ran
    last_updated = Column(DateTime, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="prediction")
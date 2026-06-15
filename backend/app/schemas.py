from pydantic import BaseModel, EmailStr
from typing import Optional

# --- USER SCHEMAS (For Security) ---
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str # This is only for the registration 'form'

class LoginRequest(BaseModel):  # This is the specific one missing!
    email: str
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True # Allows Pydantic to read data from SQLAlchemy models

# --- CUSTOMER SCHEMAS (For Data Pipeline) ---
class CustomerBase(BaseModel):
    """
    This defines the 'Shape' of a customer record.
    It matches your 21 columns from the CSV.
    """
    customerID: str
    gender: str
    SeniorCitizen: int
    Partner: str
    Dependents: str
    tenure: int
    PhoneService: str
    MultipleLines: str
    InternetService: str
    OnlineSecurity: str
    OnlineBackup: str
    DeviceProtection: str
    TechSupport: str
    StreamingTV: str
    StreamingMovies: str
    Contract: str
    PaperlessBilling: str
    PaymentMethod: str
    MonthlyCharges: float
    TotalCharges: float
    Status: str

class CustomerResponse(CustomerBase):
    id: int # The internal database ID

    class Config:
        from_attributes = True

# --- PREDICTION SCHEMAS (The AI Output) ---
class PredictionResult(BaseModel):
    customer_id: str
    prediction: int  # 1 for Churn, 0 for Stay
    probability: float
    risk_level: str
    recommendation: str
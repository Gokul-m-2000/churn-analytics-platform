from app.database import SessionLocal
from app.models import User
from passlib.context import CryptContext

# 1. Set up the enterprise password hasher
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_master_admin():
    print("Connecting to MariaDB...")
    db = SessionLocal()

    # 2. Check if you already ran this script
    existing_admin = db.query(User).filter(User.email == "admin@churn.com").first()
    if existing_admin:
        print("Security Alert: admin@churn.com already exists in the database.")
        db.close()
        return

    print("Forging Master Key and encrypting password...")
    
    # 3. Create the VIP Account (You can change "admin123" to your preferred password)
    hashed_password = pwd_context.hash("admin123") 
    
    new_admin = User(
        email="admin@churn.com",
        full_name="Gokul (Master Admin)",
        hashed_password=hashed_password,
        is_admin=True # <-- THE MASTER KEY
    )
    
    # 4. Inject directly into the database
    db.add(new_admin)
    db.commit()
    print("Success! Enterprise Master Admin securely injected into the database.")
    db.close()

if __name__ == "__main__":
    create_master_admin()
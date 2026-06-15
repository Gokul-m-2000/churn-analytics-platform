from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


# THE NEW ENTERPRISE MARIADB CONNECTION
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:@127.0.0.1:3306/churn_db"

# Notice we removed "check_same_thread" because MariaDB handles multiple connections naturally
engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
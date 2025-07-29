from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.settings import settings

# DB URL 구성
BASE_URL = f"mysql+pymysql://{settings.db_user}:{settings.db_password}@{settings.db_endpoint}:{settings.db_port}/"
DATABASE_URL = f"{BASE_URL}{settings.db_name}?charset=utf8mb4"

# SQLAlchemy 엔진 및 세션
engine = create_engine(DATABASE_URL, 
pool_size=15,
max_overflow=20,
pool_timeout=30,
pool_recycle=1800,
pool_pre_ping=True,
echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_engine():
    return engine

def get_session():
    return SessionLocal()

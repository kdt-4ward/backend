from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from core.settings import settings

DB_NAME = "chat"

# Base URL: DB 이름 없는 상태
BASE_URL = f"mysql+pymysql://{settings.db_user}:{settings.db_password}@{settings.db_endpoint}:{settings.db_port}/"
# Full URL: DB 이름까지 포함
DATABASE_URL = f"{BASE_URL}{DB_NAME}"

# 엔진과 세션
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine)

def get_engine():
    return engine

def get_session():
    return SessionLocal()
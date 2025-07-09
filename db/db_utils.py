from sqlalchemy import create_engine, text
from core.settings import settings

DB_NAME = "chat"
BASE_URL = f"mysql+pymysql://{settings.db_user}:{settings.db_password}@{settings.db_endpoint}:{settings.db_port}/"

def create_database_if_not_exists():
    engine = create_engine(BASE_URL, echo=True)
    with engine.connect() as conn:
        conn.execute(text(f"""
            CREATE DATABASE IF NOT EXISTS {DB_NAME}
            CHARACTER SET utf8mb4
            COLLATE utf8mb4_unicode_ci
        """))
        conn.commit()
        print(f"✅ 데이터베이스 '{DB_NAME}' 생성 확인 완료")

def drop_database():
    engine = create_engine(BASE_URL, echo=True)
    with engine.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {DB_NAME}"))
        conn.commit()
        print(f"🗑 데이터베이스 '{DB_NAME}' 삭제 완료")

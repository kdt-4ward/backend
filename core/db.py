from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from backend.core.settings import settings

BASE_URL = f"mysql+pymysql://{settings.db_user}:{settings.db_password}@{settings.db_endpoint}:{settings.db_port}/"

DB_NAME = "chat"
# 데이터베이스가 없을 경우 생성
def create_database_if_not_exists():
    temp_engine = create_engine(BASE_URL, echo=True)
    with temp_engine.connect() as conn:
        conn.execute(text(f"""
            CREATE DATABASE IF NOT EXISTS {DB_NAME}
            CHARACTER SET utf8mb4
            COLLATE utf8mb4_unicode_ci
        """))
        conn.commit()

create_database_if_not_exists()

# 생성 후 연결용 URL
DATABASE_URL = f"{BASE_URL}{DB_NAME}"
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine)

def get_engine():
    return engine




# # 삭제
# def drop_database():
#     engine = create_engine(BASE_URL, echo=True)
#     with engine.connect() as conn:
#         conn.execute(text(f"DROP DATABASE IF EXISTS {DB_NAME}"))
#         conn.commit()
#         print(f"✅ 데이터베이스 '{DB_NAME}' 삭제 완료")

# drop_database()
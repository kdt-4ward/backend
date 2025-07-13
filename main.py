from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import ai_chat, ws_chat, history, auth
from models.db_tables import Base
from db.db import engine
from core.settings import settings
from db.db_utils import create_database_if_not_exists
from test_data.seed_data import insert_test_data_to_db
import logging
import sys

log_format = "[%(asctime)s][%(levelname)s][%(name)s] %(message)s"
date_format = "%Y-%m-%d %H:%M:%S"

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter(fmt=log_format, datefmt=date_format))

logging.basicConfig(
    level=logging.INFO,
    handlers=[console_handler]
)

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug
)

@app.get("/")
def health_check():
    return {"status": "ok"}

def startup():
    create_database_if_not_exists()

    ## test data 삽입 / 배포시 삭제
    insert_test_data_to_db()

    # 추가로 테이블 생성, 마이그레이션 등

startup()

# DB 테이블 생성
Base.metadata.create_all(bind=engine)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(ai_chat.router)
app.include_router(ws_chat.router)
app.include_router(history.router)  # 선택
app.include_router(auth.router)
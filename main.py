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

@app.on_event("startup")
async def on_startup():
    create_database_if_not_exists()
    ## =============== 배포시 삭제 ==================== ##
    ## test data 삽입
    insert_test_data_to_db()

    # 유저 성향 분석 (비동기)
    from jobs.analysis_personality import run_trait_summary_for_all_users
    import asyncio
    try:
        await run_trait_summary_for_all_users()
        logging.info("유저 성향 분석/요약 완료")
    except Exception as e:
        logging.error(f"유저 성향 분석 실패: {e}")

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
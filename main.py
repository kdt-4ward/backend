from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import router as api_router
from db.db_tables import Base
from db.db import engine
from core.settings import settings
from db.db_utils import create_database_if_not_exists
from test_data.seed_data import insert_test_data_to_db
from jobs.daily_analysis import test_weekly_couplechat_analysis_from_start_date
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


create_database_if_not_exists()
@app.on_event("startup")
async def on_startup():
    create_database_if_not_exists()
    # =============== 배포시 삭제 ==================== ##
    # test data 삽입
    # insert_test_data_to_db()

    # # 유저 성향 분석 (비동기)

    # from jobs.analysis_personality import run_trait_summary_for_all_users
    # import asyncio
    # try:
    #     await run_trait_summary_for_all_users()
    #     logging.info("유저 성향 분석/요약 완료")
    # except Exception as e:
    #     logging.error(f"유저 성향 분석 실패: {e}")
    # try:
    #     await test_weekly_couplechat_analysis_from_start_date()
    #     logging.info("유저 couple chat 분석 완료")
    # except Exception as e:
    #     logging.error(f"유저 couple chat 분석 실패: {e}")

    # from jobs.weekly_analysis import test_run_seven_days_analysis

    # # try:
    # await test_run_seven_days_analysis()
    # #     logging.info("주간 분석 완료")
    # # except Exception as e:
    #     logging.error(f"주간 분석 실패: {e}")
    

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
app.include_router(api_router)

# 임시 테스트용 로컬 파일 등록
# AWS S3에 연결 시 삭제
# from fastapi.staticfiles import StaticFiles
# from routers import upload  
# app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")  # 정적 파일 서빙
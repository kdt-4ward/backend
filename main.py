from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import router as api_router
from db.db_tables import Base
from db.db import engine
from core.settings import settings
from services.scheduler_advanced import advanced_scheduler
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

# @app.on_event("startup")
# async def startup_event():
#     """애플리케이션 시작 시 스케줄러 실행"""
#     advanced_scheduler.start()

# @app.on_event("shutdown")
# async def shutdown_event():
#     """애플리케이션 종료 시 스케줄러 중지"""
#     advanced_scheduler.shutdown()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(api_router)

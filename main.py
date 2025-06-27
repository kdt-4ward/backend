from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import ai_chat, ws_chat, history
from backend.models.db_models import Base
from backend.core.db import engine
from backend.core.settings import settings

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug
)

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
# app.include_router(ai_chat.router)
# app.include_router(ws_chat.router)
# app.include_router(history.router)  # 선택
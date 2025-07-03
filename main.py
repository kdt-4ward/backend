from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import ai_chat, ws_chat, history, auth
from models.db_models import Base
from core.db import engine
from core.settings import settings
from core.db_utils import create_database_if_not_exists

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug
)

@app.get("/")
def health_check():
    return {"status": "ok"}

def startup():
    create_database_if_not_exists()
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


# from tests.data.preprocessed.insert_db import insert_data
# insert_data()
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import ai_chat, ws_chat, history, auth, post, comment, emotion_log
from models.db_models import Base
from db.db import engine
from core.settings import settings
from db.db_utils import create_database_if_not_exists

# 임시 테스트용 staticfiles
from fastapi.staticfiles import StaticFiles
from routers import upload  

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
app.include_router(post.router)
app.include_router(comment.router)
app.include_router(upload.router)
app.include_router(emotion_log.router)
# 임시 테스트용 로컬 파일 등록
# AWS S3에 연결 시 삭제
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")  # 정적 파일 서빙

# from tests.data.preprocessed.insert_db import insert_data
# insert_data()
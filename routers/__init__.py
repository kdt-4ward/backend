# routers/__init__.py
from fastapi import APIRouter
from .ai_chat import router as ai_chat_router
from .ws_chat import router as ws_chat_router
from .auth import router as auth_router
from .history import router as history_router
from .post import router as post_router
from .emotion_log import router as emotion_router
from .upload import router as upload_router
from .comment import router as comment_router

router = APIRouter()
router.include_router(ai_chat_router, prefix="/chat", tags=["AI Chat"])
router.include_router(ws_chat_router, prefix="/ws", tags=["WebSocket"])
router.include_router(auth_router, prefix="/auth", tags=["Auth"])
router.include_router(history_router, prefix="/history", tags=["History"])
router.include_router(post_router, prefix="/post", tags=["Post"])
router.include_router(emotion_router, prefix="/emotion", tags=["Emotion"])
router.include_router(upload_router, tags=["Upload"])
router.include_router(comment_router, tags=["Comment"])
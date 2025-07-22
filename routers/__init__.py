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
from .survey import router as survey_router
from .couple import router as couple_router
from .analysis import router as analysis_router
from .recommendation import router as recommendation_router

router = APIRouter()
router.include_router(ai_chat_router, prefix="/chat", tags=["AI Chat"])
router.include_router(ws_chat_router, prefix="/ws", tags=["WebSocket"])
router.include_router(auth_router, prefix="/auth", tags=["Auth"])
router.include_router(history_router, prefix="/history", tags=["History"])
router.include_router(post_router, prefix="/post", tags=["Post"])
router.include_router(emotion_router, tags=["Emotion"])
router.include_router(upload_router, tags=["Upload"])
router.include_router(comment_router, tags=["Comment"])
router.include_router(survey_router, prefix="/survey", tags=["Survey"])
router.include_router(couple_router, prefix="/couple", tags=["Couple"])
router.include_router(analysis_router, prefix="/analysis", tags=["Analysis"])
router.include_router(recommendation_router, prefix="/recommendations", tags=["Recommendation"])
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.db_tables import EmotionLog
from models.schema import EmotionLogRequest, EmotionLogResponse
from core.dependencies import get_db_session
from core.redis_v2.redis import redis_client
from datetime import datetime
from typing import List
import json

router = APIRouter(prefix="/emotion")

# POST: 감정 기록 저장
@router.post("/log")
def save_emotion_log(req: EmotionLogRequest, db: Session = Depends(get_db_session)):
    try:
        log = EmotionLog(
            user_id=req.user_id,
            couple_id=req.couple_id,
            emotion=req.emotion,
            detail_emotions=json.dumps(req.detail_emotions or []),
            memo=req.memo,
            recorded_at=req.recorded_at or datetime.utcnow()
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        redis_client.delete(f"emotion_logs:{req.user_id}")
        return {"message": "감정 기록 저장 완료", "log_id": log.emotion_id}
    except Exception as e:
        print("ERROR:", e)
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")

# GET: 사용자 감정 기록 전체 조회
@router.get("/log/{user_id}", response_model=List[EmotionLogResponse])
def get_emotion_logs(user_id: str, db: Session = Depends(get_db_session)):
    cache_key = f"emotion_logs:{user_id}"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    logs = db.query(EmotionLog).filter_by(user_id=user_id).order_by(EmotionLog.recorded_at.desc()).all()

    result = []
    for log in logs:
        result.append({
            "emotion_id": log.emotion_id,
            "user_id": log.user_id,
            "couple_id": log.couple_id,
            "emotion": log.emotion,
            "detail_emotions": json.loads(log.detail_emotions or "[]"),
            "memo": log.memo,
            "recorded_at": log.recorded_at.isoformat() if log.recorded_at else None,   # <-- 수정!
            "updated_at": log.updated_at.isoformat() if log.updated_at else None,       # <-- 수정!
        })

    redis_client.set(cache_key, json.dumps(result, ensure_ascii=False), ex=1800)
    return result

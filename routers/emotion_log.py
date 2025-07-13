from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.db_tables import EmotionLog
from models.schema import EmotionLogRequest
from core.dependencies import get_db_session
from core.redis import redis_client
from datetime import datetime
import json

router = APIRouter(prefix="/emotion")

@router.post("/log")
def save_emotion_log(req: EmotionLogRequest, db: Session = Depends(get_db_session)):
    log = EmotionLog(
        user_id=req.user_id,
        emotion=req.emotion,
        memo=req.memo,
        date=datetime.utcnow()
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    redis_client.delete(f"emotion_logs:{req.user_id}")
    return {"message": "감정 기록 저장 완료", "log_id": log.id}

@router.get("/log/{user_id}")
def get_emotion_logs(user_id: str, db: Session = Depends(get_db_session)):
    cache_key = f"emotion_logs:{user_id}"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    logs = db.query(EmotionLog).filter_by(user_id=user_id).order_by(EmotionLog.date.desc()).all()
    result = [{"id": l.id, "emotion": l.emotion, "memo": l.memo, "date": l.date.isoformat()} for l in logs]
    redis_client.set(cache_key, json.dumps(result, ensure_ascii=False), ex=1800)
    return result

@router.delete("/log/{log_id}")
def delete_emotion_log(log_id: int, db: Session = Depends(get_db_session)):
    log = db.query(EmotionLog).filter_by(id=log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="감정 기록을 찾을 수 없습니다.")
    db.delete(log)
    db.commit()

    redis_client.delete(f"emotion_logs:{log.user_id}")
    return {"message": "감정 기록 삭제 완료"}

from fastapi import APIRouter
from db.db import SessionLocal
from models.db_tables import Message

router = APIRouter()

@router.get("/history/{couple_id}")
async def get_history(couple_id: str):
    db = SessionLocal()
    msgs = db.query(Message).filter_by(couple_id=couple_id).order_by(Message.created_at).all()
    db.close()
    return [
        {
            "chat_id": m.chat_id,
            "couple_id": m.couple_id,
            "user_id": m.user_id,
            "content": m.content,
            "image_url": m.image_url,
            "has_image": m.has_image,
            "created_at": m.created_at.isoformat(),
            "deleted_at": m.deleted_at.isoformat() if m.deleted_at else None
        }
        for m in msgs
    ]
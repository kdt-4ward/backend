from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean, Integer
from datetime import datetime
from .base import Base

class EmotionLog(Base):
    __tablename__ = "emotion_logs"

    emotion_id = Column(Integer, primary_key=True, autoincrement=True)  # PK
    user_id = Column(String(255), ForeignKey("users.user_id"), nullable=False)
    couple_id = Column(String(255), ForeignKey("couples.couple_id"), nullable=True)

    emotion = Column(String(100), nullable=False)                       # 기본 감정 (캐릭터 ID 등)
    detail_emotions = Column(Text, nullable=True)                       # 세부 감정들 (JSON 문자열 형태)
    memo = Column(Text, nullable=True)   # <-- ✅ 메모 추가!

    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow)  # 기록 날짜
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 수정 날짜
    deleted_at = Column(DateTime, nullable=True)

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

import enum
from sqlalchemy import Enum

class GenderEnum(enum.Enum):
    male = "male"
    female = "female"
    other = "other"

# ================== 채팅 메시지 ===================
class Message(Base):
    __tablename__ = "messages"

    chat_id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(String(255), nullable=False)
    user_id = Column(String(255), nullable=False)
    content = Column(Text)
    image_url = Column(Text)
    has_image = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    is_delivered = Column(Boolean, default=False)
    embed_index = Column(Integer, nullable=True)  # <--- 추가!

# ================== AI 메시지(챗봇) =================
class AIMessage(Base):
    __tablename__ = "ai_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False)
    couple_id = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    embed_index = Column(Integer, nullable=True)  # <--- 추가!

# ================== 페르소나 설정 ==================
class PersonaConfig(Base):
    __tablename__ = "persona_config"

    couple_id = Column(String(255), primary_key=True, index=True)
    persona_name = Column(String(255), default="무민")
    updated_at = Column(DateTime, default=datetime.utcnow)

# ================== User 테이블 (예시) ==============
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), unique=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    modified_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    birth = Column(DateTime, nullable=True)
    gender = Column(Enum(GenderEnum), nullable=True)
    # 기타 필요한 필드 추가
# ==================== Couple table =======================
class Couple(Base):
    __tablename__ = "couples"

    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(String(255), nullable=False)
    user_1 = Column(String(255), nullable=False)
    user_2 = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    modified_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
       
# ================ Questionnaire ================
class Questionnaire(Base):
    __tablename__ = "questionnaires"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False)
    answers = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

# ================ EmotionLog ================
class EmotionLog(Base):
    __tablename__ = "emotion_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False)
    emotion = Column(Text)
    date = Column(DateTime, default=datetime.utcnow)
    memo = Column(Text)

# ================ WeeklySolution (분석 결과 저장용, 선택) ================
class WeeklySolution(Base):
    __tablename__ = "weekly_solutions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class AIChatSummary(Base):
    __tablename__ = "ai_chat_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False)
    couple_id = Column(String(255), nullable=False)
    summary = Column(Text, nullable=False)
    emb_id = Column(Integer, nullable=True)  # 벡터 DB 연결 시
    created_at = Column(DateTime, default=datetime.utcnow)
    last_msg_id = Column(Integer, nullable=False)

class CoupleChatSummary(Base):
    __tablename__ = "couple_chat_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(String(255), nullable=False)
    summary = Column(Text, nullable=False)
    emb_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


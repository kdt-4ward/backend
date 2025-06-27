from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class Message(Base):
    __tablename__ = "messages"

    chat_id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(String(255), nullable=False)   # ✔ 길이 명시
    user_id = Column(String(255), nullable=False)
    content = Column(Text)
    image_url = Column(Text)
    has_image = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    is_delivered = Column(Boolean, default=False)

class AIMessage(Base):
    __tablename__ = "ai_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False)
    couple_id = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class PersonaConfig(Base):
    __tablename__ = "persona_config"

    user_id = Column(String, primary_key=True, index=True)
    persona_name = Column(String, default="무민")
    updated_at = Column(DateTime, default=datetime.utcnow)
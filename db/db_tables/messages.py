from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean, Integer, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

# ================== 커플 채팅 메시지 ===================
class Message(Base):
    __tablename__ = "messages"

    chat_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    couple_id = Column(String(255), ForeignKey("couples.couple_id", ondelete="CASCADE"), nullable=False)
    content = Column(Text)
    image_url = Column(Text)
    has_image = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    is_delivered = Column(Boolean, default=False)
    embed_index = Column(Integer, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="messages")
    couple = relationship("Couple", back_populates="messages")

# ================== AI chat 페르소나 설정 ==================
class PersonaConfig(Base):
    __tablename__ = "persona_config"

    couple_id = Column(String(255), ForeignKey("couples.couple_id", ondelete="CASCADE"), primary_key=True, index=True)
    persona_name = Column(String(255), default="무민")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    couple = relationship("Couple", back_populates="persona_config")

# ================== AI 메시지(챗봇) =================
class AIMessage(Base):
    __tablename__ = "ai_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    couple_id = Column(String(255), ForeignKey("couples.couple_id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    name = Column(String(255), nullable=True) # function_name
    embed_index = Column(Integer, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="ai_messages")
    couple = relationship("Couple", back_populates="ai_messages")

# =============== AI 메세지 누적 요약 =====================
class AIChatSummary(Base):
    __tablename__ = "ai_chat_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    couple_id = Column(String(255), ForeignKey("couples.couple_id", ondelete="CASCADE"), nullable=False)
    summary = Column(Text, nullable=False)
    emb_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_msg_id = Column(Integer, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="ai_chat_summaries")
    couple = relationship("Couple", back_populates="ai_chat_summaries")

# =============== Chunk 메타데이터 =====================
class ChunkMetadata(Base):
    __tablename__ = "chunk_metadata"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    chunk_id = Column(Integer, nullable=False)  # chunk 순서
    start_msg_id = Column(Integer, nullable=False)  # 시작 메시지 ID
    end_msg_id = Column(Integer, nullable=False)    # 끝 메시지 ID
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    embedding = Column(Text, nullable=False)  # JSON 형태로 저장
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="chunk_metadata")
    
    __table_args__ = (
        Index('idx_user_chunk', 'user_id', 'chunk_id'),
        Index('idx_user_time', 'user_id', 'start_time'),
        Index('idx_user_msg_range', 'user_id', 'start_msg_id', 'end_msg_id'),
    )
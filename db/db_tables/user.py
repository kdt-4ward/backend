from sqlalchemy import Column, ForeignKey, String, DateTime, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .base import Base

class GenderEnum(enum.Enum):
    male = "male"
    female = "female"
    other = "other"

class User(Base):
    __tablename__ = "users"

    user_id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=True)
    password = Column(String(255), nullable=True)  # 비밀번호 필드 추가
    birth = Column(DateTime, nullable=True)
    gender = Column(Enum(GenderEnum), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    modified_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    profile_image = Column(String(500), nullable=True)
    couple_id = Column(String(255), ForeignKey("couples.couple_id"), nullable=True)
    
    # Relationships with cascade delete
    couple = relationship("Couple", foreign_keys=[couple_id], back_populates="user")
    
    # User as user_1 in couples
    couples_as_user1 = relationship("Couple", foreign_keys="Couple.user_1", 
                                   cascade="all, delete", back_populates="user1")
    
    # User as user_2 in couples
    couples_as_user2 = relationship("Couple", foreign_keys="Couple.user_2", 
                                   cascade="all, delete", back_populates="user2")
    
    # Couple invites
    sent_invites = relationship("CoupleInvite", foreign_keys="CoupleInvite.inviter_user_id",
                               cascade="all, delete", back_populates="inviter")
    received_invites = relationship("CoupleInvite", foreign_keys="CoupleInvite.invited_user_id",
                                   cascade="all, delete", back_populates="invited")
    
    # Messages
    messages = relationship("Message", cascade="all, delete", back_populates="user")
    
    # AI Messages
    ai_messages = relationship("AIMessage", cascade="all, delete", back_populates="user")
    
    # AI Chat Summaries
    ai_chat_summaries = relationship("AIChatSummary", cascade="all, delete", back_populates="user")
    
    # Chunk Metadata
    chunk_metadata = relationship("ChunkMetadata", cascade="all, delete", back_populates="user")
    
    # Posts
    posts = relationship("Post", cascade="all, delete", back_populates="user")
    
    # Comments
    comments = relationship("Comment", cascade="all, delete", back_populates="user")
    
    # Emotion Logs
    emotion_logs = relationship("EmotionLog", cascade="all, delete", back_populates="user")
    
    # Survey Responses
    survey_responses = relationship("UserSurveyResponse", cascade="all, delete", back_populates="user")
    
    # Analysis Results
    ai_daily_analysis = relationship("AIDailyAnalysisResult", cascade="all, delete", back_populates="user")
    weekly_solutions = relationship("WeeklySolution", cascade="all, delete", back_populates="user")
    user_trait_summary = relationship("UserTraitSummary", cascade="all, delete", back_populates="user")
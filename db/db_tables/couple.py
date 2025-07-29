from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class Couple(Base):
    __tablename__ = "couples"

    couple_id = Column(String(255), primary_key=True)
    user_1 = Column(String(255), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    user_2 = Column(String(255), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    modified_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user1 = relationship("User", foreign_keys=[user_1], back_populates="couples_as_user1")
    user2 = relationship("User", foreign_keys=[user_2], back_populates="couples_as_user2")
    user = relationship("User", foreign_keys="User.couple_id", back_populates="couple")
    
    # Couple related data
    messages = relationship("Message", cascade="all, delete", back_populates="couple")
    ai_messages = relationship("AIMessage", cascade="all, delete", back_populates="couple")
    ai_chat_summaries = relationship("AIChatSummary", cascade="all, delete", back_populates="couple")
    posts = relationship("Post", cascade="all, delete", back_populates="couple")
    emotion_logs = relationship("EmotionLog", cascade="all, delete", back_populates="couple")
    persona_config = relationship("PersonaConfig", cascade="all, delete", back_populates="couple")
    
    # Analysis results - 각각 다른 이름으로 구분
    ai_daily_analysis = relationship("AIDailyAnalysisResult", cascade="all, delete", back_populates="couple")
    couple_daily_analysis = relationship("CoupleDailyAnalysisResult", cascade="all, delete", back_populates="couple")
    comparison_analysis = relationship("DailyComparisonAnalysisResult", cascade="all, delete", back_populates="couple")
    weekly_analysis = relationship("CoupleWeeklyAnalysisResult", cascade="all, delete", back_populates="couple")
    weekly_comparison = relationship("CoupleWeeklyComparisonResult", cascade="all, delete", back_populates="couple")
    weekly_recommendations = relationship("CoupleWeeklyRecommendation", cascade="all, delete", back_populates="couple")
    
    # Invites
    invites = relationship("CoupleInvite", cascade="all, delete", back_populates="couple")

class CoupleInvite(Base):
    __tablename__ = "couple_invites"

    invite_code = Column(String(16), primary_key=True)  # 랜덤 초대 코드, 8~16자
    inviter_user_id = Column(String(255), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    status = Column(String(32), default="pending")       # pending, accepted, expired 등
    invited_user_id = Column(String(255), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=True)
    couple_id = Column(String(255), ForeignKey("couples.couple_id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    accepted_at = Column(DateTime, nullable=True)
    expired_at = Column(DateTime, nullable=True)
    
    # Relationships
    inviter = relationship("User", foreign_keys=[inviter_user_id], back_populates="sent_invites")
    invited = relationship("User", foreign_keys=[invited_user_id], back_populates="received_invites")
    couple = relationship("Couple", back_populates="invites")
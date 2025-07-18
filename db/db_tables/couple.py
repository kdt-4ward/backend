from sqlalchemy import Column, String, DateTime, ForeignKey
from datetime import datetime
from .base import Base

class Couple(Base):
    __tablename__ = "couples"

    couple_id = Column(String(255), primary_key=True)
    user_1 = Column(String(255), ForeignKey("users.user_id"), nullable=False)
    user_2 = Column(String(255), ForeignKey("users.user_id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    modified_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CoupleInvite(Base):
    __tablename__ = "couple_invites"

    invite_code = Column(String(16), primary_key=True)  # 랜덤 초대 코드, 8~16자
    inviter_user_id = Column(String(255), ForeignKey("users.user_id"), nullable=False)
    status = Column(String(32), default="pending")       # pending, accepted, expired 등
    invited_user_id = Column(String(255), ForeignKey("users.user_id"), nullable=True)
    couple_id = Column(String(255), ForeignKey("couples.couple_id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    accepted_at = Column(DateTime, nullable=True)
    expired_at = Column(DateTime, nullable=True)
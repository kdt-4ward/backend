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
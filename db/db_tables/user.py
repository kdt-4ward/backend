from sqlalchemy import Column, ForeignKey, String, DateTime, Enum
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
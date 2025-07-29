from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class SurveyQuestion(Base):
    __tablename__ = "survey_questions"

    id = Column(Integer, primary_key=True)
    code = Column(String(255), unique=True)
    text = Column(String(255), nullable=False)
    order = Column(Integer)
    
    # Relationships
    choices = relationship("SurveyChoice", cascade="all, delete", back_populates="question")
    responses = relationship("UserSurveyResponse", cascade="all, delete", back_populates="question")

class SurveyChoice(Base):
    __tablename__ = "survey_choices"

    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey("survey_questions.id", ondelete="CASCADE"))
    text = Column(String(255), nullable=False)
    tag = Column(String(255))
    
    # Relationships
    question = relationship("SurveyQuestion", back_populates="choices")
    responses = relationship("UserSurveyResponse", cascade="all, delete", back_populates="choice")

class UserSurveyResponse(Base):
    __tablename__ = "user_survey_responses"

    id = Column(Integer, primary_key=True)
    user_id = Column(String(255), ForeignKey("users.user_id", ondelete="CASCADE"))
    question_id = Column(Integer, ForeignKey("survey_questions.id", ondelete="CASCADE"))
    choice_id = Column(Integer, ForeignKey("survey_choices.id", ondelete="CASCADE"), nullable=True)
    custom_input = Column(Text, nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="survey_responses")
    question = relationship("SurveyQuestion", back_populates="responses")
    choice = relationship("SurveyChoice", back_populates="responses")
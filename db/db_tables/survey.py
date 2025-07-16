from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text
from datetime import datetime
from .base import Base

class SurveyQuestion(Base):
    __tablename__ = "survey_questions"

    id = Column(Integer, primary_key=True)
    code = Column(String(255), unique=True)
    text = Column(String(255), nullable=False)
    order = Column(Integer)

class SurveyChoice(Base):
    __tablename__ = "survey_choices"

    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey("survey_questions.id"))
    text = Column(String(255), nullable=False)
    tag = Column(String(255))

class UserSurveyResponse(Base):
    __tablename__ = "user_survey_responses"

    id = Column(Integer, primary_key=True)
    user_id = Column(String(255), ForeignKey("users.user_id"))
    question_id = Column(Integer, ForeignKey("survey_questions.id"))
    choice_id = Column(Integer, ForeignKey("survey_choices.id"), nullable=True)
    custom_input = Column(Text, nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow)
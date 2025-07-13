from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base
from datetime import datetime
import enum
from sqlalchemy import Enum

Base = declarative_base()

class GenderEnum(enum.Enum):
    male = "male"
    female = "female"
    other = "other"

# ================== User 테이블 (예시) ==============
class User(Base):
    __tablename__ = "users"

    user_id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    modified_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    birth = Column(DateTime, nullable=True)
    gender = Column(Enum(GenderEnum), nullable=True)

# ==================== Couple table =======================
class Couple(Base):
    __tablename__ = "couples"

    couple_id = Column(String(255), primary_key=True)
    user_1 = Column(String(255), ForeignKey("users.user_id"), nullable=False)
    user_2 = Column(String(255), ForeignKey("users.user_id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    modified_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ================== 채팅 메시지 ===================
class Message(Base):
    __tablename__ = "messages"

    chat_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), ForeignKey("users.user_id"), nullable=False)
    couple_id = Column(String(255), ForeignKey("couples.couple_id"), nullable=False)
    content = Column(Text)
    image_url = Column(Text)
    has_image = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    is_delivered = Column(Boolean, default=False)
    embed_index = Column(Integer, nullable=True)

# ================== AI 메시지(챗봇) =================
class AIMessage(Base):
    __tablename__ = "ai_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), ForeignKey("users.user_id"), nullable=False)
    couple_id = Column(String(255), ForeignKey("couples.couple_id"), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    embed_index = Column(Integer, nullable=True)

# ================== 페르소나 설정 ==================
class PersonaConfig(Base):
    __tablename__ = "persona_config"

    couple_id = Column(String(255), ForeignKey("couples.couple_id"), primary_key=True, index=True)
    persona_name = Column(String(255), default="무민")
    updated_at = Column(DateTime, default=datetime.utcnow)

# ================ EmotionLog ================
class EmotionLog(Base):
    __tablename__ = "emotion_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), ForeignKey("users.user_id"), nullable=False)
    emotion = Column(Text)
    date = Column(DateTime, default=datetime.utcnow)
    memo = Column(Text)

# ================ Analysis & Solution ================
class WeeklySolution(Base):
    __tablename__ = "weekly_solutions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), ForeignKey("users.user_id"), nullable=False)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class AIDailyAnalysisResult(Base):
    __tablename__ = "aidaily_analysis_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), ForeignKey("users.user_id"), nullable=False)
    couple_id = Column(String(255), ForeignKey("couples.couple_id"), nullable=True)
    date = Column(DateTime, nullable=False)  # 분석 기준 날짜 (date only, 시간 X)
    result = Column(Text, nullable=False)  # JSON string or summary
    created_at = Column(DateTime, default=datetime.utcnow)
    modified_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CoupleDailyAnalysisResult(Base):
    __tablename__ = "couple_daily_analysis_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(String(255), ForeignKey("couples.couple_id"), nullable=False)
    date = Column(DateTime, nullable=False)  # 분석 기준 날짜 (date only)
    result = Column(Text, nullable=False)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    modified_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UserTraitSummary(Base):
    __tablename__ = "user_trait_summaries"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), ForeignKey("users.user_id"), nullable=False, unique=True)  # user_id 단일 unique
    summary = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
# =============== 누적 요약 용 =====================
class AIChatSummary(Base):
    __tablename__ = "ai_chat_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), ForeignKey("users.user_id"), nullable=False)
    couple_id = Column(String(255), ForeignKey("couples.couple_id"), nullable=False)
    summary = Column(Text, nullable=False)
    emb_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_msg_id = Column(Integer, nullable=False)

class CoupleChatSummary(Base):
    __tablename__ = "couple_chat_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(String(255), ForeignKey("couples.couple_id"), nullable=False)
    summary = Column(Text, nullable=False)
    emb_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# ======================== 설문 DB ============================
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

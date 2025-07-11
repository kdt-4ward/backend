from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

import enum
from sqlalchemy import Enum

class GenderEnum(enum.Enum):
    male = "male"
    female = "female"
    other = "other"

# ================== 채팅 메시지 ===================
class Message(Base):
    __tablename__ = "messages"

    chat_id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(String(255), nullable=False)
    user_id = Column(String(255), nullable=False)
    content = Column(Text)
    image_url = Column(Text)
    has_image = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    is_delivered = Column(Boolean, default=False)
    embed_index = Column(Integer, nullable=True)  # <--- 추가!

# ================== AI 메시지(챗봇) =================
class AIMessage(Base):
    __tablename__ = "ai_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False)
    couple_id = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    embed_index = Column(Integer, nullable=True)  # <--- 추가!

# ================== 페르소나 설정 ==================
class PersonaConfig(Base):
    __tablename__ = "persona_config"

    couple_id = Column(String(255), primary_key=True, index=True)
    persona_name = Column(String(255), default="무민")
    updated_at = Column(DateTime, default=datetime.utcnow)

# ================== User 테이블 (예시) ==============
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), unique=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    modified_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    birth = Column(DateTime, nullable=True)
    gender = Column(Enum(GenderEnum), nullable=True)
    # 기타 필요한 필드 추가
# ==================== Couple table =======================
class Couple(Base):
    __tablename__ = "couples"

    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(String(255),unique=True, nullable=False)
    user_1 = Column(String(255), nullable=False)
    user_2 = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    modified_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
       
# ================ Questionnaire ================
class Questionnaire(Base):
    __tablename__ = "questionnaires"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False)
    answers = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

# ================ EmotionLog ================
class EmotionLog(Base):
    __tablename__ = "emotion_logs"

    emotion_id = Column(Integer, primary_key=True, autoincrement=True)  # PK
    user_id = Column(String(255), ForeignKey("users.user_id"), nullable=False)
    couple_id = Column(String(255), ForeignKey("couples.couple_id"), nullable=True)

    emotion = Column(String(100), nullable=False)                       # 기본 감정 (캐릭터 ID 등)
    detail_emotions = Column(Text, nullable=True)                       # 세부 감정들 (JSON 문자열 형태)

    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow)  # 기록 날짜
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 수정 날짜
    deleted_at = Column(DateTime, nullable=True)    

# ================ WeeklySolution (분석 결과 저장용, 선택) ================
class WeeklySolution(Base):
    __tablename__ = "weekly_solutions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class AIChatSummary(Base):
    __tablename__ = "ai_chat_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False)
    couple_id = Column(String(255), nullable=False)
    summary = Column(Text, nullable=False)
    emb_id = Column(Integer, nullable=True)  # 벡터 DB 연결 시
    created_at = Column(DateTime, default=datetime.utcnow)
    last_msg_id = Column(Integer, nullable=False)

class CoupleChatSummary(Base):
    __tablename__ = "couple_chat_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(String(255), nullable=False)
    summary = Column(Text, nullable=False)
    emb_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ========================설문 DB ============================

class SurveyQuestion(Base):
    __tablename__ = "survey_questions"

    id = Column(Integer, primary_key=True)
    code = Column(String(255), unique=True)  # ex) relationship_value
    text = Column(String(255), nullable=False)
    order = Column(Integer)

class SurveyChoice(Base):
    __tablename__ = "survey_choices"

    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey("survey_questions.id"))
    text = Column(String(255), nullable=False)
    tag = Column(String(255))  # 예: "trust_first", "quality_time"

class UserSurveyResponse(Base):
    __tablename__ = "user_survey_responses"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    question_id = Column(Integer, ForeignKey("survey_questions.id"))
    choice_id = Column(Integer, ForeignKey("survey_choices.id"), nullable=True)  # 객관식 선택 시
    custom_input = Column(Text, nullable=True)  # 기타 입력 시
    submitted_at = Column(DateTime, default=datetime.utcnow)


# 게시글
class Post(Base):
    __tablename__ = "posts"

    post_id = Column(Integer, primary_key=True, autoincrement=True)   # 게시글 ID (PK)
    user_id = Column(String(255), nullable=False)                     # 작성자
    couple_id = Column(String(255), nullable=False)                   # 커플 ID
    content = Column(Text, nullable=True)                             # 게시글 내용

    created_at = Column(DateTime, default=datetime.utcnow)            # 생성일
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 수정일
    deleted_at = Column(DateTime, nullable=True)                      # 삭제일 (소프트 삭제용)

class Comment(Base):
    __tablename__ = "Post_comments"

    comment_id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.post_id"))
    user_id = Column(String(255), nullable=False)
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

class PostImage(Base):
    __tablename__ = "post_images"

    image_id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey("posts.post_id"), nullable=False)
    image_url = Column(String(500), nullable=False)
    image_order = Column(Integer, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

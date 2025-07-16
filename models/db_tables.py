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
    email = Column(String(255), unique=True, nullable=True)
    password = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    modified_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    birth = Column(DateTime, nullable=True)
    gender = Column(Enum(GenderEnum), nullable=True)
    profile_image = Column(String(500), nullable=True)
    couple_id = Column(String(255), ForeignKey("couples.couple_id"), nullable=True)

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

    emotion_id = Column(Integer, primary_key=True, autoincrement=True)  # PK
    user_id = Column(String(255), ForeignKey("users.user_id"), nullable=False)
    couple_id = Column(String(255), ForeignKey("couples.couple_id"), nullable=True)

    emotion = Column(String(100), nullable=False)                       # 기본 감정 (캐릭터 ID 등)
    detail_emotions = Column(Text, nullable=True)                       # 세부 감정들 (JSON 문자열 형태)
    memo = Column(Text, nullable=True)   # <-- ✅ 메모 추가!

    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow)  # 기록 날짜
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 수정 날짜
    deleted_at = Column(DateTime, nullable=True)

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

class CoupleWeeklyAnalysisResult(Base):
    __tablename__ = "couple_weekly_analysis_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(String(255), ForeignKey("couples.couple_id"), nullable=False)
    
    week_start_date = Column(DateTime, nullable=False)  # 주 시작 날짜 (월요일 등)
    week_end_date = Column(DateTime, nullable=False)    # 주 종료 날짜 (일요일 등)
    
    result = Column(Text, nullable=False)  # JSON string (주간 요약, 통계 등)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    modified_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CoupleWeeklyComparisonResult(Base):
    __tablename__ = "couple_weekly_comparison_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(String(255), ForeignKey("couples.couple_id"), nullable=False)

    week_start_date = Column(DateTime, nullable=False)
    week_end_date = Column(DateTime, nullable=False)

    comparison = Column(Text, nullable=False)  # LLM 비교 분석 결과
    created_at = Column(DateTime, default=datetime.utcnow)

class CoupleWeeklyRecommendation(Base):
    __tablename__ = "couple_weekly_recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(String(255), ForeignKey("couples.couple_id"), nullable=False)

    week_start_date = Column(DateTime, nullable=False)
    week_end_date = Column(DateTime, nullable=False)

    advice = Column(Text, nullable=False)  # 조언
    content_type = Column(String(50))      # 예: "영화", "플레이리스트"
    content_title = Column(String(255))
    content_reason = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    
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
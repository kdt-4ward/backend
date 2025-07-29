from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

########## AI chat 일간 분석 ##############
class AIDailyAnalysisResult(Base):
    __tablename__ = "aidaily_analysis_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    couple_id = Column(String(255), ForeignKey("couples.couple_id", ondelete="CASCADE"), nullable=True)
    date = Column(DateTime, nullable=False)  # 분석 기준 날짜 (date only, 시간 X)
    result = Column(Text, nullable=False)  # JSON string or summary
    created_at = Column(DateTime, default=datetime.utcnow)
    modified_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="ai_daily_analysis")
    couple = relationship("Couple", back_populates="ai_daily_analysis")

########## 커플 chat 일간 분석 ##############
class CoupleDailyAnalysisResult(Base):
    __tablename__ = "couple_daily_analysis_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(String(255), ForeignKey("couples.couple_id", ondelete="CASCADE"), nullable=False)
    date = Column(DateTime, nullable=False)  # 분석 기준 날짜 (date only)
    result = Column(Text, nullable=False)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    modified_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    couple = relationship("Couple", back_populates="couple_daily_analysis")

########## 일간 비교 분석 결과 ##############
class DailyComparisonAnalysisResult(Base):
    __tablename__ = "daily_comparison_analysis_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(String(255), ForeignKey("couples.couple_id", ondelete="CASCADE"), nullable=False)
    date = Column(DateTime, nullable=False)  # 분석 기준 날짜 (date only)
    result = Column(Text, nullable=False)  # JSON string (비교 분석 결과)
    created_at = Column(DateTime, default=datetime.utcnow)
    modified_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    couple = relationship("Couple", back_populates="comparison_analysis")

########### 커플 chat 주간 분석 ################
class CoupleWeeklyAnalysisResult(Base):
    __tablename__ = "couple_weekly_analysis_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(String(255), ForeignKey("couples.couple_id", ondelete="CASCADE"), nullable=False)
    
    week_start_date = Column(DateTime, nullable=False)  # 주 시작 날짜 (월요일 등)
    week_end_date = Column(DateTime, nullable=False)    # 주 종료 날짜 (일요일 등)
    
    result = Column(Text, nullable=False)  # JSON string (주간 요약, 통계 등)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    modified_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    couple = relationship("Couple", back_populates="weekly_analysis")

############ AI vs Couple chat 비교 분석 #################

class CoupleWeeklyComparisonResult(Base):
    __tablename__ = "couple_weekly_comparison_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(String(255), ForeignKey("couples.couple_id", ondelete="CASCADE"), nullable=False)

    week_start_date = Column(DateTime, nullable=False)
    week_end_date = Column(DateTime, nullable=False)

    comparison = Column(Text, nullable=False)  # LLM 비교 분석 결과
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    couple = relationship("Couple", back_populates="weekly_comparison")

############# 컨텐츠 추천 ####################

class CoupleWeeklyRecommendation(Base):
    __tablename__ = "couple_weekly_recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(String(255), ForeignKey("couples.couple_id", ondelete="CASCADE"), nullable=False)

    week_start_date = Column(DateTime, nullable=False)
    week_end_date = Column(DateTime, nullable=False)

    advice = Column(Text, nullable=False)  # 조언/솔루션
    
    # 기본 song 정보
    song_title = Column(String(255), nullable=True)
    song_reason = Column(Text, nullable=True)
    
    # 기본 movie 정보  
    movie_title = Column(String(255), nullable=True)
    movie_reason = Column(Text, nullable=True)

    # 강화된 정보 (TMDB, YouTube API 정보)
    enhanced_song_data = Column(Text, nullable=True)  # JSON string - YouTube API 정보
    enhanced_movie_data = Column(Text, nullable=True)  # JSON string - TMDB API 정보

    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    couple = relationship("Couple", back_populates="weekly_recommendations")

###################### 주간 솔루션 ##################
class WeeklySolution(Base):
    __tablename__ = "weekly_solutions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="weekly_solutions")

###################### 유저 성향 분석 결과 #######################
class UserTraitSummary(Base):
    __tablename__ = "user_trait_summaries"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, unique=True)  # user_id 단일 unique
    summary = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="user_trait_summary")
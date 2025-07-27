from datetime import datetime, timedelta
from db.db_tables import *  # 실제 모델 경로/명에 맞게 조정
from sqlalchemy.orm import Session
import json


def get_user_name(db: Session, user_id: str) -> str | None:
    user = db.query(User).filter_by(user_id=user_id).first()
    return user.name if user else None

def get_user_traits(db: Session, user_id: str):
    results = (
        db.query(
            SurveyQuestion.code,
            SurveyQuestion.text.label("question_text"),
            SurveyChoice.text.label("choice_text"),
            SurveyChoice.tag,
            UserSurveyResponse.custom_input
        )
        .join(UserSurveyResponse, SurveyQuestion.id == UserSurveyResponse.question_id)
        .outerjoin(SurveyChoice, SurveyChoice.id == UserSurveyResponse.choice_id)
        .filter(UserSurveyResponse.user_id == user_id)
        .all()
    )
    return [
        {
            "code": row.code,
            "question_text": row.question_text,
            "choice_text": row.choice_text,
            "tag": row.tag,
            "custom_input": row.custom_input,
        }
        for row in results
    ]

def save_user_trait_summary(db: Session, user_id: str, summary: str) -> None:
    """
    Save or update a user's trait summary (1 per user).
    """
    try:
        existing = db.query(UserTraitSummary).filter_by(user_id=user_id).first()
        if existing:
            existing.summary = summary
        else:
            new = UserTraitSummary(
                user_id=user_id,
                summary=summary
            )
            db.add(new)
        db.commit()
    except Exception as e:
        db.rollback()
        raise e


def get_week_chat_logs_by_couple_id(db: Session, couple_id: str):
    from datetime import datetime, timedelta

    one_week_ago = datetime.utcnow() - timedelta(days=7)
    return db.query(Message).filter(
        Message.couple_id == couple_id,
        Message.created_at >= one_week_ago
    ).all()

def get_all_couple_ids(db) -> list[str]:
    return [row[0] for row in db.query(Couple.couple_id).distinct().all()]

def get_all_user_ids(db):
    """전체 user_id 리스트 반환"""
    return [row.user_id for row in db.query(User.user_id).all()]

def get_users_by_couple_id(db, couple_id: str) -> tuple[str, str]:
    couple = db.query(Couple).filter(Couple.couple_id == couple_id).first()
    if not couple:
        return []
    return couple.user_1, couple.user_2

def get_week_chat_logs(db, couple_id):
    """최근 7일 채팅 로그"""
    week_ago = datetime.utcnow() - timedelta(days=7)
    return db.query(Message).filter(
        Message.couple_id == couple_id,
        Message.created_at >= week_ago
    ).order_by(Message.created_at).all()

def get_servey(db, user_id):
    """사용자 사전 질의응답"""
    return db.query(UserSurveyResponse).filter_by(user_id=user_id).order_by(UserSurveyResponse.submitted_at.desc()).all()

def get_daily_emotions(db, user_id):
    """최근 7일 감정 요약 로그"""
    week_ago = datetime.utcnow() - timedelta(days=7)
    return db.query(EmotionLog).filter(
        EmotionLog.user_id == user_id,
        EmotionLog.date >= week_ago
    ).order_by(EmotionLog.date).all()

# 1. 커플 일간 채팅 로그 조회
def get_daily_chat_logs_by_couple_id(db: Session, couple_id: str, date: datetime):
    # date는 datetime 객체라고 가정 (date.date() 아님!)
    end = date
    start = end - timedelta(hours=24)

    rows = db.query(Message).filter(
        Message.couple_id == couple_id,
        Message.created_at >= start,
        Message.created_at < end
    ).order_by(Message.created_at).all()

    return [
        {"user_id": row.user_id, "content": row.content, "created_at": row.created_at}
        for row in rows
    ]
# 2. 커플 일간 분석 결과 저장
def save_daily_couple_analysis_result(db: Session, couple_id: str, date: datetime.date, result: dict):
    date_start = datetime.combine(date, datetime.min.time())

    obj = db.query(CoupleDailyAnalysisResult).filter(
        CoupleDailyAnalysisResult.couple_id == couple_id,
        CoupleDailyAnalysisResult.date == date_start
    ).first()

    result_str = json.dumps(result, ensure_ascii=False)
    now = datetime.utcnow()
    if obj:
        obj.result = result_str
        obj.modified_at = now
    else:
        obj = CoupleDailyAnalysisResult(
            couple_id=couple_id,
            date=date_start,
            result=result_str,
            created_at=now,
            modified_at=now
        )
        db.add(obj)
    db.commit()
# 3. 유저 일간 AI 채팅 로그 조회
def get_daily_ai_chat_logs_by_user_id(db: Session, user_id: str, date: datetime.date):
    start = datetime.combine(date, datetime.min.time())
    end = datetime.combine(date, datetime.max.time())
    rows = db.query(AIMessage).filter(
        AIMessage.user_id == user_id,
        AIMessage.created_at >= start,
        AIMessage.created_at <= end
    ).order_by(AIMessage.created_at).all()
    return [
        {"role": row.role, "content": row.content, "created_at": row.created_at}
        for row in rows
    ]

# 4. 유저 일간 AI 분석 결과 저장
def save_daily_ai_analysis_result(db: Session, user_id: str, date: datetime.date, result: dict):
    # date는 반드시 "해당 일" 00:00:00 ~ 23:59:59 범위의 날짜
    date_start = datetime.combine(date, datetime.min.time())

    # user_id로부터 couple_id 찾기
    couple_id = get_couple_id_by_user_id(db, user_id)

    # upsert 방식: user_id + date(unique)에 대해 갱신/저장
    obj = db.query(AIDailyAnalysisResult).filter(
        AIDailyAnalysisResult.user_id == user_id,
        AIDailyAnalysisResult.date == date_start
    ).first()

    result_str = json.dumps(result, ensure_ascii=False)
    now = datetime.utcnow()
    if obj:
        obj.result = result_str
        obj.modified_at = now
        if couple_id:
            obj.couple_id = couple_id
    else:
        obj = AIDailyAnalysisResult(
            user_id=user_id,
            couple_id=couple_id,
            date=date_start,
            result=result_str,
            created_at=now,
            modified_at=now
        )
        db.add(obj)
    db.commit()

def get_couple_id_by_user_id(db: Session, user_id: str) -> str | None:
    """사용자 ID로부터 커플 ID를 찾습니다. user_1 또는 user_2에서 찾습니다."""
    # user_1에서 찾기
    couple = db.query(Couple.couple_id).filter(Couple.user_1 == user_id).first()
    if couple:
        return couple.couple_id
    
    # user_2에서 찾기
    couple = db.query(Couple.couple_id).filter(Couple.user_2 == user_id).first()
    if couple:
        return couple.couple_id
    
    # 커플을 찾지 못한 경우
    return None

def load_daily_couple_stats(db: Session, couple_id: str, week_dates: list[datetime.date]) -> list[dict]:
    summaries = db.query(CoupleDailyAnalysisResult).filter(
        CoupleDailyAnalysisResult.couple_id == couple_id,
        CoupleDailyAnalysisResult.date >= week_dates[0],
        CoupleDailyAnalysisResult.date <= week_dates[-1]
    ).order_by(CoupleDailyAnalysisResult.created_at).all()
    return [json.loads(row.result) for row in summaries]

def load_daily_ai_stats(db: Session, user_id: str, week_dates: list[datetime.date]) -> list[dict]:
    summaries = db.query(AIChatSummary).filter(
        AIChatSummary.user_id == user_id,
        AIChatSummary.created_at >= week_dates[0],
        AIChatSummary.created_at <= week_dates[-1]
    ).order_by(AIChatSummary.created_at).all()
    return [json.loads(row.summary) for row in summaries]

def get_daily_emotion_logs_by_couple_id(db: Session, couple_id: str, date: datetime):
    """커플의 일간 감정 기록을 조회합니다."""
    end = date
    start = end - timedelta(hours=24)
    
    # 해당 커플의 두 사용자 ID 조회
    couple = db.query(Couple).filter_by(couple_id=couple_id).first()
    if not couple:
        return []
    
    user1_id, user2_id = couple.user_1, couple.user_2
    
    # 두 사용자의 감정 기록 조회
    emotion_logs = db.query(EmotionLog).filter(
        EmotionLog.user_id.in_([user1_id, user2_id]),
        EmotionLog.recorded_at >= start,
        EmotionLog.recorded_at < end
    ).order_by(EmotionLog.recorded_at).all()
    
    return [
        {
            "user_id": log.user_id,
            "emotion": log.emotion,
            "detail_emotions": json.loads(log.detail_emotions) if log.detail_emotions else [],
            "memo": log.memo,
            "recorded_at": log.recorded_at
        }
        for log in emotion_logs
    ]

def get_daily_emotion_logs_by_user_id(db: Session, user_id: str, date: datetime):
    """사용자의 일간 감정 기록을 조회합니다. (하루에 한 번만 기록됨)"""
    end = date
    start = end - timedelta(hours=24)
    
    log = (
        db.query(EmotionLog)
        .filter(
            EmotionLog.user_id == user_id,
            EmotionLog.recorded_at >= start,
            EmotionLog.recorded_at < end
        )
        .order_by(EmotionLog.recorded_at.desc())
        .first()
    )
    
    if not log:
        return []
    
    return {
        "user_id": log.user_id,
        "emotion": log.emotion,
        "detail_emotions": json.loads(log.detail_emotions) if log.detail_emotions else [],
        "memo": log.memo,
        "recorded_at": log.recorded_at
    }

# 5. 일간 비교 분석 결과 저장
def save_daily_comparison_analysis_result(db: Session, couple_id: str, date: datetime.date, result: dict):
    date_start = datetime.combine(date, datetime.min.time())

    obj = db.query(DailyComparisonAnalysisResult).filter(
        DailyComparisonAnalysisResult.couple_id == couple_id,
        DailyComparisonAnalysisResult.date == date_start
    ).first()

    result_str = json.dumps(result, ensure_ascii=False)
    now = datetime.utcnow()
    if obj:
        obj.result = result_str
        obj.modified_at = now
    else:
        obj = DailyComparisonAnalysisResult(
            couple_id=couple_id,
            date=date_start,
            result=result_str,
            created_at=now,
            modified_at=now
        )
        db.add(obj)
    db.commit()
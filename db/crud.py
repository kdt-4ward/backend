from datetime import datetime, timedelta
from models.db_tables import Message, EmotionLog, Couple, User, UserSurveyResponse  # 실제 모델 경로/명에 맞게 조정


def get_week_chat_logs_by_couple_id(db, couple_id: str):
    from datetime import datetime, timedelta

    one_week_ago = datetime.utcnow() - timedelta(days=7)
    return db.query(Message).filter(
        Message.couple_id == couple_id,
        Message.created_at >= one_week_ago
    ).all()

def get_all_couple_ids(db) -> list[str]:
    return db.query(Couple.couple_id).distinct().all()

def get_all_user_ids(db):
    """전체 user_id 리스트 반환"""
    return [row.id for row in db.query(User.user_id).all()]

def get_users_by_couple_id(db, couple_id: str) -> list[User]:
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

from datetime import datetime, timedelta
from models.db_models import Message, Questionnaire, EmotionLog, User  # 실제 모델 경로/명에 맞게 조정

def get_all_user_ids(db):
    """전체 user_id 리스트 반환"""
    return [row.id for row in db.query(User.id).all()]

def get_week_chat_logs(db, couple_id):
    """최근 7일 채팅 로그"""
    week_ago = datetime.utcnow() - timedelta(days=7)
    return db.query(Message).filter(
        Message.couple_id == couple_id,
        Message.created_at >= week_ago
    ).order_by(Message.created_at).all()

def get_questionnaire(db, user_id):
    """사용자의 최신 질문지"""
    return db.query(Questionnaire).filter_by(user_id=user_id).order_by(Questionnaire.created_at.desc()).first()

def get_daily_emotions(db, user_id):
    """최근 7일 감정 요약 로그"""
    week_ago = datetime.utcnow() - timedelta(days=7)
    return db.query(EmotionLog).filter(
        EmotionLog.user_id == user_id,
        EmotionLog.date >= week_ago
    ).order_by(EmotionLog.date).all()

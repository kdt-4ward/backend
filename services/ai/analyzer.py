import random
from typing import List, Dict
from services.ai.analyzer_langchain import daily_chain
from db.db import SessionLocal
from models.db_models import Message
from datetime import datetime, timedelta

# 샘플 키워드 세트 (현실 적용 시 보강 필요)
AFFECTION_KEYWORDS = ["사랑해", "보고싶어", "고마워", "예쁘다", "멋지다", "행복해", "축하해"]
CONSIDERATION_KEYWORDS = ["괜찮아?", "힘내", "걱정마", "도와줄게", "수고했어", "조심해"]
ACTIVITY_KEYWORDS = ["만나자", "보고싶다", "가자", "해보자", "같이", "제안", "시도", "먼저 연락"]

PLAYLIST_RECOMMENDATIONS = [
    "잔잔한 카페 분위기의 Lo-fi 플레이리스트",
    "사랑이 싹트는 설레는 팝송 모음",
    "마음을 위로해주는 힐링 발라드"
]
MOVIE_RECOMMENDATIONS = [
    "러브 액츄얼리",
    "어바웃 타임",
    "인사이드 아웃",
    "클로저"
]

def group_messages_by_day(messages):
    """메시지를 날짜별로 그룹핑"""
    day_dict = {}
    for msg in messages:
        day = msg.created_at.date()
        day_dict.setdefault(day, []).append(msg.content)
    return day_dict

async def analyze_weekly_chat(couple_id):
    with SessionLocal() as db:
        since = datetime.utcnow() - timedelta(days=7)
        messages = db.query(Message).filter(
            Message.couple_id == couple_id,
            Message.created_at >= since
        ).order_by(Message.created_at).all()
    day_dict = group_messages_by_day(messages)
    daily_stats = []
    for day, msgs in sorted(day_dict.items()):
        day_result = await summarize_and_count_by_day(msgs)  # <<<<<<<< LLM NLU 분석으로 변경
        day_result["date"] = str(day)
        daily_stats.append(day_result)
    # 이후 daily_stats로 최종 주간 요약 프롬프트/LLM 분석 (동일)
    return daily_stats
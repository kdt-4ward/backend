import datetime
import logging
from db.crud import (
    get_all_user_ids,
    get_user_traits,
    get_user_name,
    save_user_trait_summary
)
from services.ai.user_personality_summary import summarize_personality_from_tags
from db.db import get_session

logger = logging.getLogger(__name__)

# 1. 한 명 분석 및 저장 함수
async def analyze_and_save_user_trait_summary(db, user_id: str):
    try:
        responses = get_user_traits(db, user_id)
        if not responses:
            logger.warning(f"[성향 요약] 사용자 {user_id} 응답 없음")
            return False

        user_name = get_user_name(db, user_id) or "user"
        summary = await summarize_personality_from_tags(responses, user_name=user_name)
        save_user_trait_summary(db, user_id, summary)
        logger.info(f"[성향 요약] 사용자 {user_id} 요약 저장 완료")
        return True
    except Exception as e:
        logger.error(f"[성향 요약] 사용자 {user_id} 처리 실패: {e}")
        return False

# 2. 전체 일괄 분석 함수
async def run_trait_summary_for_all_users():
    with get_session() as db:
        user_ids = get_all_user_ids(db)
        logger.info(f"[성향 요약] {len(user_ids)}명 대상 분석 시작")
        for user_id in user_ids:
            await analyze_and_save_user_trait_summary(db, user_id)
        logger.info("[성향 요약] 전체 완료")
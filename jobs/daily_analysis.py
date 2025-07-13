import asyncio
import logging
import datetime
from db.crud import (
    get_all_couple_ids,
    get_all_user_ids,
    get_daily_chat_logs_by_couple_id,
    save_daily_couple_analysis_result,
    get_daily_ai_chat_logs_by_user_id,
    save_daily_ai_analysis_result,
)
from services.ai.analyzer_langchain import analyze_daily
from db.db import get_session
logger = logging.getLogger(__name__)

async def run_daily_analysis_for_target(
    target_id: str,
    date: datetime.date,
    log_fetch_func,
    analyze_func,
    prompt_name: str,
    save_func,
    log_prefix: str = ""
):
    chat_logs = log_fetch_func(get_session(), target_id, date)
    if not chat_logs or len(chat_logs) == 0:
        logger.warning(f"[{log_prefix}] {target_id}의 {date} 대화 없음")
        return

    messages = [c['content'] if isinstance(c, dict) else c for c in chat_logs]

    try:
        result = await analyze_func(messages, prompt_name=prompt_name)
        save_func(get_session(), target_id, date, result)
        logger.info(f"[{log_prefix}] {target_id}의 {date} 분석 저장 완료")
    except Exception as e:
        logger.error(f"[{log_prefix}] {target_id} 분석 실패: {e}")

async def run_all_targets_daily_analysis(
    get_target_ids_func,
    log_fetch_func,
    analyze_func,
    prompt_name: str,
    save_func,
    log_prefix: str,
    date: datetime.date = None,
):
    if date is None:
        date = datetime.date.today()
    target_ids = get_target_ids_func(get_session())
    logger.info(f"[{log_prefix}] 전체 {len(target_ids)}명 분석 시작 ({date})")
    tasks = [
        run_daily_analysis_for_target(
            target_id,
            date,
            log_fetch_func,
            analyze_func,
            prompt_name,
            save_func,
            log_prefix
        )
        for target_id in target_ids
    ]
    await asyncio.gather(*tasks)
    logger.info(f"[{log_prefix}] 전체 분석 완료")


def daily_couplechat_analysis_for_all_couples():
    asyncio.run(
        run_all_targets_daily_analysis(
            get_target_ids_func=get_all_couple_ids,
            log_fetch_func=get_daily_chat_logs_by_couple_id,
            analyze_func=analyze_daily,
            prompt_name="daily_nlu",
            save_func=save_daily_couple_analysis_result,
            log_prefix="커플 일간분석"
        )
    )

def daily_aichat_analysis_for_all_users():
    asyncio.run(
        run_all_targets_daily_analysis(
            get_target_ids_func=get_all_user_ids,
            log_fetch_func=get_daily_ai_chat_logs_by_user_id,
            analyze_func=analyze_daily,
            prompt_name="daily_ai_nlu",
            save_func=save_daily_ai_analysis_result,
            log_prefix="AI상담 일간분석"
        )
    )
import asyncio
import datetime
import logging
from db.crud import (
    get_all_couple_ids,
    get_all_user_ids,
    get_daily_chat_logs_by_couple_id,
    get_daily_ai_chat_logs_by_user_id,
    get_daily_emotion_logs_by_couple_id,
    save_daily_couple_analysis_result,
    save_daily_ai_analysis_result,
    save_daily_comparison_analysis_result
)
from services.ai.analyzer_langchain import analyze_daily
from services.ai.analyzer import DailyAnalyzer
from db.db import get_session

logger = logging.getLogger(__name__)

async def run_daily_for_all(target_ids: list[str], analyzer: DailyAnalyzer, date: datetime.date):
    tasks = [analyzer.run(tid, date) for tid in target_ids]
    await asyncio.gather(*tasks)

async def daily_couplechat_analysis_for_all_couples(target_date=None):
    db = get_session()
    couple_ids = get_all_couple_ids(db)
    if target_date is None:
        target_date = datetime.date.today()

    analyzer = DailyAnalyzer(
        db=db,
        chat_fetch_func=get_daily_chat_logs_by_couple_id,
        analyze_func=analyze_daily,
        save_func=save_daily_couple_analysis_result,
        prompt_name="daily_nlu"
    )
    await run_daily_for_all(couple_ids, analyzer, target_date)
    # asyncio.run(run_daily_for_all(couple_ids, analyzer, target_date))

async def daily_aichat_analysis_for_all_users():
    user_ids = get_all_user_ids()
    today = datetime.date.today()

    analyzer = DailyAnalyzer(
        db=get_session(),
        chat_fetch_func=get_daily_ai_chat_logs_by_user_id,
        analyze_func=analyze_daily,
        save_func=save_daily_ai_analysis_result,
        prompt_name="daily_ai_nlu"
    )
    await run_daily_for_all(user_ids, analyzer, today)
    # asyncio.run(run_daily_for_all(user_ids, analyzer, today))

async def daily_couplechat_emotion_comparison_analysis_for_all_couples(target_date=None):
    """
    일간 커플 채팅과 감정 기록 비교 분석을 모든 커플에 대해 실행합니다.
    채팅에서 보인 감정과 기록된 감정의 일치도, 소통 패턴과 감정의 연관성 등을 분석합니다.
    """
    db = get_session()
    couple_ids = get_all_couple_ids(db)
    if target_date is None:
        target_date = datetime.date.today()

    analyzer = DailyAnalyzer(
        db=db,
        chat_fetch_func=get_daily_chat_logs_by_couple_id,
        emotion_fetch_func=get_daily_emotion_logs_by_couple_id,
        analyze_func=analyze_daily,
        save_func=save_daily_comparison_analysis_result,
        prompt_name="daily_comparison_prompt"
    )
    await run_daily_for_all(couple_ids, analyzer, target_date)
    logger.info(f"[일간 비교 분석] {len(couple_ids)}개 커플의 {target_date} 비교 분석 완료")

async def test_weekly_couplechat_analysis_from_start_date():
    start_date = datetime.datetime(2025, 7, 2, 4, 0, 0)

    for i in range(7):
        target_date = start_date + datetime.timedelta(days=i)
        print(f"[테스트] {target_date} 분석 시작")

        await daily_couplechat_analysis_for_all_couples(target_date)
        await daily_couplechat_emotion_comparison_analysis_for_all_couples(target_date)

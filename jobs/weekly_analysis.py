import asyncio
from datetime import datetime, timedelta
from db.crud import get_all_couple_ids, get_users_by_couple_id, load_daily_couple_stats, load_daily_ai_stats
from services.ai.analyzer import WeeklyAnalyzer
from db.result_saver import WeeklyResultSaver
from db.db import get_session

def get_week_dates(start_date: datetime.date) -> list[datetime.date]:
    return [start_date + timedelta(days=i) for i in range(7)]

async def run_all_weekly_analyses(start_date=None):
    session = get_session()

    # 커플 정보 로드
    couple_list = []
    couple_ids = get_all_couple_ids(session)
    for couple_id in couple_ids:
        user1_id, user2_id = get_users_by_couple_id(session, couple_id)
        couple_list.append((couple_id, user1_id, user2_id))

    # 주간 날짜 정의
    if start_date is None:
        start_date = datetime.today().date() - timedelta(days=7)
    week_dates = get_week_dates(start_date)

    # 분석기 생성
    saver = WeeklyResultSaver(db_session=session, week_dates=week_dates)
    analyzer = WeeklyAnalyzer(
        db=session,
        load_daily_couple_stats_func=load_daily_couple_stats,
        load_daily_ai_stats_func=load_daily_ai_stats,
        save_func=lambda c_id, u1, u2, result: saver.save(
            c_id, u1, u2, result
        )
    )

    # 모든 커플에 대해 실행
    for couple_id, user1_id, user2_id in couple_list:
        await analyzer.run(couple_id, user1_id, user2_id, week_dates)

async def test_run_seven_days_analysis():
    start_date = datetime(2025, 7, 1).date()  # 시작일
    
    week_start = start_date
    week_dates = [week_start + timedelta(days=i) for i in range(7)]

    print(f"\n📅 [WEEK 1] 주간 분석 기간: {week_start} ~ {week_dates[-1]}")
    await run_all_weekly_analyses(start_date)

if __name__ == "__main__":
    asyncio.run(run_all_weekly_analyses())

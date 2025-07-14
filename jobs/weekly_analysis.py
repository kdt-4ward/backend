from services.ai.analyzer_langchain import aggregate_weekly_stats, aggregate_weekly_ai_stats_by_day
from services.ai.weekly_analysis_pipeline import WeeklyAnalysisPipeline
from db.crud import get_all_couple_ids, get_users_by_couple_id

async def run_all_weekly_analyses(couple_list, week_dates):
    for couple in couple_list:
        couple_id = couple['couple_id']
        user1_id = couple['user_1']
        user2_id = couple['user_2']

        # 1. 일간분석 결과 불러오기
        daily_couple_stats = load_daily_couple_stats(couple_id, week_dates)
        print("=====daily_couple_stats=======")
        print(daily_couple_stats)
        print("===================================")
        daily_user1_ai_stats = load_daily_ai_stats(user1_id, week_dates)
        daily_user2_ai_stats = load_daily_ai_stats(user2_id, week_dates)

        if not daily_couple_stats and not daily_user1_ai_stats and not daily_user2_ai_stats:
            # 로그 및 건너뛰기
            continue

        # 2. 집계
        couple_weekly = aggregate_weekly_stats(daily_couple_stats)
        print("=====couple_weekly=======")
        print(couple_weekly)
        print("===================================")
        user1_ai_weekly = aggregate_weekly_ai_stats_by_day(daily_user1_ai_stats)
        user2_ai_weekly = aggregate_weekly_ai_stats_by_day(daily_user2_ai_stats)

        # 3. LLM 주간분석
        pipeline = WeeklyAnalysisPipeline()
        result = await pipeline.analyze(couple_weekly, user1_ai_weekly, user2_ai_weekly)
        print("==============최종 결과 ===================")
        print(result)
        print("=======================================")
        # 4. 저장
        save_weekly_analysis_result(couple_id, user1_id, user2_id, result, week_dates)


async def run_seven_weeks_analysis():
    start_date = datetime(2025, 7, 1).date()  # 시작일
    week_count = 7

    # 전체 커플 리스트 조회
    with SessionLocal() as db:
        couple_ids = get_all_couple_ids(db)
        couple_list = []
        for couple_id in couple_ids:
            user1, user2 = get_users_by_couple_id(db, couple_id)
            couple_list.append({
                "couple_id": couple_id,
                "user_1": user1,
                "user_2": user2
            })

    
    week_start = start_date
    week_dates = [week_start + timedelta(days=i) for i in range(7)]

    print(f"\n📅 [WEEK 1] 주간 분석 기간: {week_start} ~ {week_dates[-1]}")
    await run_all_weekly_analyses(couple_list, week_dates)

from sqlalchemy.orm import Session
from models.db_tables import CoupleDailyAnalysisResult, AIChatSummary, WeeklySolution, CoupleWeeklyAnalysisResult, CoupleWeeklyComparisonResult, CoupleWeeklyRecommendation
from db.db import SessionLocal
from datetime import datetime, timedelta
import json

# 1. 커플 채팅 요약 7일치 불러오기
def load_daily_couple_stats(couple_id: str, week_dates: list[datetime.date]) -> list[dict]:
    with SessionLocal() as db:
        summaries = db.query(CoupleDailyAnalysisResult).filter(
            CoupleDailyAnalysisResult.couple_id == couple_id,
            CoupleDailyAnalysisResult.date >= week_dates[0],
            CoupleDailyAnalysisResult.date < week_dates[-1] + timedelta(days=1)
        ).order_by(CoupleDailyAnalysisResult.created_at).all()
        print("=========================summary===============================")
        print(summaries)
        print("=========================-=============================================")
        return [json.loads(row.result) for row in summaries]

# 2. 유저별 AI 상담 요약 7일치 불러오기
def load_daily_ai_stats(user_id: str, week_dates: list[datetime.date]) -> list[dict]:
    with SessionLocal() as db:
        summaries = db.query(AIChatSummary).filter(
            AIChatSummary.user_id == user_id,
            AIChatSummary.created_at >= week_dates[0],
            AIChatSummary.created_at < week_dates[-1] + timedelta(days=1)
        ).order_by(AIChatSummary.created_at).all()

        return [json.loads(row.summary) for row in summaries]

# 3. 주간 분석 결과 저장
def save_weekly_analysis_result(couple_id: str, user1_id: str, user2_id: str, result: dict, week_dates: list[datetime.date]):
    with SessionLocal() as db:
        now = datetime.utcnow()

        # 커플 주간 요약 저장
        if result.get("주간커플분석") and result["주간커플분석"]["success"]:
            db.add(CoupleWeeklyAnalysisResult(
                couple_id=couple_id,
                week_start_date=week_dates[0],
                week_end_date=week_dates[-1],
                result=json.dumps(result["주간커플분석"]["result"], ensure_ascii=False),
                created_at=now
            ))
        # 유저1 AI 주간 요약 저장
        if result.get("개인분석", {}).get("user1", {}).get("success"):
            db.add(WeeklySolution(
                user_id=user1_id,
                content=result["개인분석"]["user1"]["result"],
                created_at=now
            ))

        # 유저2 AI 주간 요약 저장
        if result.get("개인분석", {}).get("user2", {}).get("success"):
            db.add(WeeklySolution(
                user_id=user2_id,
                content=result["개인분석"]["user2"]["result"],
                created_at=now
            ))

        # 비교분석 결과 저장
        if result.get("커플vsAI차이") and result["커플vsAI차이"]["success"]:
            db.add(CoupleWeeklyComparisonResult(
                couple_id=couple_id,
                week_start_date=week_dates[0],
                week_end_date=week_dates[-1],
                comparison=result["커플vsAI차이"]["result"],
                created_at=now
            ))

        # 추천 결과 저장
        if result.get("추천") and result["추천"]["success"]:
            parsed = result["추천"]["result"]
            db.add(CoupleWeeklyRecommendation(
                couple_id=couple_id,
                week_start_date=week_dates[0],
                week_end_date=week_dates[-1],
                advice=parsed.get("조언", ""),
                content_type=parsed.get("추천컨텐츠", {}).get("type"),
                content_title=parsed.get("추천컨텐츠", {}).get("제목"),
                content_reason=parsed.get("추천컨텐츠", {}).get("이유"),
                created_at=now
            ))
        db.commit()

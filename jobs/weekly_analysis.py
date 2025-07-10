from services.ai.analyzer_langchain import aggregate_weekly_stats, aggregate_weekly_ai_stats_by_day
from services.ai.weekly_analysis_pipeline import WeeklyAnalysisPipeline

async def run_all_weekly_analyses(couple_list, week_dates):
    for couple in couple_list:
        couple_id = couple['couple_id']
        user1_id = couple['user_1']
        user2_id = couple['user_2']

        # 1. 일간분석 결과 불러오기
        daily_couple_stats = load_daily_couple_stats(couple_id, week_dates)
        daily_user1_ai_stats = load_daily_ai_stats(user1_id, week_dates)
        daily_user2_ai_stats = load_daily_ai_stats(user2_id, week_dates)

        if not daily_couple_stats or not daily_user1_ai_stats or not daily_user2_ai_stats:
            # 로그 및 건너뛰기
            continue

        # 2. 집계
        couple_weekly = aggregate_weekly_stats(daily_couple_stats)
        user1_ai_weekly = aggregate_weekly_ai_stats_by_day(daily_user1_ai_stats)
        user2_ai_weekly = aggregate_weekly_ai_stats_by_day(daily_user2_ai_stats)

        # 3. LLM 주간분석
        pipeline = WeeklyAnalysisPipeline()
        result = await pipeline.analyze(couple_weekly, user1_ai_weekly, user2_ai_weekly)

        # 4. 저장
        save_weekly_analysis_result(couple_id, user1_id, user2_id, result)

def load_daily_couple_stats(couple_id, week_dates):
    # DB에서 couple_id, week_dates에 해당하는 일간분석 결과를 리스트로 반환
    pass

def load_daily_ai_stats(user_id, week_dates):
    # DB에서 user_id, week_dates에 해당하는 AI 일간분석 결과를 리스트로 반환
    pass

def save_weekly_analysis_result(couple_id, user1_id, user2_id, result):
    # WeeklySolution, CoupleChatSummary 등 결과 저장
    pass
import datetime
from utils.log_utils import get_logger

logger = get_logger(__name__)


class BaseAnalyzer:
    def __init__(self, analyze_func, save_func, prompt_name):
        self.analyze_func = analyze_func
        self.save_func = save_func
        self.prompt_name = prompt_name
    async def run(self, target_id, date):
        raise NotImplementedError

class DailyAnalyzer(BaseAnalyzer):
    def __init__(self, db, fetch_func, analyze_func, save_func, prompt_name):
        super().__init__(analyze_func, save_func, prompt_name)
        self.fetch_func = fetch_func
        self.db = db

    async def run(self, target_id, date):
        chat_logs = self.fetch_func(self.db, target_id, date)
        if not chat_logs:
            logger.warning(f"[DailyAnalyzer] {target_id}의 {date} 대화 없음")
            return
        messages = [f"{c['user_id']} :{c['content']} [{c['created_at']}]" if isinstance(c, dict) else c for c in chat_logs]
        try:
            result = await self.analyze_func(messages, self.prompt_name)
            self.save_func(self.db, target_id, date, result)
            logger.info(f"[DailyAnalyzer] {target_id}의 {(date - datetime.timedelta(days=1)).date()} 분석 저장 완료")
        except Exception as e:
            logger.error(f"[DailyAnalyzer] {target_id} 분석 실패: {e}")

from services.ai.analyzer_langchain import aggregate_weekly_stats, aggregate_weekly_ai_stats_by_day
from services.ai.weekly_analysis_pipeline import WeeklyAnalysisPipeline

class WeeklyAnalyzer:
    def __init__(
        self,
        db,
        load_daily_couple_stats_func,
        load_daily_ai_stats_func,
        save_func
    ):
        self.db = db
        self.load_daily_couple_stats_func = load_daily_couple_stats_func
        self.load_daily_ai_stats_func = load_daily_ai_stats_func
        self.save_func = save_func

    async def run(self, couple_id: str, user1_id: str, user2_id: str, week_dates: list[str]):
        daily_couple_stats = self.load_daily_couple_stats_func(self.db, couple_id, week_dates)
        daily_user1_stats = self.load_daily_ai_stats_func(self.db, user1_id, week_dates)
        daily_user2_stats = self.load_daily_ai_stats_func(self.db, user2_id, week_dates)

        if not daily_couple_stats and not daily_user1_stats and not daily_user2_stats:
            logger.warning(f"[WeeklyAnalyzer] {couple_id} - 데이터 부족으로 분석 스킵")
            return

        if not daily_couple_stats:
            logger.warning(f"[WeeklyAnalyzer] {couple_id} - couple chat 데이터 부족으로 분석 스킵")
            couple_weekly = {"result": "데이터 부족 분석 스킵"}
        else:
            couple_weekly = aggregate_weekly_stats(daily_couple_stats)

        if not daily_user1_stats:
            logger.warning(f"[WeeklyAnalyzer] {couple_id} - {user1_id} 님의 AI chat 데이터 부족으로 분석 스킵")
            user1_ai_weekly = {"result": "데이터 부족 분석 스킵"}
        else:
            user1_ai_weekly = aggregate_weekly_ai_stats_by_day(daily_user1_stats)
        
        if not daily_user2_stats:
            logger.warning(f"[WeeklyAnalyzer] {couple_id} - {user2_id} 님의 AI chat 데이터 부족으로 분석 스킵")
            user2_ai_weekly = {"result": "데이터 부족 분석 스킵"}
        else:
            user2_ai_weekly = aggregate_weekly_ai_stats_by_day(daily_user2_stats)

        pipeline = WeeklyAnalysisPipeline()
        result = await pipeline.analyze(couple_weekly, user1_ai_weekly, user2_ai_weekly)

        self.save_func(couple_id, user1_id, user2_id, result)
        logger.info(f"[WeeklyAnalyzer] {couple_id} 주간 분석 완료")
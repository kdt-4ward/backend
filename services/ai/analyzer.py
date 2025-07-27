import json
import datetime
import traceback
from utils.log_utils import get_logger
from db.crud import get_users_by_couple_id

logger = get_logger(__name__)


class BaseAnalyzer:
    def __init__(self, analyze_func, save_func, prompt_name):
        self.analyze_func = analyze_func
        self.save_func = save_func
        self.prompt_name = prompt_name
    async def run(self, target_id, date):
        raise NotImplementedError

class DailyAnalyzer(BaseAnalyzer):
    """
    일간 분석 및 일간 비교 분석을 모두 처리할 수 있는 통합 Analyzer.
    - chat_fetch_func: 채팅 로그를 가져오는 함수 (필수)
    - emotion_fetch_func: 감정 로그를 가져오는 함수 (없으면 일반 일간 분석, 있으면 비교 분석)
    - analyze_func: 분석 함수 (messages, emotions, prompt_name) 또는 (messages, prompt_name)
    - save_func: 결과 저장 함수
    - prompt_name: 사용할 프롬프트 이름
    """
    def __init__(
        self,
        db,
        chat_fetch_func,
        analyze_func,
        save_func,
        prompt_name,
        emotion_fetch_func=None
    ):
        super().__init__(analyze_func, save_func, prompt_name)
        self.chat_fetch_func = chat_fetch_func
        self.emotion_fetch_func = emotion_fetch_func
        self.db = db

    async def run(self, target_id, date):
        """
        param:
            target_id: 분석 대상 커플 id 또는 user_id
            date: 분석 날짜
        """
        if self.prompt_name == "daily_ai_nlu":
            user1_id = target_id
            user2_id = None
            couple_id = None  # AI 분석의 경우 couple_id는 None
        else:
            user1_id, user2_id = get_users_by_couple_id(self.db, target_id)
            couple_id = target_id  # 커플 분석의 경우 target_id가 couple_id

        chat_logs = self.chat_fetch_func(self.db, target_id, date)

        emotion_logs = None
        if self.emotion_fetch_func is not None:
            emotion_logs = self.emotion_fetch_func(self.db, target_id, date)

        # 일간 분석: 채팅 로그만 필요, 비교 분석: 채팅+감정 모두 필요
        if self.emotion_fetch_func is None:
            # 일반 일간 분석
            if not chat_logs:
                logger.warning(f"[DailyAnalyzer] {target_id}의 {date} 대화 없음")
                return
            logger.info(f"chat_logs: {chat_logs}")
            messages = [
                f"{c.get('user_id', c.get('role', 'Unknown'))} :{c['content']} [{c['created_at']}]" if isinstance(c, dict) else c
                for c in chat_logs
            ]
            try:
                logger.info(f"[DailyAnalyzer][{self.prompt_name}] {target_id}의 {date} 분석 시작")
                result = await self.analyze_func(messages, prompt_name=self.prompt_name, user1_id=user1_id, user2_id=user2_id)
                if self.prompt_name == "daily_nlu":
                    self.save_func(self.db, couple_id, date, result)
                else:
                    self.save_func(self.db, user1_id, date, result)
                logger.info(f"[DailyAnalyzer] {target_id}의 {date} 분석 저장 완료")
            except Exception as e:
                logger.error(f"[DailyAnalyzer] {target_id} 분석 실패: {e}")
                traceback.print_exc()
        else:
            # 비교 분석 (채팅+감정)
            if not chat_logs and not emotion_logs:
                logger.warning(f"[DailyAnalyzer] {target_id}의 {date} 데이터 없음")
                return

            messages = []
            if chat_logs:
                messages = [f"{c.get('user_id', c.get('role', 'Unknown'))} :{c['content']} [{c['created_at']}]" for c in chat_logs]
            emotions = []
            if emotion_logs:
                emotions = [f"{e['user_id']} :{e['emotion']} - {e['memo']} [{e['recorded_at']}]" for e in emotion_logs]
            try:
                result = await self.analyze_func(messages, emotions=emotions, prompt_name=self.prompt_name, user1_id=user1_id, user2_id=user2_id)
                self.save_func(self.db, target_id, date, result)
                logger.info(f"[DailyAnalyzer] {target_id}의 {date} 비교 분석 저장 완료")
            except Exception as e:
                logger.error(f"[DailyAnalyzer] {target_id} 비교 분석 실패: {e}")
                traceback.print_exc()

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
            logger.warning(f"[WeeklyAnalyzer] couple_id: {couple_id} - 모든 데이터 부족으로 주간 분석 스킵")
            return

        if not daily_couple_stats:
            logger.warning(f"[WeeklyAnalyzer] couple_id: {couple_id} - couple chat 데이터 부족으로 분석 스킵")
            couple_weekly = {"result": "데이터 부족 분석 스킵"}
        else:
            couple_weekly = aggregate_weekly_stats(daily_couple_stats)

        if not daily_user1_stats:
            logger.warning(f"[WeeklyAnalyzer] couple_id: {couple_id} - user1_id: {user1_id} 님의 AI chat 데이터 부족으로 분석 스킵")
            user1_ai_weekly = {"result": "데이터 부족 분석 스킵"}
        else:
            user1_ai_weekly = aggregate_weekly_ai_stats_by_day(daily_user1_stats)
        
        if not daily_user2_stats:
            logger.warning(f"[WeeklyAnalyzer] couple_id: {couple_id} - user2_id: {user2_id} 님의 AI chat 데이터 부족으로 분석 스킵")
            user2_ai_weekly = {"result": "데이터 부족 분석 스킵"}
        else:
            user2_ai_weekly = aggregate_weekly_ai_stats_by_day(daily_user2_stats)

        pipeline = WeeklyAnalysisPipeline(self.db)
        result = await pipeline.analyze(couple_weekly, user1_ai_weekly, user2_ai_weekly, couple_id, user1_id, user2_id)

        await self.save_func(couple_id, user1_id, user2_id, result)
        logger.info(f"[WeeklyAnalyzer] couple_id: {couple_id} 주간 분석 완료")
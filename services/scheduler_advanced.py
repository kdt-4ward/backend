from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
import logging
from jobs.process_analysis_data import process_daily_analysis_data, process_weekly_analysis_data

logger = logging.getLogger(__name__)

class AdvancedSchedulerService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.setup_jobs()
        self.setup_listeners()
    
    def setup_jobs(self):
        """작업 설정"""
        # 매일 오전 4시 일일 분석
        self.scheduler.add_job(
            self.run_daily_analysis,
            CronTrigger(hour=4, minute=0),
            id='daily_analysis',
            name='일일 분석',
            replace_existing=True
        )
        
        # 매주 월요일 오전 4시 주간 분석
        self.scheduler.add_job(
            self.run_weekly_analysis,
            CronTrigger(day_of_week='mon', hour=4, minute=0),
            id='weekly_analysis',
            name='주간 분석',
            replace_existing=True
        )
    
    def setup_listeners(self):
        """이벤트 리스너 설정"""
        self.scheduler.add_listener(self.job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
    
    def job_listener(self, event):
        """작업 실행 이벤트 리스너"""
        if event.exception:
            logger.error(f'작업 {event.job_id} 실행 중 오류: {event.exception}')
        else:
            logger.info(f'작업 {event.job_id} 성공적으로 실행됨')
    
    async def run_daily_analysis(self):
        """일일 분석 실행"""
        try:
            logger.info("일일 분석 시작...")
            await process_daily_analysis_data()
            logger.info("일일 분석 완료!")
        except Exception as e:
            logger.error(f"일일 분석 오류: {e}")
    
    async def run_weekly_analysis(self):
        """주간 분석 실행"""
        try:
            logger.info("주간 분석 시작...")
            await process_weekly_analysis_data()
            logger.info("주간 분석 완료!")
        except Exception as e:
            logger.error(f"주간 분석 오류: {e}")
    
    def start(self):
        """스케줄러 시작"""
        self.scheduler.start()
        logger.info("고급 스케줄러가 시작되었습니다.")
    
    def shutdown(self):
        """스케줄러 종료"""
        self.scheduler.shutdown()
        logger.info("고급 스케줄러가 종료되었습니다.")
    
    def get_jobs(self):
        """등록된 작업 목록 조회"""
        return self.scheduler.get_jobs()

# 전역 인스턴스
advanced_scheduler = AdvancedSchedulerService()
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import asyncio
import logging
from jobs.process_analysis_data import process_daily_analysis_data, process_weekly_analysis_data
from core.dependencies import get_db_session

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SchedulerService:
    def __init__(self):
        self.last_daily_run = None
        self.last_weekly_run = None
        self.running = False
    
    async def run_scheduled_tasks(self):
        """스케줄된 작업들을 실행"""
        self.running = True
        logger.info("스케줄러가 시작되었습니다.")
        
        while self.running:
            try:
                current_time = datetime.now()
                
                # 매일 오전 4시 정리 작업 (중복 실행 방지)
                if (current_time.hour == 4 and 
                    current_time.minute == 0 and
                    (self.last_daily_run is None or 
                     current_time.date() > self.last_daily_run.date())):
                    
                    logger.info("일일 분석 데이터 처리 시작...")
                    try:
                        await process_daily_analysis_data()
                        self.last_daily_run = current_time
                        logger.info("일일 분석 데이터 처리 완료!")
                    except Exception as e:
                        logger.error(f"일일 분석 데이터 처리 오류: {e}")
                
                # 매주 월요일 오전 4시 주간 분석 (중복 실행 방지)
                if (current_time.weekday() == 0 and  # 월요일
                    current_time.hour == 4 and 
                    current_time.minute == 0 and
                    (self.last_weekly_run is None or 
                     current_time.date() > self.last_weekly_run.date())):
                    
                    logger.info("주간 분석 데이터 처리 시작...")
                    try:
                        await process_weekly_analysis_data()
                        self.last_weekly_run = current_time
                        logger.info("주간 분석 데이터 처리 완료!")
                    except Exception as e:
                        logger.error(f"주간 분석 데이터 처리 오류: {e}")
                
                # 1분 대기
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"스케줄러 오류: {e}")
                await asyncio.sleep(60)
    
    def stop(self):
        """스케줄러 중지"""
        self.running = False
        logger.info("스케줄러가 중지되었습니다.")

# 전역 스케줄러 인스턴스
scheduler = SchedulerService()

async def start_scheduler():
    """스케줄러 시작"""
    await scheduler.run_scheduled_tasks()

def stop_scheduler():
    """스케줄러 중지"""
    scheduler.stop()

# FastAPI와 함께 사용하는 경우
async def run_scheduler_background():
    """백그라운드에서 스케줄러 실행"""
    try:
        await start_scheduler()
    except Exception as e:
        logger.error(f"백그라운드 스케줄러 오류: {e}")

# 독립 실행용
async def main():
    await start_scheduler()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단되었습니다.")
        stop_scheduler()
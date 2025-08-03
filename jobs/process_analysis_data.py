import asyncio
import logging
import sys
import os
import json
from datetime import datetime, timedelta

# 현재 스크립트의 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
sys.path.append(backend_dir)

from jobs.analysis_personality import run_trait_summary_for_all_users
from jobs.daily_analysis import (
    daily_couplechat_analysis_for_all_couples,
    daily_aichat_analysis_for_all_users,
    daily_couplechat_emotion_comparison_analysis_for_all_couples
)
from jobs.weekly_analysis import run_all_weekly_analyses
from db.crud import get_all_user_ids, get_all_couple_ids, get_users_by_couple_id
from db.db import get_session
from db.db_tables import Message, AIMessage, CoupleDailyAnalysisResult, AIDailyAnalysisResult, CoupleWeeklyAnalysisResult, DailyComparisonAnalysisResult

logger = logging.getLogger(__name__)

def get_couple_data_range(couple_id: str, db) -> tuple[datetime.date, datetime.date]:
    """각 커플의 데이터 범위를 반환합니다."""
    # 커플 채팅 데이터 범위
    first_couple_message = db.query(Message).filter_by(couple_id=couple_id).order_by(Message.created_at.asc()).first()
    last_couple_message = db.query(Message).filter_by(couple_id=couple_id).order_by(Message.created_at.desc()).first()
    
    # 커플의 유저들 가져오기
    user1_id, user2_id = get_users_by_couple_id(db, couple_id)
    
    # AI 채팅 데이터 범위
    first_ai_message = db.query(AIMessage).filter(
        AIMessage.couple_id == couple_id
    ).order_by(AIMessage.created_at.asc()).first()
    last_ai_message = db.query(AIMessage).filter(
        AIMessage.couple_id == couple_id
    ).order_by(AIMessage.created_at.desc()).first()
    
    # 전체 데이터 범위 계산
    start_date = None
    end_date = None
    
    if first_couple_message:
        start_date = first_couple_message.created_at.date()
    if first_ai_message:
        ai_start_date = first_ai_message.created_at.date()
        if start_date is None or ai_start_date < start_date:
            start_date = ai_start_date
    
    if last_couple_message:
        end_date = last_couple_message.created_at.date()
    if last_ai_message:
        ai_end_date = last_ai_message.created_at.date()
        if end_date is None or ai_end_date > end_date:
            end_date = ai_end_date
    
    return start_date, end_date

def get_week_dates_for_couple(start_date: datetime.date, end_date: datetime.date) -> list[datetime.date]:
    """각 커플의 첫 데이터 날짜를 기준으로 주간 분석 날짜들을 반환합니다."""
    week_start_dates = []
    current_week_start = start_date
    
    # 첫 데이터 날짜를 주의 시작으로 설정
    while current_week_start <= end_date:
        week_start_dates.append(current_week_start)
        current_week_start += timedelta(days=7)
    
    return week_start_dates

def get_couple_weekly_analysis_dates(couple_id: str, db) -> list[tuple[datetime.date, datetime.date]]:
    """각 커플의 주간 분석 기간들을 반환합니다. (시작일, 종료일) 튜플 리스트"""
    couple_start_date, couple_end_date = get_couple_data_range(couple_id, db)
    
    if not couple_start_date or not couple_end_date:
        return []
    
    weekly_periods = []
    current_week_start = couple_start_date
    
    while current_week_start <= couple_end_date:
        # 주의 시작일부터 6일 후까지 (총 7일)
        week_end = current_week_start + timedelta(days=6)
        
        weekly_periods.append((current_week_start, week_end))
        current_week_start += timedelta(days=7)
    
    return weekly_periods

def check_analysis_result_success(result_json: str) -> bool:
    """분석 결과의 success 필드를 확인합니다."""
    try:
        result = json.loads(result_json)
        return result.get("success", True)  # success 필드가 없으면 True로 간주
    except (json.JSONDecodeError, TypeError):
        return False

def get_failed_analysis_dates(db) -> dict:
    """실패한 분석 결과가 있는 날짜들을 반환합니다."""
    failed_dates = {
        "couple_daily": [],
        "ai_daily": [],
        "comparison_daily": []
    }
    
    # 커플 일간 분석 실패 확인
    couple_results = db.query(CoupleDailyAnalysisResult).all()
    for result in couple_results:
        if not check_analysis_result_success(result.result):
            failed_dates["couple_daily"].append({
                "couple_id": result.couple_id,
                "date": result.date.date()
            })
    
    # AI 일간 분석 실패 확인
    ai_results = db.query(AIDailyAnalysisResult).all()
    for result in ai_results:
        if not check_analysis_result_success(result.result):
            failed_dates["ai_daily"].append({
                "user_id": result.user_id,
                "date": result.date.date()
            })
    
    # 일간 비교 분석 실패 확인
    comparison_results = db.query(DailyComparisonAnalysisResult).all()
    for result in comparison_results:
        if not check_analysis_result_success(result.result):
            failed_dates["comparison_daily"].append({
                "couple_id": result.couple_id,
                "date": result.date.date()
            })
    
    return failed_dates

def get_dates_with_chat_but_no_analysis(db) -> dict:
    """채팅은 있지만 분석 결과가 없는 날짜들을 반환합니다."""
    missing_analysis = {
        "couple_daily": [],
        "ai_daily": [],
        "comparison_daily": []
    }
    
    # 커플 채팅 데이터 확인
    couple_ids = get_all_couple_ids(db)
    for couple_id in couple_ids:
        # 해당 커플의 모든 메시지 날짜 확인
        messages = db.query(Message).filter_by(couple_id=couple_id).all()
        message_dates = set(msg.created_at.date() for msg in messages)
        
        # 해당 커플의 분석 결과 날짜 확인
        analysis_results = db.query(CoupleDailyAnalysisResult).filter_by(couple_id=couple_id).all()
        analysis_dates = set(result.date.date() for result in analysis_results)
        
        # 채팅은 있지만 분석이 없는 날짜들
        missing_dates = message_dates - analysis_dates
        for date in missing_dates:
            missing_analysis["couple_daily"].append({
                "couple_id": couple_id,
                "date": date
            })
    
    # AI 채팅 데이터 확인
    user_ids = get_all_user_ids(db)
    for user_id in user_ids:
        # 해당 유저의 모든 AI 메시지 날짜 확인
        ai_messages = db.query(AIMessage).filter_by(user_id=user_id).all()
        ai_message_dates = set(msg.created_at.date() for msg in ai_messages)
        
        # 해당 유저의 AI 분석 결과 날짜 확인
        ai_analysis_results = db.query(AIDailyAnalysisResult).filter_by(user_id=user_id).all()
        ai_analysis_dates = set(result.date.date() for result in ai_analysis_results)
        
        # AI 채팅은 있지만 분석이 없는 날짜들
        missing_dates = ai_message_dates - ai_analysis_dates
        for date in missing_dates:
            missing_analysis["ai_daily"].append({
                "user_id": user_id,
                "date": date
            })
    
    return missing_analysis

async def reprocess_failed_analysis():
    """실패한 분석 결과들을 다시 처리합니다."""
    
    logger.info("🔄 실패한 분석 결과 재처리 시작")
    
    try:
        with get_session() as db:
            # 1. 실패한 분석 결과 확인
            failed_dates = get_failed_analysis_dates(db)
            logger.info(f" 실패한 분석 결과: 커플 일간 {len(failed_dates['couple_daily'])}개, AI 일간 {len(failed_dates['ai_daily'])}개, 비교 분석 {len(failed_dates['comparison_daily'])}개")
            
            # 2. 채팅은 있지만 분석이 없는 날짜 확인
            missing_analysis = get_dates_with_chat_but_no_analysis(db)
            logger.info(f" 누락된 분석: 커플 일간 {len(missing_analysis['couple_daily'])}개, AI 일간 {len(missing_analysis['ai_daily'])}개, 비교 분석 {len(missing_analysis['comparison_daily'])}개")
            
            # 3. 커플 일간 분석 재처리
            if failed_dates["couple_daily"] or missing_analysis["couple_daily"]:
                logger.info(" 커플 일간 분석 재처리 시작")
                all_couple_dates = set()
                
                # 실패한 분석 날짜들
                for item in failed_dates["couple_daily"]:
                    all_couple_dates.add((item["couple_id"], item["date"]))
                
                # 누락된 분석 날짜들
                for item in missing_analysis["couple_daily"]:
                    all_couple_dates.add((item["couple_id"], item["date"]))
                
                for couple_id, date in all_couple_dates:
                    logger.info(f"   📅 커플 {couple_id}의 {date} 일간 분석 재처리")
                    await daily_couplechat_analysis_for_all_couples(date)
            
            # 4. AI 일간 분석 재처리
            if failed_dates["ai_daily"] or missing_analysis["ai_daily"]:
                logger.info(" AI 일간 분석 재처리 시작")
                all_ai_dates = set()
                
                # 실패한 분석 날짜들
                for item in failed_dates["ai_daily"]:
                    all_ai_dates.add((item["user_id"], item["date"]))
                
                # 누락된 분석 날짜들
                for item in missing_analysis["ai_daily"]:
                    all_ai_dates.add((item["user_id"], item["date"]))
                
                for user_id, date in all_ai_dates:
                    logger.info(f"   📅 유저 {user_id}의 {date} AI 일간 분석 재처리")
                    await daily_aichat_analysis_for_all_users(target_date=date)
            
            # 5. 일간 비교 분석 재처리
            if failed_dates["comparison_daily"] or missing_analysis["comparison_daily"]:
                logger.info(" 일간 비교 분석 재처리 시작")
                all_comparison_dates = set()
                
                # 실패한 분석 날짜들
                for item in failed_dates["comparison_daily"]:
                    all_comparison_dates.add((item["couple_id"], item["date"]))
                
                # 누락된 분석 날짜들
                for item in missing_analysis["comparison_daily"]:
                    all_comparison_dates.add((item["couple_id"], item["date"]))
                
                for couple_id, date in all_comparison_dates:
                    logger.info(f"   📅 커플 {couple_id}의 {date} 비교 분석 재처리")
                    await daily_couplechat_emotion_comparison_analysis_for_all_couples(date)
        
        logger.info("✅ 실패한 분석 결과 재처리 완료")
        
    except Exception as e:
        logger.error(f"❌ 실패한 분석 결과 재처리 중 오류 발생: {e}")
        import traceback
        logger.error(f"상세 오류: {traceback.format_exc()}")
        raise

async def process_daily_analysis_data():
    """DB에 있는 데이터를 기간에 맞춰 분석합니다."""
    
    logger.info("🚀 일간 데이터 분석 처리 시작")
    
    try:
        # 2. 일간 분석 (확인 후 필요한 것만)
        logger.info("=" * 50)
        logger.info("2️⃣ 일간 분석 시작")
        logger.info("=" * 50)
        
        with get_session() as db:
            # 2-1. 실패한 분석 결과 확인
            failed_dates = get_failed_analysis_dates(db)
            logger.info(f" 실패한 분석 결과: 커플 일간 {len(failed_dates['couple_daily'])}개, AI 일간 {len(failed_dates['ai_daily'])}개, 비교 분석 {len(failed_dates['comparison_daily'])}개")
            
            # 2-2. 채팅은 있지만 분석이 없는 날짜 확인
            missing_analysis = get_dates_with_chat_but_no_analysis(db)
            logger.info(f" 누락된 분석: 커플 일간 {len(missing_analysis['couple_daily'])}개, AI 일간 {len(missing_analysis['ai_daily'])}개, 비교 분석 {len(missing_analysis['comparison_daily'])}개")
            
            # 2-3. 커플 일간 분석 (실패하거나 누락된 것만)
            if failed_dates["couple_daily"] or missing_analysis["couple_daily"]:
                logger.info("🔄 커플 일간 분석 시작")
                all_couple_dates = set()
                
                # 실패한 분석 날짜들
                for item in failed_dates["couple_daily"]:
                    all_couple_dates.add((item["couple_id"], item["date"]))
                
                # 누락된 분석 날짜들
                for item in missing_analysis["couple_daily"]:
                    all_couple_dates.add((item["couple_id"], item["date"]))
                
                for couple_id, date in all_couple_dates:
                    logger.info(f"   📅 커플 {couple_id}의 {date} 일간 분석 처리")
                    await daily_couplechat_analysis_for_all_couples(date, couple_ids=[couple_id])
                logger.info("✅ 커플 일간 분석 완료")
            else:
                logger.info("✅ 커플 일간 분석 - 처리할 항목 없음")
            
            # 2-4. AI 일간 분석 (실패하거나 누락된 것만)
            if failed_dates["ai_daily"] or missing_analysis["ai_daily"]:
                logger.info("🔄 AI 일간 분석 시작")
                all_ai_dates = set()
                
                # 실패한 분석 날짜들
                for item in failed_dates["ai_daily"]:
                    all_ai_dates.add((item["user_id"], item["date"]))
                
                # 누락된 분석 날짜들
                for item in missing_analysis["ai_daily"]:
                    all_ai_dates.add((item["user_id"], item["date"]))
                
                for user_id, date in all_ai_dates:
                    logger.info(f"   📅 유저 {user_id}의 {date} AI 일간 분석 처리")
                    await daily_aichat_analysis_for_all_users(target_date=date, user_ids=[user_id])
                logger.info("✅ AI 일간 분석 완료")
            else:
                logger.info("✅ AI 일간 분석 - 처리할 항목 없음")
            
            # 2-5. 일간 비교 분석 (실패하거나 누락된 것만)
            if failed_dates["comparison_daily"] or missing_analysis["comparison_daily"]:
                logger.info("🔄 일간 비교 분석 시작")
                all_comparison_dates = set()
                
                # 실패한 분석 날짜들
                for item in failed_dates["comparison_daily"]:
                    all_comparison_dates.add((item["couple_id"], item["date"]))
                
                # 누락된 분석 날짜들
                for item in missing_analysis["comparison_daily"]:
                    all_comparison_dates.add((item["couple_id"], item["date"]))
                
                for couple_id, date in all_comparison_dates:
                    logger.info(f"   📅 커플 {couple_id}의 {date} 비교 분석 처리")
                    await daily_couplechat_emotion_comparison_analysis_for_all_couples(date, couple_ids=[couple_id])
                logger.info("✅ 일간 비교 분석 완료")
            else:
                logger.info("✅ 일간 비교 분석 - 처리할 항목 없음")
        
        logger.info("✅ 일간 분석 완료")
    except Exception as e:
            logger.error(f"❌ 일간 데이터 분석 처리 중 오류 발생: {e}")
            import traceback
            logger.error(f"상세 오류: {traceback.format_exc()}")
            raise

async def process_weekly_analysis_data():
    """DB에 있는 데이터를 기간에 맞춰 분석합니다."""
    
    logger.info("🚀 주간 데이터 분석 처리 시작")
    
    try:
        # 3. 주간 분석 (각 커플별로 개별 처리)
        logger.info("=" * 50)
        logger.info("3️⃣ 주간 분석 시작")
        logger.info("=" * 50)
        
        with get_session() as db:
            couple_ids = get_all_couple_ids(db)
            
            for couple_id in couple_ids:
                logger.info(f"💕 커플 {couple_id} 주간 분석 시작")
                
                # 각 커플의 데이터 범위 확인
                couple_start_date, couple_end_date = get_couple_data_range(couple_id, db)
                
                if couple_start_date and couple_end_date:
                    logger.info(f"   📅 커플 {couple_id} 데이터 기간: {couple_start_date} ~ {couple_end_date}")
                    
                    # 각 커플의 주간 분석 기간들 계산
                    weekly_periods = get_couple_weekly_analysis_dates(couple_id, db)
                    
                    for i, (week_start, week_end) in enumerate(weekly_periods, 1):
                        logger.info(f"   📅 Week {i}: {week_start} ~ {week_end} 주간 분석 처리 중...")
                        
                        # 주간 분석 실행 (주 시작일을 기준으로)
                        await run_all_weekly_analyses(week_start, couple_ids=[couple_id])
                        logger.info(f"   ✅ Week {i} 주간 분석 완료")
                else:
                    logger.warning(f"   ⚠️ 커플 {couple_id}의 분석할 데이터가 없습니다.")
        
        logger.info("✅ 주간 분석 완료")
        
        # 4. 결과 요약
        logger.info("=" * 50)
        logger.info("4️⃣ 분석 결과 요약")
        logger.info("=" * 50)
        
        with get_session() as db:
            # 성향 분석 결과 확인
            user_ids = get_all_user_ids(db)
            logger.info(f"    성향 분석된 사용자 수: {len(user_ids)}명")
            
            # 커플 수 확인
            couple_ids = get_all_couple_ids(db)
            logger.info(f"   💕 분석된 커플 수: {len(couple_ids)}개")
            
            # 일간 분석 결과 확인
            couple_daily_count = db.query(CoupleDailyAnalysisResult).count()
            ai_daily_count = db.query(AIDailyAnalysisResult).count()
            comparison_daily_count = db.query(DailyComparisonAnalysisResult).count()
            logger.info(f"   📈 일간 분석 결과: 커플 {couple_daily_count}개, AI {ai_daily_count}개, 비교 분석 {comparison_daily_count}개")
            
            # 주간 분석 결과 확인
            weekly_count = db.query(CoupleWeeklyAnalysisResult).count()
            logger.info(f"   📊 주간 분석 결과: {weekly_count}개")
            
            # 각 커플별 상세 정보
            for couple_id in couple_ids:
                couple_start, couple_end = get_couple_data_range(couple_id, db)
                if couple_start and couple_end:
                    week_count = len(get_week_dates_for_couple(couple_start, couple_end))
                    logger.info(f"   💕 커플 {couple_id}: {couple_start} ~ {couple_end} ({week_count}주)")
        
        logger.info("🎉 모든 데이터 분석 처리 완료!")
        
    except Exception as e:
        logger.error(f"❌ 데이터 분석 처리 중 오류 발생: {e}")
        import traceback
        logger.error(f"상세 오류: {traceback.format_exc()}")
        raise

async def process_analysis_for_specific_period(start_date: datetime.date, end_date: datetime.date):
    """특정 기간의 데이터만 분석합니다."""
    
    logger.info(f"🚀 특정 기간 분석 시작: {start_date} ~ {end_date}")
    
    try:
        # 1. 성향 분석
        # logger.info("1️⃣ 성향 분석 시작")
        # await run_trait_summary_for_all_users()
        # logger.info("✅ 성향 분석 완료")
        
        # 2. 일간 분석 (확인 후 필요한 것만)
        logger.info("2️⃣ 일간 분석 시작")
        
        with get_session() as db:
            # 2-1. 실패한 분석 결과 확인
            failed_dates = get_failed_analysis_dates(db)
            logger.info(f" 실패한 분석 결과: 커플 일간 {len(failed_dates['couple_daily'])}개, AI 일간 {len(failed_dates['ai_daily'])}개, 비교 분석 {len(failed_dates['comparison_daily'])}개")
            
            # 2-2. 채팅은 있지만 분석이 없는 날짜 확인
            missing_analysis = get_dates_with_chat_but_no_analysis(db)
            logger.info(f" 누락된 분석: 커플 일간 {len(missing_analysis['couple_daily'])}개, AI 일간 {len(missing_analysis['ai_daily'])}개, 비교 분석 {len(missing_analysis['comparison_daily'])}개")
            
            # 2-3. 커플 일간 분석 (실패하거나 누락된 것만)
            if failed_dates["couple_daily"] or missing_analysis["couple_daily"]:
                logger.info("🔄 커플 일간 분석 시작")
                all_couple_dates = set()
                
                # 실패한 분석 날짜들
                for item in failed_dates["couple_daily"]:
                    all_couple_dates.add((item["couple_id"], item["date"]))
                
                # 누락된 분석 날짜들
                for item in missing_analysis["couple_daily"]:
                    all_couple_dates.add((item["couple_id"], item["date"]))
                
                for couple_id, date in all_couple_dates:
                    logger.info(f"   📅 커플 {couple_id}의 {date} 일간 분석 처리")
                    await daily_couplechat_analysis_for_all_couples(date, couple_ids=[couple_id])
                logger.info("✅ 커플 일간 분석 완료")
            else:
                logger.info("✅ 커플 일간 분석 - 처리할 항목 없음")
            
            # 2-4. AI 일간 분석 (실패하거나 누락된 것만)
            if failed_dates["ai_daily"] or missing_analysis["ai_daily"]:
                logger.info("🔄 AI 일간 분석 시작")
                all_ai_dates = set()
                
                # 실패한 분석 날짜들
                for item in failed_dates["ai_daily"]:
                    all_ai_dates.add((item["user_id"], item["date"]))
                
                # 누락된 분석 날짜들
                for item in missing_analysis["ai_daily"]:
                    all_ai_dates.add((item["user_id"], item["date"]))
                
                for user_id, date in all_ai_dates:
                    logger.info(f"   📅 유저 {user_id}의 {date} AI 일간 분석 처리")
                    await daily_aichat_analysis_for_all_users(target_date=date, user_ids=[user_id])
                logger.info("✅ AI 일간 분석 완료")
            else:
                logger.info("✅ AI 일간 분석 - 처리할 항목 없음")
            
            # 2-5. 일간 비교 분석 (실패하거나 누락된 것만)
            if failed_dates["comparison_daily"] or missing_analysis["comparison_daily"]:
                logger.info("🔄 일간 비교 분석 시작")
                all_comparison_dates = set()
                
                # 실패한 분석 날짜들
                for item in failed_dates["comparison_daily"]:
                    all_comparison_dates.add((item["couple_id"], item["date"]))
                
                # 누락된 분석 날짜들
                for item in missing_analysis["comparison_daily"]:
                    all_comparison_dates.add((item["couple_id"], item["date"]))
                
                for couple_id, date in all_comparison_dates:
                    logger.info(f"   📅 커플 {couple_id}의 {date} 비교 분석 처리")
                    await daily_couplechat_emotion_comparison_analysis_for_all_couples(date, couple_ids=[couple_id])
                logger.info("✅ 일간 비교 분석 완료")
            else:
                logger.info("✅ 일간 비교 분석 - 처리할 항목 없음")
        
        logger.info("✅ 일간 분석 완료")
        
        # 3. 주간 분석 (각 커플별로 개별 처리)
        logger.info("3️⃣ 주간 분석 시작")
        
        with get_session() as db:
            couple_ids = get_all_couple_ids(db)
            
            for couple_id in couple_ids:
                logger.info(f"💕 커플 {couple_id} 주간 분석 시작")
                
                # 각 커플의 주간 분석 기간들 확인 (특정 기간 내에서만)
                couple_start_date, couple_end_date = get_couple_data_range(couple_id, db)
                
                if couple_start_date and couple_end_date:
                    # 특정 기간과 겹치는 부분만 계산
                    analysis_start = max(couple_start_date, start_date)
                    analysis_end = min(couple_end_date, end_date)
                    
                    if analysis_start <= analysis_end:
                        weekly_periods = []
                        current_week_start = analysis_start
                        
                        while current_week_start <= analysis_end:
                            week_end = current_week_start + timedelta(days=6)
                            if week_end > analysis_end:
                                week_end = analysis_end
                            
                            weekly_periods.append((current_week_start, week_end))
                            current_week_start += timedelta(days=7)
                        
                        logger.info(f"   커플 {couple_id} 분석 기간: {analysis_start} ~ {analysis_end}")
                        logger.info(f"   📅 총 {len(weekly_periods)}주 분석 예정")
                        
                        for i, (week_start, week_end) in enumerate(weekly_periods, 1):
                            logger.info(f"   📅 Week {i}: {week_start} ~ {week_end} 주간 분석 처리 중...")
                            await run_all_weekly_analyses(week_start, couple_id=couple_id)
                            logger.info(f"   ✅ Week {i} 주간 분석 완료")
                    else:
                        logger.warning(f"   ⚠️ 커플 {couple_id}의 분석 기간이 지정된 기간과 겹치지 않습니다.")
                else:
                    logger.warning(f"   ⚠️ 커플 {couple_id}의 분석할 데이터가 없습니다.")
        
        logger.info("✅ 주간 분석 완료")
        logger.info("🎉 특정 기간 분석 완료!")
        
    except Exception as e:
        logger.error(f"❌ 특정 기간 분석 중 오류 발생: {e}")
        raise

if __name__ == "__main__":
    # 전체 시나리오 데이터 분석
    asyncio.run(process_analysis_data())
    
    # 또는 특정 기간만 분석하려면:
    # start_date = datetime(2025, 7, 18).date()
    # end_date = datetime(2025, 7, 24).date()
    # asyncio.run(process_analysis_for_specific_period(start_date, end_date)) 
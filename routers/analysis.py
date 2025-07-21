from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date, timedelta
import json

from db.db import get_session
from db.db_tables.analysis import (
    AIDailyAnalysisResult,
    CoupleDailyAnalysisResult,
    DailyComparisonAnalysisResult,
    CoupleWeeklyAnalysisResult,
    CoupleWeeklyRecommendation,
    CoupleWeeklyComparisonResult,
    UserTraitSummary,
    WeeklySolution
)

from db.crud import load_daily_couple_stats
from db.db_tables.user import User
from db.db_tables.couple import Couple
from services.ai.analyzer import aggregate_weekly_stats

router = APIRouter()

# ==================== 주간 분석 결과 ====================

@router.get("/weekly/couple/{couple_id}")
async def get_couple_weekly_analysis(
    couple_id: str,
    start_date: Optional[date] = Query(None, description="주 시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="주 종료 날짜 (YYYY-MM-DD)"),
    db: Session = Depends(get_session)
):
    """커플 주간 분석 결과 조회"""
    try:
        query = db.query(CoupleWeeklyAnalysisResult).filter(
            CoupleWeeklyAnalysisResult.couple_id == couple_id
        )
        
        if start_date:
            query = query.filter(CoupleWeeklyAnalysisResult.week_start_date >= start_date)
        if end_date:
            query = query.filter(CoupleWeeklyAnalysisResult.week_end_date <= end_date)
            
        results = query.order_by(CoupleWeeklyAnalysisResult.week_start_date.desc()).all()
        
        return {
            "success": True,
            "data": [
                {
                    "id": result.id,
                    "couple_id": result.couple_id,
                    "week_start_date": result.week_start_date.strftime("%Y-%m-%d"),
                    "week_end_date": result.week_end_date.strftime("%Y-%m-%d"),
                    "result": json.loads(result.result),
                    "created_at": result.created_at.isoformat(),
                    "modified_at": result.modified_at.isoformat()
                }
                for result in results
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"커플 주간 분석 조회 실패: {str(e)}")

@router.get("/weekly/comparison/{couple_id}")
async def get_weekly_comparison_analysis(
    couple_id: str,
    start_date: Optional[date] = Query(None, description="주 시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="주 종료 날짜 (YYYY-MM-DD)"),
    db: Session = Depends(get_session)
):
    """주간 비교 분석 결과 조회 (AI vs 커플 채팅)"""
    try:
        query = db.query(CoupleWeeklyComparisonResult).filter(
            CoupleWeeklyComparisonResult.couple_id == couple_id
        )
        
        if start_date:
            query = query.filter(CoupleWeeklyComparisonResult.week_start_date >= start_date)
        if end_date:
            query = query.filter(CoupleWeeklyComparisonResult.week_end_date <= end_date)
            
        results = query.order_by(CoupleWeeklyComparisonResult.week_start_date.desc()).all()
        
        return {
            "success": True,
            "data": [
                {
                    "id": result.id,
                    "couple_id": result.couple_id,
                    "week_start_date": result.week_start_date.strftime("%Y-%m-%d"),
                    "week_end_date": result.week_end_date.strftime("%Y-%m-%d"),
                    "comparison": result.comparison,
                    "created_at": result.created_at.isoformat()
                }
                for result in results
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"주간 비교 분석 조회 실패: {str(e)}")

@router.get("/weekly/recommendations/{couple_id}")
async def get_weekly_recommendations(
    couple_id: str,
    start_date: Optional[date] = Query(None, description="주 시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="주 종료 날짜 (YYYY-MM-DD)"),
    db: Session = Depends(get_session)
):
    """주간 추천 컨텐츠 조회"""
    try:
        query = db.query(CoupleWeeklyRecommendation).filter(
            CoupleWeeklyRecommendation.couple_id == couple_id
        )
        
        if start_date:
            query = query.filter(CoupleWeeklyRecommendation.week_start_date >= start_date)
        if end_date:
            query = query.filter(CoupleWeeklyRecommendation.week_end_date <= end_date)
            
        results = query.order_by(CoupleWeeklyRecommendation.week_start_date.desc()).all()
        
        return {
            "success": True,
            "data": [
                {
                    "id": result.id,
                    "couple_id": result.couple_id,
                    "week_start_date": result.week_start_date.strftime("%Y-%m-%d"),
                    "week_end_date": result.week_end_date.strftime("%Y-%m-%d"),
                    "advice": result.advice,
                    "content_type": result.content_type,
                    "content_title": result.content_title,
                    "content_reason": result.content_reason,
                    "created_at": result.created_at.isoformat()
                }
                for result in results
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"주간 추천 조회 실패: {str(e)}")


@router.get("/user/weekly-solutions/{user_id}")
async def get_user_weekly_solutions(
    user_id: str,
    start_date: Optional[date] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="종료 날짜 (YYYY-MM-DD)"),
    db: Session = Depends(get_session)
):
    """사용자 주간 솔루션 조회"""
    try:
        query = db.query(WeeklySolution).filter(
            WeeklySolution.user_id == user_id
        )
        
        if start_date:
            query = query.filter(WeeklySolution.created_at >= start_date)
        if end_date:
            query = query.filter(WeeklySolution.created_at <= end_date)
            
        results = query.order_by(WeeklySolution.created_at.desc()).all()
        
        return {
            "success": True,
            "data": [
                {
                    "id": result.id,
                    "user_id": result.user_id,
                    "content": result.content,
                    "created_at": result.created_at.isoformat()
                }
                for result in results
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"사용자 주간 솔루션 조회 실패: {str(e)}")

# ==================== 분석 통계 ====================

@router.get("/stats/{couple_id}")
async def get_analysis_stats(
    couple_id: str,
    end_date: Optional[date] = Query(None, description="종료 날짜 (YYYY-MM-DD)"),
    db: Session = Depends(get_session)
):
    """주간 통계 정보 조회"""
    try:
        # 총 분석 횟수
        end_date = end_date or datetime.now()
        week_dates = [end_date - timedelta(days=i) for i in reversed(range(7))]
        daily_couple_stats = load_daily_couple_stats(db, couple_id, week_dates)
        print("daily_couple_stats 결과",daily_couple_stats)
        weekly_stats = aggregate_weekly_stats(daily_couple_stats)
        print('weekly_stats 결과',weekly_stats)
        # INSERT_YOUR_CODE
        # weekly_stats["user_stats"]의 각 user별로, *_횟수 리스트를 sum해서 total로 저장
        user_stats = weekly_stats.get("user_stats", {})
        new_user_stats = {}

        for user_id, stats in user_stats.items():
            new_user_stats[user_id] = {}
            for key, value in stats.items():
                if key.endswith("횟수") and isinstance(value, list):
                    new_user_stats[user_id][key] = sum(value)
                elif key.endswith("전체샘플") and isinstance(value, list):
                    new_user_stats[user_id][key] = [sample for samples in value for sample in samples]
        weekly_stats["user_stats"] = new_user_stats

        return weekly_stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 통계 조회 실패: {str(e)}")

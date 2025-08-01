from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date, timedelta
import json

from db.db import get_session
from db.db_tables.analysis import (
    CoupleWeeklyAnalysisResult,
    CoupleWeeklyRecommendation,
)

from db.crud import load_daily_couple_stats, get_user_name, get_users_by_couple_id
from utils.user_mapping import replace_user_ids_with_names
from services.ai.analyzer import aggregate_weekly_stats


router = APIRouter()

# ==================== 주간 분석 결과 ====================

@router.get("/weekly/couple/analysis/{couple_id}")
async def get_couple_weekly_analysis(
    couple_id: str,
    end_date: Optional[date] = Query(None, description="주 종료 날짜 (YYYY-MM-DD)"),
    db: Session = Depends(get_session)
):
    """커플 주간 분석 결과 조회"""
    try:
        query = db.query(CoupleWeeklyAnalysisResult).filter(
            CoupleWeeklyAnalysisResult.couple_id == couple_id
        )
        
        if end_date:
            query = query.filter(CoupleWeeklyAnalysisResult.week_end_date <= end_date)
            
        result = query.order_by(CoupleWeeklyAnalysisResult.week_start_date.desc()).first()
        if result is None:
            return {
                "success": True,
                "data": None
            }
        
        analysis_result = json.loads(str(result.result)) if result.result is not None else {}

        if analysis_result:
            user1_id, user2_id = get_users_by_couple_id(db, couple_id)
            if user1_id and user2_id:  # None 체크 추가
                user1_name = get_user_name(db, user1_id)
                user2_name = get_user_name(db, user2_id)
                
                # positive_points와 negative_points가 리스트인 경우 각 항목을 처리
                if isinstance(analysis_result.get("positive_points"), list):
                    analysis_result["positive_points"] = [
                        replace_user_ids_with_names(str(point), user1_id, user1_name, user2_id, user2_name)
                        for point in analysis_result["positive_points"]
                    ]
                else:
                    analysis_result["positive_points"] = replace_user_ids_with_names(str(analysis_result["positive_points"]), user1_id, user1_name, user2_id, user2_name)
                
                if isinstance(analysis_result.get("negative_points"), list):
                    analysis_result["negative_points"] = [
                        replace_user_ids_with_names(str(point), user1_id, user1_name, user2_id, user2_name)
                        for point in analysis_result["negative_points"]
                    ]
                else:
                    analysis_result["negative_points"] = replace_user_ids_with_names(str(analysis_result["negative_points"]), user1_id, user1_name, user2_id, user2_name)
                
                analysis_result["summary"] = replace_user_ids_with_names(str(analysis_result["summary"]), user1_id, user1_name, user2_id, user2_name)

        return {
            "success": True,
            "data": {
                "week_start_date": result.week_start_date.strftime("%Y-%m-%d"),
                "week_end_date": result.week_end_date.strftime("%Y-%m-%d"),
                "result": analysis_result,
                "created_at": result.created_at.isoformat(),
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"커플 주간 분석 조회 실패: {str(e)}")

@router.get("/weekly/couple/solution/{couple_id}")
async def get_couple_weekly_solution(
    couple_id: str,
    end_date: Optional[date] = Query(None, description="주 종료 날짜 (YYYY-MM-DD)"),
    db: Session = Depends(get_session)
):
    """커플 주간 솔루션 조회"""
    try:
        result = db.query(CoupleWeeklyRecommendation).filter(
            CoupleWeeklyRecommendation.couple_id == couple_id
        ).order_by(CoupleWeeklyRecommendation.week_end_date.desc())

        if end_date:
            result = result.filter(
                CoupleWeeklyRecommendation.week_end_date <= end_date
            )

        result = result.first()
        
        user1_id, user2_id = get_users_by_couple_id(db, couple_id)
        user1_name = get_user_name(db, user1_id)
        user2_name = get_user_name(db, user2_id)

        cleaned_advice = replace_user_ids_with_names(str(result.advice), user1_id, user1_name, user2_id, user2_name)

        return {
            "success": True,
            "data": {
                "week_start_date": result.week_start_date.strftime("%Y-%m-%d"),
                "week_end_date": result.week_end_date.strftime("%Y-%m-%d"),
                "advice": cleaned_advice,
                "created_at": result.created_at.isoformat(),
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"커플 주간 분석 조회 실패: {str(e)}")

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
        
        # weekly_stats["user_stats"]의 각 user별로, *_횟수 리스트를 sum해서 total로 저장
        # analyzer_langchain.py의 aggregate_weekly_stats 구조에 맞게 합계 및 샘플 평탄화
        user_stats = weekly_stats.get("user_stats", {})
        new_user_stats = {}

        for user_id, stats in user_stats.items():
            new_user_stats[user_id] = {}
            for stat_key, stat_val in stats.items():
                # stat_key: affection, empathy, initiative, encouragement, conflict
                # stat_val: {"count": [...], "samples": [[...], ...]}
                count_list = stat_val.get("count", [])
                samples_list = stat_val.get("samples", [])
                new_user_stats[user_id][stat_key] = {
                    "total_count": sum(count_list),
                    "all_samples": [sample for samples in samples_list for sample in samples]
                }
        weekly_stats["user_stats"] = new_user_stats

        return weekly_stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 통계 조회 실패: {str(e)}")

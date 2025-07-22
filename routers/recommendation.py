from fastapi import APIRouter, Depends, HTTPException, Query
from jobs.content_recommendation import enhance_movie_info, enhance_song_info
from datetime import date
from sqlalchemy.orm import Session
from db.db import get_session
from db.db_tables.analysis import CoupleWeeklyRecommendation
from typing import Optional
from utils.log_utils import get_logger
import json
import asyncio

router = APIRouter()
logger = get_logger(__name__)

def get_weekly_recommendation_data(couple_id: str, date: Optional[date] = None, db: Session = None) -> CoupleWeeklyRecommendation:
    """DB에서 주간 추천 데이터 조회"""
    query = db.query(CoupleWeeklyRecommendation).filter(
        CoupleWeeklyRecommendation.couple_id == couple_id
    )
    
    if date:
        query = query.filter(CoupleWeeklyRecommendation.week_end_date <= date)
        
    return query.order_by(CoupleWeeklyRecommendation.week_end_date.desc()).first()

@router.get("/couple/{couple_id}/songs")
async def get_couple_song_recommendations(
    couple_id: str,
    date: Optional[date] = Query(None, description="조회 날짜 (YYYY-MM-DD)"),
    db: Session = Depends(get_session)
):
    """
    커플을 위한 주간 노래 추천만 제공합니다.
    
    - **couple_id**: 커플 ID
    - **start_date**: 주 시작 날짜 (선택사항)
    - **end_date**: 주 종료 날짜 (선택사항)
    """
    try:
        result = get_weekly_recommendation_data(couple_id, date, db)
        
        if result and result.song_title:
            # 기본 정보 구성
            recommendation_data = {
                    "id": result.id,
                    "couple_id": result.couple_id,
                    "week_start_date": result.week_start_date.strftime("%Y-%m-%d"),
                    "week_end_date": result.week_end_date.strftime("%Y-%m-%d"),
                    "created_at": result.created_at.isoformat(),
                }
            
            # 강화된 노래 데이터가 있으면 사용, 없으면 실시간으로 강화
            if result.enhanced_song_data:
                try:
                    song_data = json.loads(result.enhanced_song_data)
                    recommendation_data["song"] = song_data
                except:
                    # JSON 파싱 실패시 실시간으로 강화
                    recommendation_data["song"] = enhance_song_info(result.song_title, result.song_reason)
            else:
                # 강화된 데이터가 없으면 실시간으로 강화
                recommendation_data["song"] = enhance_song_info(result.song_title, result.song_reason)
            
            return {
                "success": True,
                "data": recommendation_data
            }
        
    except Exception as e:
        logger.error(f"주간 노래 추천 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"주간 노래 추천 조회 실패: {str(e)}")

@router.get("/couple/{couple_id}/movies")
async def get_couple_movie_recommendations(
    couple_id: str,
    date: Optional[date] = Query(None, description="조회 날짜 (YYYY-MM-DD)"),
    db: Session = Depends(get_session)
):
    """
    커플을 위한 주간 영화 추천만 제공합니다.
    
    - **couple_id**: 커플 ID
    - **start_date**: 주 시작 날짜 (선택사항)
    - **end_date**: 주 종료 날짜 (선택사항)
    """
    try:
        # DB에서 주간 추천 데이터 조회
        result = get_weekly_recommendation_data(couple_id, date, db)
        
        if result and result.movie_title:
            # 기본 정보 구성
            recommendation_data = {
                "id": result.id,
                "couple_id": result.couple_id,
                "week_start_date": result.week_start_date.strftime("%Y-%m-%d"),
                "week_end_date": result.week_end_date.strftime("%Y-%m-%d"),
                "created_at": result.created_at.isoformat(),
            }
            
            # 강화된 영화 데이터가 있으면 사용, 없으면 실시간으로 강화
            if result.enhanced_movie_data:
                try:
                    movie_data = json.loads(result.enhanced_movie_data)
                    recommendation_data["movie"] = movie_data
                except:
                    # JSON 파싱 실패시 실시간으로 강화
                    recommendation_data["movie"] = await enhance_movie_info(result.movie_title, result.movie_reason)
            else:
                # 강화된 데이터가 없으면 실시간으로 강화
                recommendation_data["movie"] = await enhance_movie_info(result.movie_title, result.movie_reason)
            
            return {
                "success": True,
                "data": recommendation_data
            }
        
    except Exception as e:
        logger.error(f"주간 영화 추천 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"주간 영화 추천 조회 실패: {str(e)}")

# 기존 전체 추천 라우터 (선택사항)
@router.get("/weekly/recommendations/{couple_id}")
async def get_weekly_recommendations(
    couple_id: str,
    start_date: Optional[date] = Query(None, description="주 시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="주 종료 날짜 (YYYY-MM-DD)"),
    db: Session = Depends(get_session)
):
    """주간 추천 컨텐츠 전체 조회 (영화 + 노래)"""
    try:
        result = get_weekly_recommendation_data(couple_id, date, db)
        
        if result:
            recommendation_data = {
                "id": result.id,
                "couple_id": result.couple_id,
                "week_start_date": result.week_start_date.strftime("%Y-%m-%d"),
                "week_end_date": result.week_end_date.strftime("%Y-%m-%d"),
                "advice": result.advice,
                "created_at": result.created_at.isoformat()
            }
            
            # 영화 정보 추가
            if result.movie_title:
                if result.enhanced_movie_data:
                    try:
                        movie_data = json.loads(result.enhanced_movie_data)
                        recommendation_data["movie"] = movie_data
                    except:
                        recommendation_data["movie"] = await enhance_movie_info(result.movie_title, result.movie_reason)
                else:
                    recommendation_data["movie"] = await enhance_movie_info(result.movie_title, result.movie_reason)
            
            # 노래 정보 추가
            if result.song_title:
                if result.enhanced_song_data:
                    try:
                        song_data = json.loads(result.enhanced_song_data)
                        recommendation_data["song"] = song_data
                    except:
                        recommendation_data["song"] = enhance_song_info(result.song_title, result.song_reason)
                else:
                    recommendation_data["song"] = enhance_song_info(result.song_title, result.song_reason)
            
        return {
            "success": True,
            "data": recommendation_data
        }
        
    except Exception as e:
        logger.error(f"주간 추천 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"주간 추천 조회 실패: {str(e)}")

@router.get("/health")
async def health_check():
    """추천 시스템 상태 확인"""
    return {"status": "healthy", "service": "couple_recommendation_system"}

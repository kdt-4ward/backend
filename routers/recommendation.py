from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, Dict, Any
from pydantic import BaseModel
from jobs.content_recomend import (
    get_couple_recommendations,
    get_daily_couple_recommendation,
    analyze_couple_situation
)

router = APIRouter()


class RecommendationResponse(BaseModel):
    couple_id: int
    analysis: Dict[str, Any]
    recommendations: Dict[str, Any]


class DailyRecommendationResponse(BaseModel):
    couple_id: int
    analysis: Dict[str, Any]
    recommendations: Dict[str, Any]
    daily: Dict[str, Any]


class CoupleAnalysisResponse(BaseModel):
    couple_id: int
    relationship_duration_days: int
    dominant_emotion: str
    relationship_status: str
    recent_emotions: Dict[str, int]
    post_count: int


@router.get("/couple/{couple_id}", response_model=RecommendationResponse)
async def get_couple_content_recommendations(
    couple_id: int,
    content_type: str = Query("both", description="추천할 콘텐츠 타입: songs, movies, both")
):
    """
    커플을 위한 맞춤형 노래와 영화 추천을 제공합니다.
    
    - **couple_id**: 커플 ID
    - **content_type**: 추천할 콘텐츠 타입 (songs, movies, both)
    
    반환되는 추천:
    - 감정 기반 노래/영화 추천
    - 관계 상황 기반 노래/영화 추천
    - 특별한 상황별 활동 추천
    """
    try:
        result = get_couple_recommendations(couple_id, content_type)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"추천 생성 중 오류가 발생했습니다: {str(e)}")


@router.get("/couple/{couple_id}/daily", response_model=DailyRecommendationResponse)
async def get_daily_couple_recommendations(couple_id: int):
    """
    커플을 위한 일일 맞춤형 추천을 제공합니다.
    
    - **couple_id**: 커플 ID
    
    반환되는 추천:
    - 기본 노래/영화 추천
    - 오늘의 팁
    - 활동 제안
    """
    try:
        result = get_daily_couple_recommendation(couple_id)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"일일 추천 생성 중 오류가 발생했습니다: {str(e)}")


@router.get("/couple/{couple_id}/analysis", response_model=CoupleAnalysisResponse)
async def get_couple_situation_analysis(couple_id: int):
    """
    커플의 현재 상황을 분석합니다.
    
    - **couple_id**: 커플 ID
    
    분석 결과:
    - 관계 기간
    - 주요 감정
    - 관계 상황 (새로운 커플, 장기 커플, 어려운 시기)
    - 최근 감정 분포
    - 최근 포스트 수
    """
    try:
        result = analyze_couple_situation(couple_id)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"상황 분석 중 오류가 발생했습니다: {str(e)}")


@router.get("/couple/{couple_id}/songs")
async def get_couple_song_recommendations(couple_id: int):
    """
    커플을 위한 노래 추천만 제공합니다.
    
    - **couple_id**: 커플 ID
    """
    try:
        result = get_couple_recommendations(couple_id, "songs")
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"노래 추천 생성 중 오류가 발생했습니다: {str(e)}")


@router.get("/couple/{couple_id}/movies")
async def get_couple_movie_recommendations(couple_id: int):
    """
    커플을 위한 영화 추천만 제공합니다.
    
    - **couple_id**: 커플 ID
    """
    try:
        result = get_couple_recommendations(couple_id, "movies")
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"영화 추천 생성 중 오류가 발생했습니다: {str(e)}")


@router.get("/health")
async def health_check():
    """추천 시스템 상태 확인"""
    return {"status": "healthy", "service": "couple_recommendation_system"}

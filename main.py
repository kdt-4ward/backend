from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import router as api_router
from db.db_tables import Base
from db.db import engine
from core.settings import settings
from db.db_utils import create_database_if_not_exists, drop_database
from test_data.seed_data import insert_test_data_to_db
from test_data.insert_scenario_data import insert_scenario_data
from jobs.daily_analysis import test_weekly_couplechat_analysis_from_start_date
from test_data.process_analysis_data import process_analysis_data
import logging
import sys

def create_daily_analysis_result_json():
    from core.dependencies import get_db_session
    from db.crud import get_all_couple_ids
    from jobs.daily_analysis import daily_couplechat_analysis_for_all_couples
    from services.ai.analyzer import DailyAnalyzer
    from services.ai.analyzer_langchain import analyze_daily
    from db.db_tables import CoupleDailyAnalysisResult, CoupleWeeklyRecommendation, CoupleWeeklyComparisonResult
    import json
    db = get_db_session()
    couple_ids = get_all_couple_ids(db)
    daily_analysis_data = db.query(CoupleDailyAnalysisResult).all()
    weekly_recommendation_data = db.query(CoupleWeeklyRecommendation).all()
    weekly_comparison_data = db.query(CoupleWeeklyComparisonResult).all()
    
    # SQLAlchemy 객체를 딕셔너리로 변환
    serializable_daily_data = []
    for item in daily_analysis_data:
        serializable_daily_data.append({
            "id": item.id,
            "couple_id": item.couple_id,
            "date": item.date.isoformat() if item.date else None,
            "result": item.result,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "modified_at": item.modified_at.isoformat() if item.modified_at else None
        })
    
    with open("results/daily_analysis_result.json", "w") as f:
        json.dump(serializable_daily_data, f, ensure_ascii=False, indent=4)
    
    serializable_weekly_data = []
    for item in weekly_recommendation_data:
        serializable_weekly_data.append({
            "id": item.id,
            "couple_id": item.couple_id,
            "week_start_date": item.week_start_date.isoformat() if item.week_start_date else None,
            "week_end_date": item.week_end_date.isoformat() if item.week_end_date else None,
            "advice": item.advice,
            "song_title": item.song_title,
            "song_reason": item.song_reason,
            "movie_title": item.movie_title,
            "movie_reason": item.movie_reason,
            "enhanced_song_data": item.enhanced_song_data,
            "enhanced_movie_data": item.enhanced_movie_data,
        })
    
    with open("results/weekly_recommendation_result.json", "w") as f:
        json.dump(serializable_weekly_data, f, ensure_ascii=False, indent=4)

    serializable_comparison_data = []
    for item in weekly_comparison_data:
        serializable_comparison_data.append({
            "id": item.id,
            "couple_id": item.couple_id,
            "week_start_date": item.week_start_date.isoformat() if item.week_start_date else None,
            "week_end_date": item.week_end_date.isoformat() if item.week_end_date else None,
            "comparison": item.comparison,
        })
    
    with open("results/weekly_comparison_result.json", "w") as f:
        json.dump(serializable_comparison_data, f, ensure_ascii=False, indent=4)
    db.close()
    
log_format = "[%(asctime)s][%(levelname)s][%(name)s] %(message)s"
date_format = "%Y-%m-%d %H:%M:%S"

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter(fmt=log_format, datefmt=date_format))

logging.basicConfig(
    level=logging.INFO,
    handlers=[console_handler]
)

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug
)

@app.get("/")
def health_check():
    return {"status": "ok"}

@app.on_event("startup")
async def on_startup():
#     insert_test_data_to_db()
    # 데이터베이스 초기화
    drop_database()
    create_database_if_not_exists()
    Base.metadata.create_all(bind=engine)

    # # ## 시나리오 데이터 삽입
    insert_scenario_data()

    ## 시나리오 데이터 분석
    try:
        await process_analysis_data()
    except Exception as e:
        logging.error(f"데이터 분석 처리 실패: {e}")

    # # db 일간분석 결과 json 파일 생성
    # create_daily_analysis_result_json()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(api_router)

# 임시 테스트용 로컬 파일 등록
# AWS S3에 연결 시 삭제
# from fastapi.staticfiles import StaticFiles
# from routers import upload  
# app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")  # 정적 파일 서빙

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


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(api_router)

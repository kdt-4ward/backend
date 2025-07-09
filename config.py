from db.db import get_engine
from fastapi import APIRouter
from asyncio import Semaphore
from core.settings import settings
import logging
import os
from logging.handlers import TimedRotatingFileHandler

LOG_DIR = "log"
os.makedirs(LOG_DIR, exist_ok=True)

log_format = "[%(asctime)s][%(levelname)s][%(name)s] %(message)s"
date_format = "%Y-%m-%d %H:%M:%S"

console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(fmt=log_format, datefmt=date_format))

file_handler = TimedRotatingFileHandler(
    filename=os.path.join(LOG_DIR, "service.log"),
    when="midnight", interval=1, backupCount=30, encoding="utf-8"
)
file_handler.setFormatter(logging.Formatter(fmt=log_format, datefmt=date_format))

logging.basicConfig(
    level=logging.INFO,
    handlers=[console_handler, file_handler]
)

engine = get_engine()
router = APIRouter()

# 한번에 request 처리 갯수
semaphore = Semaphore(5)




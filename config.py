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

# 먼저 root 로거 초기화
root_logger = logging.getLogger()
if root_logger.hasHandlers():
    root_logger.handlers.clear()

# 핸들러 재설정
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(fmt=log_format, datefmt=date_format))

file_handler = TimedRotatingFileHandler(
    filename=os.path.join(LOG_DIR, "service.log"),
    when="midnight", interval=1, backupCount=30, encoding="utf-8"
)
file_handler.setFormatter(logging.Formatter(fmt=log_format, datefmt=date_format))

# root logger에 핸들러 연결
root_logger.setLevel(logging.INFO)
root_logger.addHandler(console_handler)
root_logger.addHandler(file_handler)


engine = get_engine()
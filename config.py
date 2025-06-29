from openai import AsyncOpenAI
from core.db import get_engine
from core.connection_manager import ConnectionManager
from fastapi import APIRouter
from asyncio import Semaphore
from core.settings import settings

engine = get_engine()
router = APIRouter()

# 한번에 request 처리 갯수
semaphore = Semaphore(3)




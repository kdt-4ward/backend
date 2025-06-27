from openai import AsyncOpenAI
from backend.core.db import get_engine
from backend.core.settings import settings
from backend.core.connection_manager import ConnectionManager
from fastapi import APIRouter
from asyncio import Semaphore

client = AsyncOpenAI(api_key=settings.openai_api_key)
engine = get_engine()

router = APIRouter()
manager = ConnectionManager()
# 한번에 request 처리 갯수
semaphore = Semaphore(3)




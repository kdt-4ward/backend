# core/concurrency.py
from asyncio import Semaphore

# 동시에 처리 가능한 요청 수 제한
semaphore = Semaphore(10)

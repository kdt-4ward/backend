from celery import Celery
from core.settings import settings

celery_app = Celery(
    "worker",
    broker=f"redis://{settings.redis_host}:{settings.redis_port}/0",
    backend=f"redis://{settings.redis_host}:{settings.redis_port}/0"
)

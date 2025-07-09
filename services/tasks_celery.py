from core.celery_worker import celery_app
from core.bot import PersonaChatBot
from services.rag_search import process_incremental_faiss_embedding
import asyncio

@celery_app.task
def run_check_and_summarize(user_id: str):
    bot = PersonaChatBot(user_id)
    asyncio.run(bot.check_and_summarize_if_needed())

@celery_app.task
def run_embedding(user_id: str):
    asyncio.run(process_incremental_faiss_embedding(user_id))

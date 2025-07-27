from core.celery_worker import celery_app
from core.bot import PersonaChatBot
from services.rag_search import process_incremental_faiss_embedding
import asyncio

@celery_app.task
def run_check_and_summarize(user_id: str):
    run_check_summary_async(user_id)

@celery_app.task
def run_embedding(user_id: str):
    run_embedding_async(user_id)

def run_check_summary_async(user_id: str):
    asyncio.run(PersonaChatBot(user_id).check_and_summarize_if_needed())

def run_embedding_async(user_id: str):
    asyncio.run(process_incremental_faiss_embedding(user_id))

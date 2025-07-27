from core.settings import settings
from db.db_tables import AIChatSummary
from db.db import SessionLocal
from core.redis_v2.redis import redis_client

class AISummaryProvider:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.redis_key = f"chat_summary:{user_id}"

    def get(self) -> str:
        raw = redis_client.get(self.redis_key)
        if raw:
            return raw

        with SessionLocal() as db:
            latest = db.query(AIChatSummary)\
                .filter_by(user_id=self.user_id)\
                .order_by(AIChatSummary.created_at.desc())\
                .first()
            if latest:
                redis_client.set(self.redis_key, latest.summary, ex=3600 * 6)
                return latest.summary
        return ""

    def set(self, summary: str):
        redis_client.set(self.redis_key, summary, ex=3600 * 6)

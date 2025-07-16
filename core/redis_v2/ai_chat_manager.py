from core.redis_v2.redis import RedisAIHistory
from db.db_tables import AIMessage, AIChatSummary
from db.db import SessionLocal
from sqlalchemy.exc import SQLAlchemyError

class AIChatHistoryManager:
    def __init__(self, user_id: str, couple_id: str,
                 prompt_provider: callable,
                 summary_provider: callable):
        self.user_id = user_id
        self.couple_id = couple_id
        self.prompt_provider = prompt_provider
        self.summary_provider = summary_provider
        self.redis = RedisAIHistory()

    def _fallback_from_db(self) -> tuple[str, list[dict]]:
        try:
            with SessionLocal() as db:
                summary_obj = db.query(AIChatSummary)\
                    .filter_by(user_id=self.user_id)\
                    .order_by(AIChatSummary.created_at.desc()).first()
                summary = summary_obj.summary if summary_obj else None
                last_msg_id = summary_obj.last_msg_id if summary_obj else None

                messages = db.query(AIMessage).filter(
                    AIMessage.user_id == self.user_id,
                    AIMessage.id > last_msg_id if last_msg_id else True
                ).order_by(AIMessage.created_at).all()

                chat_msgs = [{"role": m.role, "content": m.content, "id": m.id} for m in messages]
                return summary, chat_msgs
        except SQLAlchemyError as e:
            print(f"[DB fallback error] {e}")
            return None, []

    def load(self) -> list[dict]:
        history = self.redis.get(self.user_id)
        if not history:
            summary, chat_msgs = self._fallback_from_db()
            history = [self.prompt_provider()]
            if summary:
                history.append({"role": "summary", "content": summary})
            history.extend(chat_msgs)
            self.save(history)
        else:
            history = self.ensure_prompt_summary(history)
        return history

    def save(self, history: list[dict]):
        history = self.ensure_prompt_summary(history)
        self.redis.set(self.user_id, history)

    def append(self, message: dict):
        history = self.load()
        history.append(message)
        self.save(history)

    def clear(self):
        self.redis.clear(self.user_id)

    def ensure_prompt_summary(self, history: list[dict]) -> list[dict]:
        others = [h for h in history if h["role"] not in ("system", "summary")]
        result = [self.prompt_provider()]
        summary = self.summary_provider()
        if summary:
            result.append({"role": "summary", "content": summary})
        result.extend(others)
        return result
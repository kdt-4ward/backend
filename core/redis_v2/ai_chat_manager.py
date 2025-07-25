import asyncio
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

                chat_msgs = [{"role": m.role, "content": m.content, "id": m.id, "name": m.name} for m in messages]
                return summary, chat_msgs
        except SQLAlchemyError as e:
            print(f"[DB fallback error] {e}")
            return None, []

    async def load(self, user_message: str = None) -> list[dict]:
        """system prompt를 제외한 대화 기록만 로드 (function 메시지는 유지)"""
        history = self.redis.get(self.user_id)
        if not history:
            summary, chat_msgs = self._fallback_from_db()
            history = []
            if summary:
                history.append({"role": "summary", "content": summary})
            history.extend(chat_msgs)
            await self.save(history)
        else:
            # system prompt만 제거하고 function, summary, user, assistant 메시지는 유지
            history = [h for h in history if h["role"] not in ("system",)]
            history = await self.ensure_summary(history)
        return history

    async def save(self, history: list[dict]):
        """system prompt를 제외하고 저장 (function 메시지는 유지)"""
        # system prompt만 제거
        history = [h for h in history if h["role"] not in ("system",)]
        history = await self.ensure_summary(history)
        self.redis.set(self.user_id, history)

    async def append(self, message: dict):
        """새 메시지 추가 (system prompt는 추가하지 않음)"""
        if message["role"] != "system":
            history = await self.load()
            history.append(message)
            await self.save(history)

    def clear(self):
        self.redis.clear(self.user_id)

    async def ensure_summary(self, history: list[dict]) -> list[dict]:
        """summary는 유지하되 system prompt는 제외"""
        others = [h for h in history if h["role"] not in ("system", "summary")]
        result = []
        summary = self.summary_provider()
        if summary:
            result.append({"role": "summary", "content": summary})
        result.extend(others)
        return result

    async def get_full_history_for_openai(self, user_message: str = None) -> list[dict]:
        """OpenAI API 호출용 전체 히스토리 (system prompt 포함, function 메시지 유지)"""
        # 저장된 대화 기록 로드 (동기적으로)
        history = self.redis.get(self.user_id)
        if not history:
            summary, chat_msgs = self._fallback_from_db()
            history = []
            if summary:
                history.append({"role": "summary", "content": summary})
            history.extend(chat_msgs)
        
        # system prompt만 제거하고 function, user, assistant, summary 메시지는 유지
        history = [h for h in history if h["role"] not in ("system",)]
        
        # 동적 system prompt 생성 (비동기)
        if asyncio.iscoroutinefunction(self.prompt_provider):
            system_prompt = await self.prompt_provider(user_message)
        else:
            system_prompt = self.prompt_provider()
        
        # system prompt + 저장된 대화 기록 (function 메시지 포함)
        return [system_prompt] + history
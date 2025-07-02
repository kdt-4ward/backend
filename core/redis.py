import json
import redis
from core.settings import settings
from models.db_models import Couple, AIMessage, Message
from core.db import SessionLocal

# Redis 연결
redis_client = redis.StrictRedis(host=settings.redis_host, port=settings.redis_port, db=0, decode_responses=True)

class RedisAIHistory:
    PREFIX = "chatbot:history"

    @classmethod
    def _key(cls, user_id: str) -> str:
        return f"{cls.PREFIX}:{user_id}"

    @classmethod
    def get_history(cls, user_id: str) -> list:
        raw = redis_client.get(cls._key(user_id))
        if raw:
            return json.loads(raw)
        # Redis에 없으면 DB에서 로드
        history = cls._load_from_db(user_id)
        cls.set_history(user_id, history)
        return history

    @classmethod
    def _load_from_db(cls, user_id: str) -> list:
        with SessionLocal() as db:
            rows = db.query(AIMessage).filter_by(user_id=user_id).order_by(AIMessage.created_at).all()
            return [{"role": row.role, "content": row.content} for row in rows]

    @classmethod
    def set_history(cls, user_id: str, history: list):
        redis_client.set(cls._key(user_id), json.dumps(history), ex=3600)

    @classmethod
    def append(cls, user_id: str, message: dict):
        history = cls.get_history(user_id)
        history.append(message)
        cls.set_history(user_id, history)

    @classmethod
    def clear(cls, user_id: str):
        redis_client.delete(cls._key(user_id))


class RedisCoupleHistory:
    PREFIX = "chatroom:history"

    @classmethod
    def _key(cls, couple_id: str) -> str:
        return f"{cls.PREFIX}:{couple_id}"

    @classmethod
    def get_history(cls, couple_id: str) -> list:
        raw = redis_client.get(cls._key(couple_id))
        if raw:
            return json.loads(raw)
        # ✅ Redis에 없으면 DB에서 로드
        history = cls._load_from_db(couple_id)
        cls.set_history(couple_id, history)
        return history

    @classmethod
    def _load_from_db(cls, couple_id: str) -> list:
        with SessionLocal() as db:
            rows = db.query(Message).filter_by(couple_id=couple_id).order_by(Message.created_at).all()
            return [{"user_id": row.user_id, "content": row.content} for row in rows]

    @classmethod
    def set_history(cls, couple_id: str, history: list):
        redis_client.set(cls._key(couple_id), json.dumps(history), ex=3600)

    @classmethod
    def append(cls, couple_id: str, message: dict):
        history = cls.get_history(couple_id)
        history.append(message)
        cls.set_history(couple_id, history)

    @classmethod
    def clear(cls, couple_id: str):
        redis_client.delete(cls._key(couple_id))


def save_couple_mapping(user1: str, user2: str, couple_id: str):
    redis_client.set(f"chatbot:couple:user:{user1}", couple_id)
    redis_client.set(f"chatbot:couple:user:{user2}", couple_id)
    redis_client.set(f"chatbot:couple:pair:{couple_id}", json.dumps([user1, user2]))

def load_couple_mapping(user_id: str):
    couple_id = redis_client.get(f"chatbot:couple:user:{user_id}")
    if couple_id:
        pair_json = redis_client.get(f"chatbot:couple:pair:{couple_id}")
        if pair_json:
            user1, user2 = json.loads(pair_json)
            partner = user2 if user_id == user1 else user1
            return couple_id, partner
    # Redis에 없으면 DB 조회
    with SessionLocal() as db:
        couple = db.query(Couple).filter((Couple.user_1 == user_id) | (Couple.user_2 == user_id)).first()
        if not couple:
            return None, None

        couple_id = couple.couple_id
        user1 = couple.user_1
        user2 = couple.user_2
        save_couple_mapping(user1, user2, couple_id)  # Redis 저장
        partner = user2 if user_id == user1 else user1
        return couple_id, partner
import json
import redis
from core.settings import settings

# Redis 연결
redis_client = redis.StrictRedis(host=settings.redis_host, port=settings.redis_port, db=0, decode_responses=True)

class RedisChatHistory:
    PREFIX = "chatbot:history"

    @classmethod
    def _key(cls, couple_id: str) -> str:
        return f"{cls.PREFIX}:{couple_id}"

    @classmethod
    def get_history(cls, couple_id: str) -> list:
        raw = redis_client.get(cls._key(couple_id))
        return json.loads(raw) if raw else []

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
    if not couple_id:
        return None, None
    pair_json = redis_client.get(f"chatbot:couple:pair:{couple_id}")
    if not pair_json:
        return couple_id, None
    user1, user2 = json.loads(pair_json)
    partner = user2 if user_id == user1 else user1
    return couple_id, partner
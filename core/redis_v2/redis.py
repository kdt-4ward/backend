import json
import redis
from core.settings import settings
from models.db_tables import Couple, AIMessage, Message, AIChatSummary
from db.db import SessionLocal
from sqlalchemy.exc import SQLAlchemyError
import numpy as np

# Redis 연결
redis_client = redis.StrictRedis(host=settings.redis_host,
                                 port=settings.redis_port,
                                 db=0,
                                 decode_responses=True)

class RedisStorageBase:
    def __init__(self, prefix: str, expire: int = 3600):
        self.prefix = prefix
        self.expire = expire

    def _key(self, id_: str) -> str:
        return f"{self.prefix}:{id_}"

    def get(self, id_: str) -> list | None:
        raw = redis_client.get(self._key(id_))
        return json.loads(raw) if raw else None

    def set(self, id_: str, value: list):
        redis_client.set(self._key(id_), json.dumps(value), ex=self.expire)

    def clear(self, id_: str):
        redis_client.delete(self._key(id_))


class RedisAIHistory(RedisStorageBase):
    def __init__(self):
        super().__init__(prefix="chatbot:history")

    def append(self, user_id: str, message: dict):
        history = self.get(user_id) or []
        history.append(message)
        self.set(user_id, history[-100:])


class RedisCoupleHistory(RedisStorageBase):
    def __init__(self):
        super().__init__(prefix="chatroom:history")

    def get(self, couple_id: str) -> list:
        raw = redis_client.get(self._key(couple_id))
        if raw:
            return json.loads(raw)
        return self._load_from_db(couple_id)

    def _load_from_db(self, couple_id: str) -> list:
        with SessionLocal() as db:
            rows = db.query(Message).filter_by(couple_id=couple_id)\
                    .order_by(Message.created_at.desc())\
                    .limit(100).all()
            history = [{"user_id": r.user_id, "content": r.content} for r in reversed(rows)]
            self.set(couple_id, history)
            return history

    def append(self, couple_id: str, message: dict):
        history = self.get(couple_id) or []
        history.append(message)
        self.set(couple_id, history[-100:])


redis_bin_client = redis.StrictRedis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=0,
    decode_responses=False
)

class RedisFaissChunkCache:
    CHUNK_PREFIX = "chatbot:faiss:chunks"
    EMB_PREFIX = "chatbot:faiss:emb"
    SHAPE_PREFIX = "chatbot:faiss:shape"

    @classmethod
    def _chunk_key(cls, user_id):
        return f"{cls.CHUNK_PREFIX}:{user_id}"

    @classmethod
    def _emb_key(cls, user_id):
        return f"{cls.EMB_PREFIX}:{user_id}"

    @classmethod
    def _shape_key(cls, user_id):
        return f"{cls.SHAPE_PREFIX}:{user_id}"

    @classmethod
    def save(cls, user_id, chunks, embeddings_np):
        # chunk info: json (utf-8) 저장은 redis_client(문자열)
        redis_client.set(cls._chunk_key(user_id), json.dumps(chunks))
        # np.array: 바이너리 저장은 redis_bin_client
        redis_bin_client.set(cls._emb_key(user_id), embeddings_np.tobytes())
        redis_bin_client.set(cls._shape_key(user_id), json.dumps(list(embeddings_np.shape)).encode("utf-8"))

    @classmethod
    def load(cls, user_id):
        chunks_raw = redis_client.get(cls._chunk_key(user_id))
        emb_raw = redis_bin_client.get(cls._emb_key(user_id))
        shape_raw = redis_bin_client.get(cls._shape_key(user_id))
        if not chunks_raw or not emb_raw or not shape_raw:
            return None, None
        chunks = json.loads(chunks_raw)
        shape = tuple(json.loads(shape_raw.decode("utf-8")))
        embeddings_np = np.frombuffer(emb_raw, dtype=np.float32).reshape(shape)
        return chunks, embeddings_np

    @classmethod
    def clear(cls, user_id):
        redis_client.delete(cls._chunk_key(user_id))
        redis_bin_client.delete(cls._emb_key(user_id))
        redis_bin_client.delete(cls._shape_key(user_id))
        
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
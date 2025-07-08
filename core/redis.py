import json
import redis
from core.settings import settings
from models.db_models import Couple, AIMessage, Message, AIChatSummary
from db.db import SessionLocal
from sqlalchemy.exc import SQLAlchemyError
import numpy as np

# Redis 연결
redis_client = redis.StrictRedis(host=settings.redis_host,
                                 port=settings.redis_port,
                                 db=0,
                                 decode_responses=True)

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
        return None

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

REDIS_CHAT_HISTORY_LIMIT = 100  # 커플/유저별 Redis에 남길 메시지 개수
REDIS_CHAT_EXPIRE_SEC = 3600    # 캐시 만료 시간(초)

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
            # 최근 REDIS_CHAT_HISTORY_LIMIT개만 DESC로 불러옴
            rows = db.query(Message).filter_by(couple_id=couple_id).order_by(Message.created_at.desc()).limit(REDIS_CHAT_HISTORY_LIMIT).all()
            # 시간순 재정렬(오래된→최신)
            history = [
                {"user_id": row.user_id, "content": row.content, "created_at": row.created_at.isoformat()} 
                for row in reversed(rows)
            ]
            return history

    @classmethod
    def set_history(cls, couple_id: str, history: list):
        history = history[-REDIS_CHAT_HISTORY_LIMIT:]
        redis_client.set(cls._key(couple_id), json.dumps(history), ex=3600)

    @classmethod
    def append(cls, couple_id: str, message: dict):
        history = cls.get_history(couple_id)
        history.append(message)
        history = history[-REDIS_CHAT_HISTORY_LIMIT:]
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
    

class PersonaChatBotHistoryManager:
    def __init__(self, user_id, couple_id, get_system_prompt, get_summary):
        self.user_id = user_id
        self.couple_id = couple_id
        self.get_system_prompt = get_system_prompt  # callable
        self.get_summary = get_summary  # callable

    def _db_fallback(self):
        # DB에서 summary + 메시지 불러오는 로직 (기존 PersonaChatBot 참고)
        try:
            with SessionLocal() as db:
                # summary
                summary_obj = db.query(AIChatSummary).filter_by(user_id=self.user_id)\
                            .order_by(AIChatSummary.created_at.desc()).first()
                summary = summary_obj.summary if summary_obj else None
                last_msg_id = summary_obj.last_msg_id if summary_obj else None

                # 메시지
                if last_msg_id:
                    messages = db.query(AIMessage).filter(
                        AIMessage.user_id == self.user_id,
                        AIMessage.id > last_msg_id
                    ).order_by(AIMessage.created_at).all()
                else:
                    messages = db.query(AIMessage).filter_by(user_id=self.user_id)\
                                .order_by(AIMessage.created_at).all()

                chat_msgs = [{"role": msg.role, "content": msg.content, "id": msg.id} for msg in messages]
        except SQLAlchemyError as e:
            print(f"[DB Fallback Error] {e}")
        

        return summary, chat_msgs

    def load(self):
        # Redis에서 로딩, 없으면 fallback + Redis 저장
        history = RedisAIHistory.get_history(self.user_id)
        if not history:
            summary, chat_msgs = self._db_fallback()
            history = [self.get_system_prompt()]
            if summary:
                history.append({"role": "summary", "content": summary})
            history.extend(chat_msgs)
            self.save(history)
        else:
            # 중복 프롬프트/summary 보정
            history = self.ensure_prompt_summary(history)
        return history

    def save(self, history):
        # 항상 prompt/summary 구조 보정
        history = self.ensure_prompt_summary(history)
        RedisAIHistory.set_history(self.user_id, history)

    def append(self, message):
        # 현재 히스토리 불러서 메시지 추가 후 보정 저장
        history = self.load()
        # 기존 summary, system prompt 위치 유지, 나머지 뒤에 append
        history.append(message)
        self.save(history)

    def clear(self):
        RedisAIHistory.clear(self.user_id)

    def ensure_prompt_summary(self, history):
        """system prompt, summary 중복 없게 맨 앞에 정렬"""
        filtered = [h for h in history if h["role"] not in ("system", "summary")]
        result = [self.get_system_prompt()]
        summary = self.get_summary()
        if summary:
            result.append({"role": "summary", "content": summary})
        result.extend(filtered)
        return result

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
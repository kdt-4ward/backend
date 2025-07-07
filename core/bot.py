import json
from datetime import datetime
from core.redis import PersonaChatBotHistoryManager, load_couple_mapping, redis_client
from models.db_models import AIMessage, PersonaConfig, AIChatSummary
from core.db import SessionLocal
from services.ai.summarizer import summarize_ai_chat
from enum import Enum

class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    SUMMARY = "summary"
    FUNCTION = "function"

DEFAULT_SYSTEM_PROMPT = (
    "You are a relationship assistant chatbot. "
    "If the user's question is about relationships or dating, respond kindly and empathetically with helpful advice.\n"
    "If the question is not about relationships or dating, answer briefly and simply. "
    "Afterwards, gently encourage the user to share any relationship concerns or questions they might have. "
    "For example, you can say things like, '혹시 연애나 커플 사이에서 궁금한 점이 있다면 언제든 말씀해 주세요.', "
    "'연애 고민이 있으시면 편하게 이야기해 주세요.', or just naturally ask if there's anything related to relationships you'd like to talk about.\n"
    "Always follow these rules:\n"
    "1. For relationship topics, answer only based on what you know, real chat history, or function-call (search) results.\n"
    "2. Use chat search (function-call) only when needed, and base your answer only on actual results.\n"
    "3. If there are no search results or they are empty, kindly say: '관련 대화 기록을 찾을 수 없어요. 더 자세한 정보를 말씀해주시면 찾아볼게요.' and ask for more details.\n"
    "4. Never make up people, events, or facts that do not exist.\n"
    "5. Unless requested otherwise, keep your answers as brief and direct as possible.\n"
    "6. If information is insufficient or the question is unclear, do not guess. Instead, reply: '해당 내용을 알 수 없어요.' or '정확한 정보를 찾지 못했습니다.'\n"
    "7. Always answer in Korean.\n"
)
DEFAULT_NAME = "무민"

class PersonaChatBot:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.couple_id = self.get_couple_id()
        self.history_key = f"chat_history:{self.user_id}"
        self.summary_key = f"chat_summary:{self.user_id}"
        self.config_key = f"chat_config:{self.couple_id}"

        self.history_manager = PersonaChatBotHistoryManager(
            self.user_id,
            self.couple_id,
            self.get_system_prompt,
            self.get_summary
        )
    
    def get_system_prompt(self):
        config = self.get_config()
        persona_name = config.get('persona_name', DEFAULT_NAME)
        system_prompt = config.get('system_prompt', DEFAULT_SYSTEM_PROMPT)
        return {
            "role": "system",
            "content": f"반드시 아래 설정에 맞게 응답해줘.\n\n설정\n이름: {persona_name}\n\n역할: {system_prompt}"
        }
    
    def get_config(self):
        raw = redis_client.get(self.config_key)
        if raw:
            config = json.loads(raw)
        else:
            config = self._load_config_from_db()
            redis_client.set(self.config_key, json.dumps(config), ex=3600)
        config.setdefault("system_prompt", DEFAULT_SYSTEM_PROMPT)
        return config

    def set_persona_name(self, name: str):
        config = self.get_config()
        config["persona_name"] = name
        redis_client.set(self.config_key, json.dumps(config), ex=3600)
        self._save_config_to_db(name)
        # (옵션) 두 명 유저 history 모두 system prompt update 가능

    def _save_config_to_db(self, name: str):
        with SessionLocal() as db:
            config = db.query(PersonaConfig).filter_by(couple_id=self.couple_id).first()
            if not config:
                config = PersonaConfig(couple_id=self.couple_id)
                db.add(config)
            config.persona_name = name
            config.updated_at = datetime.utcnow()
            db.commit()

    def _load_config_from_db(self):
        with SessionLocal() as db:
            config = db.query(PersonaConfig).filter_by(couple_id=self.couple_id).first()
            if config:
                return {"persona_name": config.persona_name}
        return {"persona_name": DEFAULT_NAME}

    def get_history(self):
        return self.history_manager.load()

    def ensure_single_system_prompt(self, history):
        """히스토리에 시스템 프롬프트가 하나만 존재하도록 보정."""
        system_prompt = self.get_system_prompt()
        # 기존 system 프롬프트 제거
        history = [h for h in history if h["role"] != "system"]
        # 맨 앞에만 system 프롬프트 추가
        return [system_prompt] + history
    
    def get_full_history(self):
        with SessionLocal() as db:
            messages = db.query(AIMessage).filter_by(user_id=self.user_id)\
                        .order_by(AIMessage.created_at).all()
            origin_history = [{"role": msg.role, "content": msg.content, "id": msg.id, "created_at": msg.created_at} for msg in messages]
        return origin_history
    
    def save_history(self, history):
        self.history_manager.save(history)

    def reset(self):
        self.history_manager.clear()
        redis_client.delete(self.summary_key)  #

    def save_to_db(self, user_id, role, content):
        with SessionLocal() as db:
            ai_msg = AIMessage(
                user_id=user_id,
                couple_id=self.couple_id,
                role=role,
                content=content,
                created_at=datetime.utcnow()
            )
            db.add(ai_msg)
            db.commit()
            db.refresh(ai_msg)
        return ai_msg.id

    def get_summary(self):
        raw = redis_client.get(self.summary_key)
        if raw:
            val = raw.decode("utf-8") if hasattr(raw, "decode") else raw
            return val if val else ""

        # 🔁 DB fallback
        with SessionLocal() as db:
            latest = db.query(AIChatSummary)\
                .filter_by(user_id=self.user_id)\
                .order_by(AIChatSummary.created_at.desc())\
                .first()
            if latest:
                redis_client.set(self.summary_key, latest.summary, ex=3600 * 6)
                return latest.summary
        return ""

    def get_couple_id(self):
        # Redis나 DB에서 사용자 기반 couple_id 조회 (예: Redis에 user_id → couple_id 맵핑 저장되어 있다면)
        couple_id, _ = load_couple_mapping(self.user_id)
        if not couple_id:
            raise ValueError(f"[PersonaChatBot] user_id={self.user_id}로 couple_id를 찾을 수 없습니다. 커플 매핑이 필요합니다.")
        return couple_id

    def save_summary_and_history_atomic(self, summary: str, new_history: list, last_msg_id: int):
        # DB/Redis 동시 반영 (DB 기준 atomic, Redis는 최대한 맞춰줌)
        with SessionLocal() as db:
            db.add(AIChatSummary(
                user_id=self.user_id,
                couple_id=self.couple_id,
                summary=summary,
                created_at=datetime.utcnow(),
                last_msg_id=last_msg_id,
            ))
            db.commit()   # summary DB에 확정
        # Redis는 보조 저장소이므로, DB 성공 후에 저장(최소 once)
        self.history_manager.save(new_history)
        redis_client.set(self.summary_key, summary, ex=3600 * 6)

    async def check_and_summarize_if_needed(self):
        if not acquire_summary_lock(self.user_id):
            return

        try:
            history = self.get_history()
            # 'system', 'summary' 제외
            filtered = [h for h in history if h["role"] not in (Role.SYSTEM, Role.SUMMARY)]

            # 대화 히스토리를 턴 단위로 분할 (user→(function*)→assistant 한 쌍)
            turns = []
            current_turn = []
            for msg in filtered:
                if msg["role"] == Role.USER:
                    if current_turn:
                        # 끊긴 경우 이전 턴 저장
                        turns.append(current_turn)
                    current_turn = [msg]
                elif msg["role"] == Role.FUNCTION:
                    if current_turn:
                        current_turn.append(msg)
                elif msg["role"] == Role.ASSISTANT:
                    if current_turn:
                        current_turn.append(msg)
                        turns.append(current_turn)
                        current_turn = []
            # 끝에 남은 턴 처리
            if current_turn:
                turns.append(current_turn)

            WINDOW_SIZE = 10
            MIN_REMAINING_SIZE = 5
            assert WINDOW_SIZE > MIN_REMAINING_SIZE, f"WINDOW_SIZE: {WINDOW_SIZE}, MIN_REMAINING_SIZE: {MIN_REMAINING_SIZE}"

            prev_summary = self.get_summary()

            if len(turns) >= WINDOW_SIZE:
                # 요약 대상: 최근 WINDOW_SIZE - MIN_REMAINING_SIZE 턴
                target_turns = turns[:WINDOW_SIZE - MIN_REMAINING_SIZE]

                # 요약 input으로 합치기 (user/function/assistant 순서대로 join)
                target_msgs = [msg for turn in target_turns for msg in turn]

                summary = await summarize_ai_chat(
                    prev_summary=prev_summary,
                    target=target_msgs
                )
                last_msg_id = get_last_msg_id(target_msgs)
                # 남기는 부분: 최근 MIN_REMAINING_SIZE 턴
                remaining_turns = turns[WINDOW_SIZE - MIN_REMAINING_SIZE:]
                remaining_msgs = [msg for turn in remaining_turns for msg in turn]

                new_history = [
                    self.get_system_prompt(),
                    {
                        "role": Role.SUMMARY,
                        "content": f"(누적 요약)\n{summary}"
                    }
                ] + remaining_msgs
                self.save_summary_and_history_atomic(summary, new_history, last_msg_id)
        finally:
            release_summary_lock(self.user_id)


def acquire_summary_lock(user_id, expire=30):
    # True면 락 획득 성공, False면 이미 누군가 잡고 있음
    return redis_client.set(f"lock:summarize:{user_id}", "1", nx=True, ex=expire)

def release_summary_lock(user_id):
    redis_client.delete(f"lock:summarize:{user_id}")

def get_last_msg_id(msgs):
    for msg in reversed(msgs):
        if msg.get("id") is not None:
            return msg["id"]
    return None
from core.redis_v2.persona_config_service import PersonaConfigService
from core.redis_v2.persona_config_service import PersonaPromptProvider
from core.redis_v2.ai_summary_provider import AISummaryProvider
from core.redis_v2.ai_chat_manager import AIChatHistoryManager
from core.redis_v2.redis import load_couple_mapping, redis_client
from core.redis_v2.utils import acquire_lock, release_lock
from db.db_tables import AIMessage, AIChatSummary
from services.ai.summarizer import summarize_ai_chat
from db.db import SessionLocal
from datetime import datetime
from models.schema import Role
from utils.token_truncate import count_tokens
from core.settings import settings

class PersonaChatBot:
    def __init__(self, user_id: str, lang: str = None):
        self.user_id = user_id
        self.couple_id = self.get_couple_id()
        self.lang = lang or "ko"

        self.config_service = PersonaConfigService(self.user_id, self.couple_id)
        self.prompt_provider = PersonaPromptProvider(self.config_service, self.lang)
        self.summary_provider = AISummaryProvider(self.user_id)

        self.history_manager = AIChatHistoryManager(
            user_id=self.user_id,
            couple_id=self.couple_id,
            prompt_provider=self.prompt_provider.get,
            summary_provider=self.summary_provider.get
        )

    def get_history(self):
        return self.history_manager.load()

    def get_full_history(self):
        """DB에서 전체 대화 기록을 가져와서 임베딩용 형태로 반환"""
        with SessionLocal() as db:
            # function 메시지 제외하고 전체 메시지 조회
            messages = (
                db.query(AIMessage)
                .filter_by(user_id=self.user_id)
                .filter(AIMessage.role != "function")
                .order_by(AIMessage.created_at)
                .all()
            )
            
            # 임베딩에 필요한 형태로 변환
            result = []
            for msg in messages:
                result.append({
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at,
                    "id": msg.id,
                })
            
            return result
    def save_history(self, history):
        self.history_manager.save(history)

    def reset(self):
        self.history_manager.clear()

    def get_system_prompt(self):
        return self.prompt_provider.get()

    def get_summary(self):
        return self.summary_provider.get()

    def set_persona_name(self, name: str):
        self.config_service.set_persona_name(name)
    
    def get_couple_id(self):
        # Redis나 DB에서 사용자 기반 couple_id 조회 (예: Redis에 user_id → couple_id 맵핑 저장되어 있다면)
        couple_id, _ = load_couple_mapping(self.user_id)
        if not couple_id:
            raise ValueError(f"[PersonaChatBot] user_id={self.user_id}로 couple_id를 찾을 수 없습니다. 커플 매핑이 필요합니다.")
        return couple_id

    def save_to_db(self, user_id, role, content, name=None):
        with SessionLocal() as db:
            ai_msg = AIMessage(
                user_id=user_id,
                couple_id=self.couple_id,
                role=role,
                content=content,
                created_at=datetime.utcnow(),
                name=name
            )
            db.add(ai_msg)
            db.commit()
            db.refresh(ai_msg)
        return ai_msg.id
    
    def save_summary_and_history_atomic(self, summary: str, new_history: list, last_msg_id: int):
        with SessionLocal() as db:
            db.add(AIChatSummary(
                user_id=self.user_id,
                couple_id=self.couple_id,
                summary=summary,
                created_at=datetime.utcnow(),
                last_msg_id=last_msg_id,
            ))
            db.commit()
        self.history_manager.save(new_history)
        self.summary_provider.set(summary)
    
    async def check_and_summarize_if_needed(self):
        if not acquire_lock(f"lock:summarize:{self.user_id}"):
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

            turn_threshold = settings.sum_turn_threshold
            remaining_size = settings.sum_remaining_size
            summary_trigger_tokens = settings.sum_trigger_tokens
            assert turn_threshold > remaining_size, f"turn_threshold: {turn_threshold}, MIN_REMAINING_SIZE: {remaining_size}"
            

            prev_summary = self.get_summary()

            if should_trigger_summary(turns, token_threshold=summary_trigger_tokens, turn_threshold=turn_threshold):
                # 요약 대상: 최근 WINDOW_SIZE - MIN_REMAINING_SIZE 턴
                target_turns = turns[:turn_threshold - remaining_size]

                # 요약 input으로 합치기 (user/function/assistant 순서대로 join)
                target_msgs = [msg for turn in target_turns for msg in turn]

                summary = await summarize_ai_chat(
                    prev_summary=prev_summary,
                    target=target_msgs
                )
                last_msg_id = get_last_msg_id(target_msgs)
                # 남기는 부분: 최근 MIN_REMAINING_SIZE 턴
                remaining_turns = turns[turn_threshold - remaining_size:]
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
            release_lock(f"lock:summarize:{self.user_id}")

def get_last_msg_id(msgs):
    for msg in reversed(msgs):
        if msg.get("id") is not None:
            return msg["id"]
    return None

def should_trigger_summary(turns: list[list[dict]], token_threshold: int = 2500, turn_threshold: int = 8) -> bool:
    total_tokens = sum(
        count_tokens(msg["content"]) for turn in turns for msg in turn
    )
    return len(turns) >= turn_threshold or total_tokens >= token_threshold
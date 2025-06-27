# sample_app/core/bot.py
import json
from datetime import datetime

from backend.core.redis import redis_client
from backend.models.db_models import AIMessage, PersonaConfig  # <- 추가
from backend.core.db import SessionLocal

DEFAULT_SYSTEM_PROMPT = "너는 연애 조력자로서 사용자에게 공감하고 친절히 대답해주는 chatbot이야. 사용자가 요청하기 전까진 최대한 간략히 대답해줘."
DEFAULT_NAME="무민"

class PersonaChatBot:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.history_key = f"chat_history:{user_id}"
        self.config_key = f"chat_config:{user_id}"
        self.persona_name = None  # 나중에 get_config 통해 설정됨

    def get_config(self):
        raw = redis_client.get(self.config_key)
        if raw:
            config = json.loads(raw)
        else:
            config = self._load_config_from_db()
            redis_client.set(self.config_key, json.dumps(config), ex=3600)
        config["system_prompt"] = DEFAULT_SYSTEM_PROMPT
        self.persona_name = config["persona_name"]
        return config

    def set_persona_name(self, name: str):
        self.persona_name = name

        # Redis 저장
        config = {"persona_name": name}
        redis_client.set(self.config_key, json.dumps(config), ex=3600)

        # DB 저장
        self._save_config_to_db(name)

        # 히스토리 재설정
        self._init_system_prompt()

    def _save_config_to_db(self, name: str):
        with SessionLocal() as db:
            config = db.query(PersonaConfig).filter_by(user_id=self.user_id).first()
            if not config:
                config = PersonaConfig(user_id=self.user_id)
                db.add(config)

            config.persona_name = name
            config.updated_at = datetime.utcnow()
            db.commit()

    def _load_config_from_db(self):
        with SessionLocal() as db:
            config = db.query(PersonaConfig).filter_by(user_id=self.user_id).first()
            if config:
                return {"persona_name": config.persona_name}
        return {"persona_name": f"{DEFAULT_NAME}"}

    def _init_system_prompt(self) -> list:
        config = self.get_config()
        history_before = redis_client.get(self.history_key)
        history = [{
            "role": "system",
            "content": f"아래 설정에 맞게 응답해줘.\n\n설정\n이름: {config['persona_name']}\n\n역할: {config['system_prompt']}"
        }]
        if history_before:
            history += json.loads(history_before)[1:]

        redis_client.set(self.history_key, json.dumps(history), ex=3600)
        return history

    def get_history(self):
        raw = redis_client.get(self.history_key)
        if raw:
            return json.loads(raw)
        config = self.get_config()
        return [{
            "role": "system",
            "content": f"당신은 페르소나 기반의 챗봇입니다. 설정에 맞게 행동하세요. 설정\n\n이름: {config['persona_name']}\n\n역할: {config['system_prompt']}"
        }]

    def save_history(self, history):
        redis_client.set(self.history_key, json.dumps(history), ex=3600)

    def reset(self):
        redis_client.delete(self.history_key)

    def save_to_db(self, user_id, role, content):
        db = SessionLocal()
        db.add(AIMessage(
            user_id=user_id,
            couple_id=self.couple_id,
            role=role,
            content=content,
            created_at=datetime.utcnow()
        ))
        db.commit()
        db.close()

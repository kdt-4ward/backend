import json
from datetime import datetime
from core.redis import redis_client
from models.db_models import AIMessage, PersonaConfig, AIChatSummary
from core.db import SessionLocal

DEFAULT_SYSTEM_PROMPT = "너는 연애 조력자로서 사용자에게 공감하고 친절히 대답해주는 chatbot이야. 사용자가 요청하기 전까진 최대한 간략히 대답해줘."
DEFAULT_NAME = "무민"

class PersonaChatBot:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.history_key = f"chat_history:{user_id}"
        self.config_key = f"chat_config:{user_id}"
        self.summary_key = f"chat_summary:{user_id}"
        self.persona_name = None

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
        config = {"persona_name": name}
        redis_client.set(self.config_key, json.dumps(config), ex=3600)
        self._save_config_to_db(name)
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

    def _init_system_prompt(self):
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

        # 🔁 Redis에 없으면 → DB에서 복원
        history = self._load_history_from_db()
        self.save_history(history)
        return history

    def _load_history_from_db(self):
        with SessionLocal() as db:
            messages = db.query(AIMessage)\
                .filter_by(user_id=self.user_id)\
                .order_by(AIMessage.created_at)\
                .all()

            config = self.get_config()
            history = [{
                "role": "system",
                "content": f"아래 설정에 맞게 응답해줘.\n\n설정\n이름: {config['persona_name']}\n\n역할: {config['system_prompt']}"
            }]
            for msg in messages:
                history.append({
                    "role": msg.role,
                    "content": msg.content
                })
            return history
    
    def get_full_history(self):
        raw = redis_client.get(self.history_key)
        return json.loads(raw) if raw else []

    def get_last_turns(self, n: int = 10):
        history = self.get_history()
        system_prompt = [h for h in history if h["role"] == "system"]
        turns = [h for h in history if h["role"] != "system"]
        last_turns = turns[-n:]
        return system_prompt + last_turns

    def save_history(self, history):
        redis_client.set(self.history_key, json.dumps(history), ex=3600)

    def reset(self):
        redis_client.delete(self.history_key)
        redis_client.delete(self.summary_key)

    def save_to_db(self, user_id, role, content):
        db = SessionLocal()
        db.add(AIMessage(
            user_id=user_id,
            couple_id="unknown",  # 필요한 경우 couple_id 연동
            role=role,
            content=content,
            created_at=datetime.utcnow()
        ))
        db.commit()
        db.close()

    def get_summary(self):
        raw = redis_client.get(self.summary_key)
        if raw:
            return raw.decode("utf-8")

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

    def save_summary(self, summary: str):
        redis_client.set(self.summary_key, summary, ex=3600 * 6)
        with SessionLocal() as db:
            db.add(AIChatSummary(
                user_id=self.user_id,
                couple_id="unknown",  # 필요한 경우 설정
                summary=summary,
                created_at=datetime.utcnow()
            ))
            db.commit()


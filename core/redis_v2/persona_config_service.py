import json
from core.settings import settings
from db.db_tables import PersonaConfig, User, UserTraitSummary, Couple, EmotionLog
from db.db import SessionLocal
from services.ai.prompt_templates import PROMPT_REGISTRY

import redis
from datetime import datetime, timedelta

redis_client = redis.StrictRedis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=0,
    decode_responses=True
)

DEFAULT_NAME = "러비"
USER_NAME = "사용자"
DEFAULT_PERSONALITY = "Not given"


class PersonaConfigService:
    def __init__(self, user_id: str, couple_id: str):
        self.user_id = user_id
        self.couple_id = couple_id
        self.redis_key = f"chat_config:{user_id}"

    def get_config(self) -> dict:
        raw = redis_client.get(self.redis_key)
        if raw:
            config = json.loads(raw)
        else:
            config = self._load_from_db()
            redis_client.set(self.redis_key, json.dumps(config), ex=3600)
        return config

    def _load_from_db(self):
        with SessionLocal() as db:
            config = db.query(PersonaConfig).filter_by(couple_id=self.couple_id).first()
            user = db.query(User).filter_by(user_id=self.user_id).first()
            trait = db.query(UserTraitSummary).filter_by(user_id=self.user_id).first()

            # 감정 기록: 현재 시각 기준 12시간 이내의 기록만 가져오고, 없으면 None
            now = datetime.utcnow()
            twelve_hours_ago = now - timedelta(hours=12)
            emotion_log = db.query(EmotionLog).filter(
                EmotionLog.user_id == self.user_id,
                EmotionLog.recorded_at >= twelve_hours_ago,
                EmotionLog.recorded_at <= now
            ).order_by(EmotionLog.recorded_at.desc()).first()

            # 상대방 정보 가져오기
            couple = db.query(Couple).filter_by(couple_id=self.couple_id).first()
            if self.user_id == couple.user_1:
                partner_id = couple.user_2
            else:
                partner_id = couple.user_1
                
            # 상대방 정보 조회
            partner = db.query(User).filter_by(user_id=partner_id).first()
            partner_trait = db.query(UserTraitSummary).filter_by(user_id=partner_id).first()

            return {
                "persona_name": config.persona_name if config else DEFAULT_NAME,
                "user_name": user.name if user else USER_NAME,
                "user_personality": trait.summary if trait else DEFAULT_PERSONALITY,
                "partner_personality": partner_trait.summary if partner_trait else DEFAULT_PERSONALITY,
                "emotion": emotion_log.emotion if emotion_log else "Not Given"
            }

    def set_persona_name(self, name: str):
        config = self.get_config()
        config["persona_name"] = name
        redis_client.set(self.redis_key, json.dumps(config), ex=3600)
        with SessionLocal() as db:
            obj = db.query(PersonaConfig).filter_by(couple_id=self.couple_id).first()
            if not obj:
                obj = PersonaConfig(couple_id=self.couple_id)
            obj.persona_name = name
            obj.updated_at = datetime.utcnow()
            db.add(obj)
            db.commit()

class PersonaPromptProvider:
    def __init__(self, config_service: PersonaConfigService, lang: str = "ko"):
        self.config_service = config_service
        self.lang = lang

    def get(self) -> dict:
        config = self.config_service.get_config()
        prompt_template = PROMPT_REGISTRY.get(f"chatbot_prompt_{self.lang}", PROMPT_REGISTRY["chatbot_prompt_ko"])

        return {
            "role": "system",
            "content": prompt_template.format(
                bot_name=config["persona_name"],
                user_name=config["user_name"],
                user_personality=config.get("user_personality", DEFAULT_PERSONALITY),
                partner_personality=config.get("partner_personality", DEFAULT_PERSONALITY)
            )
        }
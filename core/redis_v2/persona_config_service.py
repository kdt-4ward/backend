import json
from core.settings import settings
from db.db_tables import PersonaConfig, User, UserTraitSummary, Couple, EmotionLog
from db.db import SessionLocal
from services.ai.prompt_templates import PROMPT_REGISTRY

import redis
from datetime import datetime, timedelta
from typing import Dict, Any

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
        if raw is not None:
            config = json.loads(raw) # type: ignore
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
            if couple is None:
                raise ValueError(f"Couple with id {self.couple_id} not found")

            if self.user_id == couple.user_1:
                partner_id = couple.user_2
            else:
                partner_id = couple.user_1
                
            # 상대방 정보 조회
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
            obj.persona_name = name # type: ignore
            db.add(obj)
            db.commit()

class PersonaPromptProvider:
    def __init__(self, config_service: PersonaConfigService, lang: str = "ko"):
        self.config_service = config_service
        self.lang = lang
        # 기존 방식과의 호환성을 위한 fallback
        self.use_composer = False  # 새로운 조합 시스템 사용 여부

    async def get(self, user_message: str) -> dict:
        config = self.config_service.get_config()
        
        # 새로운 조합 시스템 사용
        if self.use_composer and user_message:
            return await self._get_composed_prompt(config, user_message)
        
        # 기존 방식 (fallback)
        return self._get_legacy_prompt(config)
    
    async def _get_composed_prompt(self, config: dict, user_message: str) -> dict:
        """새로운 프롬프트 조합 시스템 사용"""
        from services.ai.prompt_composer import PromptComposer
        
        composer = PromptComposer(self.lang)
        
        # 기본 컨텍스트 구성
        context = {
            "bot_name": config["persona_name"],
            "user_name": config["user_name"],
            "user_personality": config.get("user_personality", DEFAULT_PERSONALITY),
            "partner_personality": config.get("partner_personality", DEFAULT_PERSONALITY),
            "emotion": config.get("emotion", "Not Given"),
            "user_message": user_message,
        }
        
        # 상황별 컨텍스트 분석
        context.update(self._analyze_message_context(user_message))
        
        # 프롬프트 조합
        prompt_content = await composer.compose_prompt(context)
        
        return {
            "role": "system",
            "content": prompt_content
        }
    
    def _get_legacy_prompt(self, config: dict) -> dict:
        """기존 방식의 프롬프트 생성 (fallback)"""
        prompt_template = PROMPT_REGISTRY.get(f"chatbot_prompt_{self.lang}", PROMPT_REGISTRY["chatbot_prompt_ko"])

        return {
            "role": "system",
            "content": prompt_template.format(
                bot_name=config["persona_name"],
                user_name=config["user_name"],
                user_personality=config.get("user_personality", DEFAULT_PERSONALITY),
                partner_personality=config.get("partner_personality", DEFAULT_PERSONALITY),
                emotion=config.get("emotion", "Not Given")
            )
        }
    
    def _analyze_message_context(self, message: str) -> Dict[str, Any]:
        """메시지 내용을 기반으로 기본 컨텍스트 분석"""
        context = {}
        
        # 기본적인 키워드 기반 분석
        crisis_keywords = ["죽고 싶다", "자살", "더 이상 못 살겠다", "폭력", "때리고 싶다", "죽이고 싶다"]
        conflict_keywords = ["싸웠", "다퉜", "갈등", "서운", "화나", "짜증나"]
        breakup_keywords = ["이별", "헤어지", "끝내", "포기"]
        relationship_keywords = ["연애", "사랑", "데이트", "남자친구", "여자친구", "커플", "연인", "남친", "여친", "기념", "선물"]
        
        message_lower = message.lower()
        
        context["crisis_detected"] = any(keyword in message_lower for keyword in crisis_keywords)
        context["conflict_detected"] = any(keyword in message_lower for keyword in conflict_keywords)
        context["breakup_concern"] = any(keyword in message_lower for keyword in breakup_keywords)
        context["is_relationship_question"] = any(keyword in message_lower for keyword in relationship_keywords)
        
        # 감정 강도 추정
        emotional_words = ["사랑해", "미워해", "화나다", "슬프다", "기쁘다", "짜증나다", "서운하다"]
        emotional_count = sum(1 for word in emotional_words if word in message_lower)
        context["emotional_intensity"] = min(emotional_count / 3, 1.0)
        
        # 메시지 복잡도
        context["message_complexity"] = min(len(message) / 100, 1.0)
        
        return context
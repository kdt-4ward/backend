from pydantic import BaseModel
from typing import Optional


# 메시지 스키마 정의
class WSMessage(BaseModel):
    type: str
    message: Optional[str] = None
    partner_id: Optional[str] = None
    couple_id: Optional[str] = None
    image_url: Optional[str] = None
    
class GoogleAuthCode(BaseModel):
    code: str

class ChatRequest(BaseModel):
    user_id: str
    message: str
    couple_id: Optional[str] = None  # DB 저장 시 필요

class UserMessage(BaseModel):
    sender_id: str
    receiver_id: str
    content: str

class BotConfigRequest(BaseModel):
    user_id: str
    persona_name: str
    
class ChatHistoryRequest(BaseModel):
    user1: str
    user2: str

### solution ###
class ChatInput(BaseModel):
    text: str

class QuestionnaireInput(BaseModel):
    user_answers: str

class DailyEmotionInput(BaseModel):
    daily_log: str

class WeeklySolutionInput(BaseModel):
    chat_traits: str
    questionnaire_traits: str
    daily_emotions: str

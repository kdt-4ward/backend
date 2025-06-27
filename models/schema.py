from pydantic import BaseModel
from typing import Optional

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

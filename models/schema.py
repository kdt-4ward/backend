from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum

class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    SUMMARY = "summary"
    FUNCTION = "function"


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

########### USER SURVEY ################
class SurveyResponseInput(BaseModel):
    user_id: str
    question_id: int
    choice_id: Optional[int] = None
    custom_input: Optional[str] = None

################# Post #######################

class ImageRequest(BaseModel):
    image_url: str
    image_order: int
    post_id: Optional[int] = None  # ✅ 게시글 생성 시에는 없음

class ImageResponse(BaseModel):
    image_id: int
    post_id: int
    image_url: str
    image_order: int
    created_at: datetime

    class Config:
        from_attributes = True

        
class PostRequest(BaseModel):
    user_id: str
    couple_id: str
    content: Optional[str] = None
    images: Optional[List[ImageRequest]] = []


class PostResponse(BaseModel):
    post_id: int
    user_id: str
    couple_id: str
    content: Optional[str]
    created_at: datetime
    images: Optional[List[str]] = []  # ✅ 추가

    class Config:
        from_attributes = True

class CommentRequest(BaseModel):
    post_id: int
    user_id: str
    comment: str

class CommentResponse(BaseModel):
    comment_id: int
    post_id: int
    user_id: str
    comment: str
    created_at: datetime
################# emotion ########################
class EmotionLogRequest(BaseModel):
    user_id: str
    couple_id: Optional[str] = None  # 커플 ID는 선택 사항
    emotion: str                     # 기본 감정 캐릭터 ID
    detail_emotions: Optional[List[str]] = []  # 세부 감정 (최대 3개)
    memo: Optional[str] = None     
    recorded_at: Optional[datetime] = None     # 기록 날짜 (지정 가능, 기본은 오늘)

class EmotionLogResponse(BaseModel):
    emotion_id: int
    user_id: str
    couple_id: Optional[str]
    emotion: str
    detail_emotions: Optional[List[str]]
    memo: Optional[str] = None
    recorded_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

################# Couple Invite ########################
class CoupleInviteCreate(BaseModel):
    inviter_user_id: str

class CoupleInviteJoin(BaseModel):
    invite_code: str
    invited_user_id: str

class CoupleInviteResponse(BaseModel):
    invite_code: str
    inviter_user_id: str
    status: str
    invited_user_id: Optional[str]
    couple_id: Optional[str]
    created_at: datetime
    accepted_at: Optional[datetime]
    expired_at: Optional[datetime]

################# User ########################
class UserResponse(BaseModel):
    user_id: str
    name: str
    profile_image: Optional[str] = None
    couple_id: Optional[str] = None
    birth: Optional[datetime] = None
    gender: Optional[str] = None
    created_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserSignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str
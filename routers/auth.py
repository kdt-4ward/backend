from uuid import uuid4
import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Header
import httpx
import jwt
from pydantic import BaseModel
from models.schema import GoogleAuthCode, UserLoginRequest, UserSignupRequest
from fastapi import Request
from db.db import SessionLocal
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from datetime import datetime, time
from utils.jwt_utils import create_access_token, create_refresh_token, verify_token
from core.settings import settings
from db.db import get_session  # DB 세션 의존성 주입
from db.crud import get_couple_id_by_user_id
from db.db_tables import *
from utils.log_utils import get_logger

logger = get_logger(__name__)
router = APIRouter()

# class CodeBody(BaseModel):
#     code: str

class KakaoLoginRequest(BaseModel):
    kakao_access_token: str

class RefreshRequest(BaseModel):
    refresh_token: str

@router.post("/kakao-login")
async def kakao_login(body: KakaoLoginRequest):
    print("카카오 로그인 요청:", body)
    kakao_api_url = "https://kapi.kakao.com/v2/user/me"
    headers = {"Authorization": f"Bearer {body.kakao_access_token}"}
    async with httpx.AsyncClient() as client:
        res = await client.get(kakao_api_url, headers=headers)
        if res.status_code != 200:
            raise HTTPException(status_code=401, detail="Kakao token invalid")
        userinfo = res.json()

    user_id = str(userinfo["id"])
    nickname = userinfo["properties"]['nickname']
    profile_image = userinfo["properties"].get("profile_image", None)
    
    # ✅ DB에 user_id로 user 생성/조회
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(user_id=user_id).first()
        if not user:
            user = User(
                user_id=user_id,
                name=nickname,
                profile_image=profile_image,
                created_at=datetime.utcnow(),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"✅ 새 사용자 저장: {user_id}")
        else:
            # 기존 유저 정보 최신화(닉네임, 프로필 등)
            user.name = nickname
            if profile_image:
                user.profile_image = profile_image
            db.commit()
            print(f"🔁 기존 사용자: {user_id}")
    finally:
        db.close()

    # JWT 발급
    access_token = create_access_token({"sub": str(user_id), "nickname": nickname, "profile_image": profile_image})
    refresh_token = create_refresh_token({"sub": str(user_id)})
    return {"access_token": access_token, "refresh_token": refresh_token}

# 서비스 API 인증 예시
def get_current_user(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No bearer token")
    token = authorization[7:]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload

@router.get("/me")
def get_me(user=Depends(get_current_user), db: Session = Depends(get_session)):
    user_id = user.get("sub")
    db_user = db.query(User).filter_by(user_id=user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "user_id": db_user.user_id,
        "nickname": db_user.name,
        "profile_image": db_user.profile_image,
        "couple_id": db_user.couple_id,
        "email": db_user.email,
    }

@router.post("/refresh")
def refresh_token(req: RefreshRequest):
    payload = verify_token(req.refresh_token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user_id = payload["sub"]
    # (DB에서 refresh token이 실제로 유효한지도 체크하면 더 안전)
    new_access_token = create_access_token({"sub": user_id})
    # 필요하다면 refresh token도 새로 발급 (권장)
    new_refresh_token = create_refresh_token({"sub": user_id})
    return {"access_token": new_access_token, "refresh_token": new_refresh_token}

################ 일반 로그인/회원가입 #################
@router.post("/signup")
def signup(data: UserSignupRequest, db: Session = Depends(get_session)):
    # 이메일 중복 확인
    if db.query(User).filter_by(email=data.email).first():
        raise HTTPException(status_code=400, detail="이미 존재하는 이메일입니다.")
    # 패스워드 해시
    pw_hash = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode()
    user = User(
        user_id=str(uuid4()),
        name=data.name,
        email=data.email,
        password=pw_hash,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"detail": "회원가입 성공", "user_id": user.user_id}

@router.post("/login")
def login(data: UserLoginRequest, db: Session = Depends(get_session)):
    user = db.query(User).filter_by(email=data.email).first()
    if not user or not user.password:
        raise HTTPException(status_code=400, detail="유효하지 않은 계정입니다.")
    # 비밀번호 비교
    if not bcrypt.checkpw(data.password.encode(), user.password.encode()):
        raise HTTPException(status_code=400, detail="비밀번호가 일치하지 않습니다.")
    # JWT 발급
    access_token = create_access_token({"sub": user.user_id, "nickname": user.name})
    refresh_token = create_refresh_token({"sub": user.user_id})
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user_id": user.user_id,
        "nickname": user.name,
        "couple_id": user.couple_id
    }

## user 삭제 시 커플 초대, 커플 정보 삭제.
## user 삭제 시 관련된 모든 정보(커플, 초대, 메시지, 분석 등) 외래키 관계 고려해서 삭제
@router.get("/delete-user")
def delete_user_completely(user=Depends(get_current_user), db: Session = Depends(get_session)):
    """사용자와 관련된 모든 데이터를 완전히 삭제"""
    user_id = user.get("sub")
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return False, "사용자를 찾을 수 없습니다."
        
        # 하드 삭제 (CASCADE로 모든 관련 데이터 삭제)
        db.delete(user)
        db.commit()
        logger.info(f"사용자 {user_id} 완전 삭제 완료")
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"사용자 {user_id} 삭제 실패: {e}")
        return False
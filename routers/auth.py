from fastapi import APIRouter, Depends, HTTPException, Header
import httpx
import jwt
from pydantic import BaseModel
from services.google_auth import get_google_access_token, get_google_userinfo
from models.schema import GoogleAuthCode
from fastapi import Request
from db.db import SessionLocal
from sqlalchemy.exc import IntegrityError
from models.db_tables import User
from sqlalchemy.orm import Session
from utils.hash_utils import hash_email  
from datetime import datetime, time
from utils.jwt_utils import create_access_token, create_refresh_token, verify_token
from core.settings import settings

router = APIRouter()

# class CodeBody(BaseModel):
#     code: str

class KakaoLoginRequest(BaseModel):
    kakao_access_token: str

class RefreshRequest(BaseModel):
    refresh_token: str
    
@router.post("/auth/kakao-login")
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
    
    # TODO: DB에 user_id로 user 생성/조회

    # JWT 발급
    access_token = create_access_token({"sub": str(user_id), "nickname": nickname})
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
def get_me(user=Depends(get_current_user)):
    return {"user_id": user.get("id"), "nickname": user.get('nickname'), "profile_image": user.get('profileImageUrl')}

@router.post("/auth/refresh")
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

# @router.get("/auth/google/callback")
# async def google_callback_get(request: Request):
#     # 쿼리 파라미터에서 code 꺼냄
#     code = request.query_params.get("code")
#     print("✅ GET 방식 전달받은 code:", code)

#     if not code:
#         raise HTTPException(status_code=400, detail="코드 없음")

#     token_json = await get_google_access_token(code)
#     access_token = token_json.get("access_token")

#     if not access_token:
#         raise HTTPException(status_code=400, detail="토큰 요청 실패")

#     userinfo = await get_google_userinfo(access_token)
#     print("👤 유저 정보:", userinfo)

#     name = userinfo.get("name")
#     email = userinfo.get("email")

#     if not email or not name:
#         raise HTTPException(status_code=400, detail="유저 정보 누락")

#     # DB 저장
#     db = SessionLocal()
#     try:
#         user = User(email=email, name=name)
#         db.add(user)
#         db.commit()
#     except IntegrityError:
#         db.rollback()  # 이미 존재하는 경우 무시
#     finally:
#         db.close()

#     return {"user_info": {"name": name, "email": email}}
#     # return {"user_info": userinfo}

# def save_user(name: str, email: str):
#     db: Session = SessionLocal()
#     user_id = hash_email(email)

#     # 중복 저장 방지
#     existing = db.query(User).filter_by(user_id=user_id).first()
#     if existing:
#         print(f"🔁 이미 존재하는 사용자: {user_id}")
#         db.close()
#         return user_id

#     user = User(user_id=user_id, name=name)
#     db.add(user)
#     db.commit()
#     db.close()
#     print(f"✅ 사용자 저장 완료: {user_id}")
#     return user_id


# @router.get("/auth/google/callback")
# async def google_callback_get(request: Request):
#     code = request.query_params.get("code")
#     print("✅ GET 방식 전달받은 code:", code)

#     if not code:
#         raise HTTPException(status_code=400, detail="코드 없음")

#     token_json = await get_google_access_token(code)
#     access_token = token_json.get("access_token")

#     if not access_token:
#         raise HTTPException(status_code=400, detail="토큰 요청 실패")

#     userinfo = await get_google_userinfo(access_token)
#     print("👤 유저 정보:", userinfo)

#     name = userinfo.get("name")
#     email = userinfo.get("email")

#     if not name or not email:
#         raise HTTPException(status_code=400, detail="유저 정보 누락")

#     # ✅ 이메일 해싱해서 user_id 생성
#     user_id = hash_email(email)

#     db: Session = SessionLocal()
#     try:
#         # ✅ 이미 존재하는 사용자면 스킵
#         existing = db.query(User).filter_by(user_id=user_id).first()
#         if not existing:
#             user = User(
#                 user_id=user_id,
#                 name=name,
#                 email=email,
#                 password="",
#                 created_at=datetime.utcnow()
#             )
#             db.add(user)
#             db.commit()
#             print(f"✅ 새 사용자 저장 완료: {user_id}")
#         else:
#             print(f"🔁 이미 존재하는 사용자: {user_id}")
#     finally:
#         db.close()

#     return {
#         "user_info": {
#             "user_id": user_id,
#             "name": name,
#             "email": email
#         }
#     }

# @router.post("/auth/google/code")
# async def google_login_code(request: Request):
#     code = request.query_params.get("code")
#     if not code:
#         raise HTTPException(status_code=400, detail="code missing")
    
#     # 1. 구글에서 access_token 받아오기
#     token_json = await get_google_access_token(code)
#     access_token = token_json.get("access_token")
#     if not access_token:
#         raise HTTPException(status_code=400, detail="token request failed")
    
#     # 2. 구글에서 유저 정보 받아오기
#     userinfo = await get_google_userinfo(access_token)
#     name = userinfo.get("name")
#     email = userinfo.get("email")
#     if not name or not email:
#         raise HTTPException(status_code=400, detail="user info missing")
    
#     # 3. 유저 생성(없으면) + user_id 해싱 생성
#     user_id = hash_email(email)
#     db: Session = SessionLocal()
#     try:
#         user = db.query(User).filter_by(user_id=user_id).first()
#         if not user:
#             user = User(
#                 user_id=user_id,
#                 name=name,
#                 email=email,
#                 created_at=datetime.utcnow()
#             )
#             db.add(user)
#             db.commit()
#         # 4. JWT 액세스/리프레시 토큰 발급
#         access_token_jwt = create_access_token({"sub": user_id, "email": email})
#         refresh_token_jwt = create_refresh_token({"sub": user_id, "email": email})
#     finally:
#         db.close()
    
#     # 5. 결과 반환
#     return {
#         "user_info": {
#             "user_id": user_id,
#             "name": name,
#             "email": email
#         },
#         "access_token": access_token_jwt,
#         "refresh_token": refresh_token_jwt,
#         "token_type": "bearer"
#     }

# # --- GET 방식 (웹리다이렉트 테스트용, 앱은 주로 POST 사용) ---
# @router.get("/auth/google/callback")
# async def google_callback_get(request: Request):
#     code = request.query_params.get("code")
#     if not code:
#         raise HTTPException(status_code=400, detail="코드 없음")

#     token_json = await get_google_access_token(code)
#     access_token = token_json.get("access_token")
#     if not access_token:
#         raise HTTPException(status_code=400, detail="토큰 요청 실패")
    
#     userinfo = await get_google_userinfo(access_token)
#     name = userinfo.get("name")
#     email = userinfo.get("email")
    
#     if not name or not email:
#         raise HTTPException(status_code=400, detail="유저 정보 누락")
    
#     user_id = hash_email(email)
#     db: Session = SessionLocal()
#     try:
#         existing = db.query(User).filter_by(user_id=user_id).first()
#         if not existing:
#             user = User(
#                 user_id=user_id,
#                 name=name,
#                 email=email,
#                 created_at=datetime.utcnow()
#             )
#             db.add(user)
#             db.commit()
#     finally:
#         db.close()

#     return {
#         "user_info": {
#             "user_id": user_id,
#             "name": name,
#             "email": email
#         }
#     }
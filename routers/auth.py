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
def delete_user(user=Depends(get_current_user), db: Session = Depends(get_session)):
    user_id = user.get("sub")    
    couple_id = get_couple_id_by_user_id(user_id)

    # 1. 커플 초대 삭제
    invites = db.query(CoupleInvite).filter(
        (CoupleInvite.inviter_user_id == user_id) |
        (CoupleInvite.invited_user_id == user_id)
    ).all()
    for invite in invites:
        db.delete(invite)
    db.commit()

    # 2. 커플 관련 분석/설정/요약/메시지 등 삭제 (couple_id 기준)
    if couple_id:
        # 커플 일간/주간 분석
        db.query(CoupleDailyAnalysisResult).filter(CoupleDailyAnalysisResult.couple_id == couple_id).delete()
        db.query(CoupleWeeklyAnalysisResult).filter(CoupleWeeklyAnalysisResult.couple_id == couple_id).delete()
        db.query(CoupleWeeklyComparisonResult).filter(CoupleWeeklyComparisonResult.couple_id == couple_id).delete()
        # 커플 페르소나 설정
        db.query(PersonaConfig).filter(PersonaConfig.couple_id == couple_id).delete()
        # 커플 요약
        db.query(AIChatSummary).filter(AIChatSummary.couple_id == couple_id).delete()
        # 커플 메시지
        db.query(Message).filter(Message.couple_id == couple_id).delete()
        # 커플 게시글/댓글/이미지
        from db.db_tables import Post, PostImage, Comment
        post_ids = [p.post_id for p in db.query(Post).filter(Post.couple_id == couple_id).all()]
        if post_ids:
            db.query(PostImage).filter(PostImage.post_id.in_(post_ids)).delete(synchronize_session=False)
            db.query(Comment).filter(Comment.post_id.in_(post_ids)).delete(synchronize_session=False)
            db.query(Post).filter(Post.couple_id == couple_id).delete()
        db.commit()

    # 3. 커플 정보 삭제 (user가 속한 커플)
    couples = db.query(Couple).filter(
        (Couple.user_1 == user_id) | (Couple.user_2 == user_id)
    ).all()
    for couple in couples:
        db.delete(couple)
    db.commit()


    # 4. 유저 관련 데이터 삭제 (user_id 기준)
    # AI 메시지
    db.query(AIMessage).filter(AIMessage.user_id == user_id).delete()
    # AI 일간 분석
    db.query(AIDailyAnalysisResult).filter(AIDailyAnalysisResult.user_id == user_id).delete()
    # AI 요약
    db.query(AIChatSummary).filter(AIChatSummary.user_id == user_id).delete()
    # 메시지
    db.query(Message).filter(Message.user_id == user_id).delete()
    # 감정 로그
    db.query(EmotionLog).filter(EmotionLog.user_id == user_id).delete()
    # 설문 응답
    db.query(UserSurveyResponse).filter(UserSurveyResponse.user_id == user_id).delete()
    # 성향 요약
    db.query(UserTraitSummary).filter(UserTraitSummary.user_id == user_id).delete()
    db.commit()

    # 5. 유저 삭제
    user_obj = db.query(User).filter(User.user_id == user_id).first()
    if user_obj:
        db.delete(user_obj)
        db.commit()

    return {"detail": "회원 탈퇴 및 관련 데이터가 모두 삭제되었습니다."}

    
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

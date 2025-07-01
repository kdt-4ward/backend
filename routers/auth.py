from fastapi import HTTPException
from services.google_auth import get_google_access_token, get_google_userinfo
from config import router
from models.schema import GoogleAuthCode
from fastapi import Request
from core.db import SessionLocal
from sqlalchemy.exc import IntegrityError
from models.db_models import User
from sqlalchemy.orm import Session
from utils.hash_utils import hash_email  
from datetime import datetime


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


@router.get("/auth/google/callback")
async def google_callback_get(request: Request):
    code = request.query_params.get("code")
    print("✅ GET 방식 전달받은 code:", code)

    if not code:
        raise HTTPException(status_code=400, detail="코드 없음")

    token_json = await get_google_access_token(code)
    access_token = token_json.get("access_token")

    if not access_token:
        raise HTTPException(status_code=400, detail="토큰 요청 실패")

    userinfo = await get_google_userinfo(access_token)
    print("👤 유저 정보:", userinfo)

    name = userinfo.get("name")
    email = userinfo.get("email")

    if not name or not email:
        raise HTTPException(status_code=400, detail="유저 정보 누락")

    # ✅ 이메일 해싱해서 user_id 생성
    user_id = hash_email(email)

    db: Session = SessionLocal()
    try:
        # ✅ 이미 존재하는 사용자면 스킵
        existing = db.query(User).filter_by(user_id=user_id).first()
        if not existing:
            user = User(
                user_id=user_id,
                name=name,
                email=email,
                password="",
                created_at=datetime.utcnow()
            )
            db.add(user)
            db.commit()
            print(f"✅ 새 사용자 저장 완료: {user_id}")
        else:
            print(f"🔁 이미 존재하는 사용자: {user_id}")
    finally:
        db.close()

    return {
        "user_info": {
            "user_id": user_id,
            "name": name,
            "email": email
        }
    }
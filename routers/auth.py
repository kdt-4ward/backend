from fastapi import HTTPException
from services.google_auth import get_google_access_token, get_google_userinfo
from config import router
from models.schema import GoogleAuthCode


@router.post("/auth/google/callback")
async def google_callback(payload: GoogleAuthCode):
    code = payload.code

    token_json = await get_google_access_token(code)
    access_token = token_json.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="토큰 요청 실패")

    userinfo = await get_google_userinfo(access_token)
    
    # TODO: 여기서 사용자 DB 저장 또는 JWT 생성 가능
    return {"user_info": userinfo}
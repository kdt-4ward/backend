from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
import io
from datetime import datetime

from core.dependencies import get_db_session
from utils.message_parser import parse_kakao_log
from db.db_tables import Message, User
from db.crud import get_couple_id_by_user_id
from models.schema import ChatUploadResponse

router = APIRouter(prefix="/chat-upload")

@router.post("/kakao-log", response_model=ChatUploadResponse)
async def upload_kakao_chat_log(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    db: Session = Depends(get_db_session)
):
    """
    카카오톡 대화 로그 파일을 업로드하여 DB에 저장
    
    - file: 카카오톡 대화 내보내기 txt 파일
    - user_id: 현재 사용자 ID
    - partner_name: 상대방 이름 (카카오톡에서 표시되는 이름)
    """
    
    # 파일 확장자 검증
    if not file.filename.endswith('.txt'):
        raise HTTPException(status_code=400, detail="txt 파일만 업로드 가능합니다.")
    
    try:
        # 파일 내용 읽기
        content = await file.read()
        raw_text = content.decode('utf-8')
        
        # 사용자의 커플 ID 조회
        couple_id = get_couple_id_by_user_id(db, user_id)
        user_name = db.query(User).filter(User.user_id == user_id).first().name
        partner_id = db.query(User).filter(User.couple_id == couple_id, User.user_id != user_id).first().user_id

        if not couple_id:
            raise HTTPException(status_code=404, detail="사용자의 커플 정보를 찾을 수 없습니다.")
        
        # 이름 매핑 딕셔너리 생성 (상대방 이름 -> user_id)
        # 실제 구현에서는 상대방의 user_id를 조회해야 함
        name2id = {user_name: user_id}
        
        # 메시지 파싱
        parsed_messages = parse_kakao_log(
            raw_text=raw_text,
            couple_id=couple_id,
            name2id=name2id,
            partner_id=partner_id
        )
        
        if not parsed_messages:
            raise HTTPException(status_code=400, detail="파싱된 메시지가 없습니다.")
        
        # DB에 메시지 저장
        saved_count = 0
        inserted_messages = []
        for msg_data in parsed_messages:
            # 중복 메시지 체크 (같은 시간, 같은 내용)
            existing_msg = db.query(Message).filter(
                Message.couple_id == couple_id,
                Message.user_id == msg_data["user_id"],
                Message.content == msg_data["content"],
                Message.created_at == msg_data["created_at"]
            ).first()
            
            if not existing_msg:
                message = Message(
                    user_id=msg_data["user_id"],
                    couple_id=couple_id,
                    content=msg_data["content"],
                    image_url=msg_data["image_url"],
                    has_image=msg_data["has_image"],
                    created_at=msg_data["created_at"]
                )
                db.add(message)
                saved_count += 1
                inserted_messages.append(message)
        db.commit()
        for message in inserted_messages:
            db.refresh(message)
        
        return ChatUploadResponse(
            success=True,
            message=f"총 {len(parsed_messages)}개 메시지 중 {saved_count}개가 성공적으로 저장되었습니다.",
            total_parsed=len(parsed_messages),
            total_saved=saved_count,
            couple_id=couple_id
        )
        
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="파일 인코딩을 확인해주세요. UTF-8 형식이어야 합니다.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"파일 처리 중 오류가 발생했습니다: {str(e)}")

@router.get("/status/{couple_id}")
async def get_upload_status(
    couple_id: str,
    db: Session = Depends(get_db_session)
):
    """
    특정 커플의 업로드된 메시지 통계 조회
    """
    total_messages = db.query(Message).filter(Message.couple_id == couple_id).count()
    
    if total_messages == 0:
        return {"message": "업로드된 메시지가 없습니다.", "total_messages": 0}
    
    # 가장 오래된 메시지와 최신 메시지 조회
    oldest_msg = db.query(Message).filter(Message.couple_id == couple_id).order_by(Message.created_at.asc()).first()
    newest_msg = db.query(Message).filter(Message.couple_id == couple_id).order_by(Message.created_at.desc()).first()
    
    return {
        "total_messages": total_messages,
        "date_range": {
            "oldest": oldest_msg.created_at.isoformat() if oldest_msg else None,
            "newest": newest_msg.created_at.isoformat() if newest_msg else None
        },
        "couple_id": couple_id
    } 
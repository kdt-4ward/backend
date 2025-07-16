from typing import List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import and_
from sqlalchemy.orm import Session
import random, string
from datetime import datetime, timedelta
from models.db_tables import CoupleInvite, Couple, User
from models.schema import CoupleInviteCreate, CoupleInviteJoin, CoupleInviteResponse
from db.db import get_session  # DB 세션 의존성 주입

router = APIRouter()

@router.post("/invite", response_model=CoupleInviteResponse)
def create_invite(data: CoupleInviteCreate, db: Session = Depends(get_session)):
    # 1. 이미 커플 연결된 유저는 초대 금지
    inviter = db.query(User).filter_by(user_id=data.inviter_user_id).first()
    if inviter.couple_id:
        raise HTTPException(status_code=400, detail="이미 커플로 연결된 유저입니다.")

    # 2. 기존에 'pending' 상태의 초대코드 있으면 재활용, 또는 생성 제한
    now = datetime.utcnow()
    existing = db.query(CoupleInvite).filter(
        and_(
            CoupleInvite.inviter_user_id == data.inviter_user_id,
            CoupleInvite.status == "pending",
            CoupleInvite.expired_at > now
        )
    ).first()
    if existing:
        return existing  # 이미 유효한 초대코드 반환
      
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    expired_at = now + timedelta(hours=24)
    invite = CoupleInvite(
        invite_code=code,
        inviter_user_id=data.inviter_user_id,
        status="pending",
        created_at=now,
        expired_at=expired_at
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return invite

@router.post("/join", response_model=CoupleInviteResponse)
def join_invite(data: CoupleInviteJoin, db: Session = Depends(get_session)):
    # 1. 이미 커플 연결된 유저는 참여 불가
    invited = db.query(User).filter_by(user_id=data.invited_user_id).first()
    if invited.couple_id:
        raise HTTPException(status_code=400, detail="이미 커플로 연결된 유저입니다.")

    now = datetime.utcnow()
    invite = db.query(CoupleInvite).filter(
        and_(
            CoupleInvite.invite_code == data.invite_code,
            CoupleInvite.status == "pending",
            CoupleInvite.expired_at > now
        )
    ).first()
    if not invite:
        raise HTTPException(status_code=404, detail="초대코드가 유효하지 않거나 만료됨.")

    # 커플 생성
    couple_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
    couple = Couple(
        couple_id=couple_id,
        user_1=invite.inviter_user_id,
        user_2=data.invited_user_id,
        created_at=datetime.utcnow()
    )
    db.add(couple)
    db.commit()

    # User 테이블에도 couple_id 업데이트
    db.query(User).filter(User.user_id.in_([invite.inviter_user_id, data.invited_user_id])).update(
        {User.couple_id: couple_id}, synchronize_session="fetch"
    )
    db.commit()

    # 초대 상태 업데이트
    invite.status = "accepted"
    invite.invited_user_id = data.invited_user_id
    invite.couple_id = couple_id
    invite.accepted_at = datetime.utcnow()
    db.commit()
    db.refresh(invite)

    return invite

@router.post("/breakup")
def breakup(user_id: str, db: Session = Depends(get_session)):
    # 1. 본인 couple_id 조회
    user = db.query(User).filter_by(user_id=user_id).first()
    if not user or not user.couple_id:
        raise HTTPException(status_code=400, detail="커플이 아닙니다.")

    couple_id = user.couple_id
    # 2. 커플의 두 명 모두 couple_id 해제
    db.query(User).filter(User.couple_id == couple_id).update(
        {User.couple_id: None}, synchronize_session="fetch"
    )
    db.commit()

    # 3. Couple 테이블에서 deleted_at 표시 (소프트삭제)
    couple = db.query(Couple).filter_by(couple_id=couple_id).first()
    if couple:
        couple.deleted_at = datetime.utcnow()
        db.commit()
    return {"detail": "커플이 해제되었습니다."}

@router.get("/invites/{user_id}", response_model=List[CoupleInviteResponse])
def list_invites(user_id: str, db: Session = Depends(get_session)):
    invites = db.query(CoupleInvite).filter_by(inviter_user_id=user_id).order_by(CoupleInvite.created_at.desc()).all()
    return invites

# 커플 정보 조회
@router.get("/info/{couple_id}")
def get_couple_info(couple_id: str, db: Session = Depends(get_session)):
    couple = db.query(Couple).filter_by(couple_id=couple_id).first()
    if not couple:
        raise HTTPException(status_code=404, detail="Couple not found")
    user1 = db.query(User).filter_by(user_id=couple.user_1).first()
    user2 = db.query(User).filter_by(user_id=couple.user_2).first()
    return {
        "couple_id": couple.couple_id,
        "created_at": couple.created_at,
        "user1": {
            "user_id": user1.user_id,
            "nickname": user1.name,
            "profile_image": user1.profile_image,
        } if user1 else None,
        "user2": {
            "user_id": user2.user_id,
            "nickname": user2.name,
            "profile_image": user2.profile_image,
        } if user2 else None,
    }
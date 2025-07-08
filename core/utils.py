from models.db_models import Couple
from core.redis import save_couple_mapping
from db.db import SessionLocal

def ensure_couple_mapping(user_id: str, partner_id: str, couple_id: str):
    # 1. DB에 존재하는지 확인
    with SessionLocal() as db:
        couple = db.query(Couple).filter_by(couple_id=couple_id).first()
        if not couple:
            couple = Couple(couple_id=couple_id, user_1=user_id, user_2=partner_id)
            db.add(couple)
            db.commit()
        # 2. Redis 매핑
        save_couple_mapping(user_id, partner_id, couple_id)
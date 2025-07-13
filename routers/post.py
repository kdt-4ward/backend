from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.db_tables import Post
from models.schema import PostRequest
from core.dependencies import get_db_session
from core.redis import redis_client, load_couple_mapping
from datetime import datetime
import json

router = APIRouter(prefix="/post")

@router.post("/")
def save_post(req: PostRequest, db: Session = Depends(get_db_session)):
    couple_id, _ = load_couple_mapping(req.user_id)
    if not couple_id:
        raise HTTPException(status_code=404, detail="커플 정보를 찾을 수 없습니다.")

    post = Post(
        user_id=req.user_id,
        couple_id=couple_id,
        title=req.title,
        content=req.content,
        created_at=datetime.utcnow()
    )
    db.add(post)
    db.commit()
    db.refresh(post)

    redis_client.delete(f"posts:{req.user_id}")
    return {"message": "게시글 저장 완료", "post_id": post.id}

@router.get("/{user_id}")
def get_posts(user_id: str, db: Session = Depends(get_db_session)):
    cache_key = f"posts:{user_id}"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    posts = db.query(Post).filter_by(user_id=user_id).order_by(Post.created_at.desc()).all()
    result = [{"id": p.id, "title": p.title, "content": p.content, "created_at": p.created_at.isoformat()} for p in posts]
    redis_client.set(cache_key, json.dumps(result, ensure_ascii=False), ex=1800)
    return result

@router.delete("/{post_id}")
def delete_post(post_id: int, db: Session = Depends(get_db_session)):
    post = db.query(Post).filter_by(id=post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    db.delete(post)
    db.commit()

    redis_client.delete(f"posts:{post.user_id}")
    return {"message": "게시글 삭제 완료"}

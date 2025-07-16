from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.db_tables import Post, Comment, PostImage
from models.schema import PostRequest, PostResponse, ImageRequest
from core.dependencies import get_db_session
from datetime import datetime
import json

router = APIRouter()

# 게시글 저장
@router.post("/")
def save_post(req: PostRequest, db: Session = Depends(get_db_session)):
    print("✅ 받은 요청 데이터:", req.dict())

    # 테스트용 주석처리
    # couple_id, _ = load_couple_mapping(req.user_id)
    couple_id = req.couple_id

    if not couple_id:
        raise HTTPException(status_code=404, detail="커플 정보를 찾을 수 없습니다.")

    post = Post(
        user_id=req.user_id,
        couple_id=couple_id,
        content=req.content,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(post)
    db.commit()
    db.refresh(post)

    # 이미지 저장 처리
    for img in req.images:
        db.add(PostImage(
            post_id=post.post_id,
            image_url=img.image_url,
            image_order=img.image_order,
        ))
    db.commit()

    return {
        "message": "게시글 저장 완료",
        "post_id": post.post_id,
    }


@router.get("/couple/{couple_id}")
def get_couple_posts(couple_id: str, db: Session = Depends(get_db_session)):

    posts = db.query(Post)\
        .filter(Post.couple_id == couple_id, Post.deleted_at == None)\
        .order_by(Post.created_at.desc())\
        .all()

    result = []
    for p in posts:
        # ✅ 대표 이미지 1장만 조회
        first_image = db.query(PostImage)\
            .filter(PostImage.post_id == p.post_id, PostImage.deleted_at == None)\
            .order_by(PostImage.image_order.asc())\
            .first()

        result.append({
            "post_id": p.post_id,
            "user_id": p.user_id,
            "couple_id": p.couple_id,
            "content": p.content,
            "created_at": p.created_at.isoformat(),
            "images": [first_image.image_url] if first_image else []  # ✅ 썸네일용
        })

    return result

# 게시글 단건 조회
@router.get("/{post_id}", response_model=PostResponse)
def get_post(post_id: int, db: Session = Depends(get_db_session)):
    post = db.query(Post).filter(Post.post_id == post_id, Post.deleted_at == None).first()
    if not post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")

    images = db.query(PostImage)\
        .filter(PostImage.post_id == post_id, PostImage.deleted_at == None)\
        .order_by(PostImage.image_order.asc())\
        .all()

    return {
        "post_id": post.post_id,
        "user_id": post.user_id,
        "couple_id": post.couple_id,
        "content": post.content,
        "created_at": post.created_at,
        "images": [img.image_url for img in images],  # ✅ 여기
    }


# 게시글 삭제 (soft delete)
@router.delete("/{post_id}")
def delete_post(post_id: int, db: Session = Depends(get_db_session)):
    post = db.query(Post).filter(Post.post_id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")

    post.deleted_at = datetime.utcnow()
    comments = db.query(Comment).filter(Comment.post_id == post_id).all()
    for c in comments:
        c.deleted_at = datetime.utcnow()
    db.commit()

    return {"message": "게시글 삭제 완료"}

@router.put("/{post_id}")
def update_post(post_id: int, req: PostRequest, db: Session = Depends(get_db_session)):
    post = db.query(Post).filter(Post.post_id == post_id, Post.deleted_at == None).first()
    if not post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    
    if post.user_id != req.user_id:
        raise HTTPException(status_code=403, detail="수정 권한이 없습니다.")

    post.content = req.content
    post.updated_at = datetime.utcnow()
    db.commit()
    # ✅ 기존 이미지 삭제 후 새로 저장
    db.query(PostImage).filter(PostImage.post_id == post_id).delete()
    for img in req.images:
        db.add(PostImage(
            post_id=post_id,
            image_url=img.image_url,
            image_order=img.image_order,
        ))
    db.commit()

    return {"message": "게시글 수정 완료"}

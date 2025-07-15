from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.db_tables import Comment
from models.schema import CommentRequest, CommentResponse
from core.dependencies import get_db_session
from datetime import datetime
from typing import List

router = APIRouter(prefix="/comment")

@router.post("/", response_model=dict)
def add_comment(req: CommentRequest, db: Session = Depends(get_db_session)):
    comment = Comment(
        post_id=req.post_id,
        user_id=req.user_id,
        comment=req.comment,
        created_at=datetime.utcnow(),
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return {"message": "댓글 추가 완료", "comment_id": comment.comment_id}


@router.get("/{post_id}", response_model=List[CommentResponse])
def get_comments(post_id: int, db: Session = Depends(get_db_session)):
    comments = db.query(Comment).filter(
        Comment.post_id == post_id,
        Comment.deleted_at == None
    ).order_by(Comment.created_at.asc()).all()
    return comments


@router.delete("/{comment_id}", response_model=dict)
def delete_comment(comment_id: int, user_id: str, db: Session = Depends(get_db_session)):
    comment = db.query(Comment).filter(Comment.comment_id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="댓글을 찾을 수 없습니다.")
    if comment.user_id != user_id:
        raise HTTPException(status_code=403, detail="본인의 댓글만 삭제할 수 있습니다.")

    comment.deleted_at = datetime.utcnow()
    db.commit()
    return {"message": "댓글 삭제 완료"}

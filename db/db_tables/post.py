from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class Post(Base):
    __tablename__ = "posts"

    post_id = Column(Integer, primary_key=True, autoincrement=True)   # 게시글 ID (PK)
    user_id = Column(String(255), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)                     # 작성자
    couple_id = Column(String(255), ForeignKey("couples.couple_id", ondelete="CASCADE"), nullable=False)                   # 커플 ID
    content = Column(Text, nullable=True)                             # 게시글 내용

    created_at = Column(DateTime, default=datetime.utcnow)            # 생성일
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 수정일
    deleted_at = Column(DateTime, nullable=True)                      # 삭제일 (소프트 삭제용)
    
    # Relationships
    user = relationship("User", back_populates="posts")
    couple = relationship("Couple", back_populates="posts")
    comments = relationship("Comment", cascade="all, delete", back_populates="post")
    images = relationship("PostImage", cascade="all, delete", back_populates="post")

class Comment(Base):
    __tablename__ = "Post_comments"

    comment_id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.post_id", ondelete="CASCADE"))
    user_id = Column(String(255), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    
    # Relationships
    post = relationship("Post", back_populates="comments")
    user = relationship("User", back_populates="comments")

class PostImage(Base):
    __tablename__ = "post_images"

    image_id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey("posts.post_id", ondelete="CASCADE"), nullable=False)
    image_url = Column(String(500), nullable=False)
    image_order = Column(Integer, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    
    # Relationships
    post = relationship("Post", back_populates="images")

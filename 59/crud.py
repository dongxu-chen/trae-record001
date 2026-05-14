from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import tsquery
from typing import List, Optional, Tuple, Dict, Any
from models import User, Post
from schemas import UserCreate, PostCreate, PostUpdate
from passlib.context import CryptContext
from database import is_postgresql

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, user: UserCreate) -> Optional[User]:
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except IntegrityError:
        db.rollback()
        return None


def get_posts(db: Session, skip: int = 0, limit: int = 100) -> List[Post]:
    return db.query(Post).offset(skip).limit(limit).all()


def get_posts_paginated(
    db: Session,
    cursor_id: Optional[int] = None,
    limit: int = 100
) -> Tuple[List[Post], Optional[int]]:
    query = db.query(Post).order_by(Post.id.desc())
    
    if cursor_id is not None:
        query = query.filter(Post.id < cursor_id)
    
    posts = query.limit(limit + 1).all()
    
    next_cursor = None
    if len(posts) > limit:
        posts = posts[:limit]
        next_cursor = posts[-1].id
    
    return posts, next_cursor


def get_total_posts_count(db: Session) -> int:
    return db.query(func.count(Post.id)).scalar()


def get_post_by_id(db: Session, post_id: int) -> Optional[Post]:
    return db.query(Post).filter(Post.id == post_id).first()


def create_post(db: Session, post: PostCreate, user_id: int) -> Post:
    db_post = Post(
        title=post.title,
        content=post.content,
        tags=[tag.lower() for tag in post.tags] if post.tags else [],
        author_id=user_id
    )
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post


def update_post(
    db: Session,
    post_id: int,
    post_update: PostUpdate,
    user_id: Optional[int] = None
) -> Optional[Post]:
    db_post = get_post_by_id(db, post_id)
    if not db_post:
        return None
    
    if user_id is not None and db_post.author_id != user_id:
        return None
    
    update_data = post_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == 'tags' and value is not None:
            value = [tag.lower() for tag in value]
        setattr(db_post, key, value)
    
    db.commit()
    db.refresh(db_post)
    return db_post


def update_post_with_owner_check(
    db: Session,
    post_id: int,
    post_update: PostUpdate,
    user_id: int
) -> Optional[Post]:
    db_post = get_post_by_id(db, post_id)
    if not db_post:
        return None
    
    if db_post.author_id != user_id:
        return db_post
    
    update_data = post_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == 'tags' and value is not None:
            value = [tag.lower() for tag in value]
        setattr(db_post, key, value)
    
    db.commit()
    db.refresh(db_post)
    return db_post


def search_posts(
    db: Session,
    query: str,
    skip: int = 0,
    limit: int = 100
) -> Tuple[List[Post], int]:
    if is_postgresql():
        search_query = func.plainto_tsquery('english', query)
        search_rank = func.ts_rank(Post.search_vector, search_query)
        
        stmt = select(
            Post,
            search_rank.label('score')
        ).where(
            Post.search_vector.op('@@')(search_query)
        ).order_by(
            search_rank.desc(),
            Post.created_at.desc()
        ).offset(skip).limit(limit)
        
        result = db.execute(stmt)
        posts_with_scores = [(row[0], row[1]) for row in result]
        
        count_stmt = select(func.count()).where(
            Post.search_vector.op('@@')(search_query)
        )
        total = db.execute(count_stmt).scalar() or 0
        
        posts = [post for post, _ in posts_with_scores]
        for post, score in posts_with_scores:
            setattr(post, '_search_score', score)
        
        return posts, total
    else:
        search_term = f"%{query.lower()}%"
        posts = db.query(Post).filter(
            or_(
                func.lower(Post.title).like(search_term),
                func.lower(Post.content).like(search_term)
            )
        ).order_by(Post.created_at.desc()).offset(skip).limit(limit).all()
        
        total = db.query(func.count(Post.id)).filter(
            or_(
                func.lower(Post.title).like(search_term),
                func.lower(Post.content).like(search_term)
            )
        ).scalar() or 0
        
        return posts, total


def get_hot_posts(
    db: Session,
    limit: int = 10,
    days: int = 7
) -> List[Post]:
    from datetime import datetime, timedelta
    cutoff_time = datetime.utcnow() - timedelta(days=days)
    
    posts = db.query(Post).filter(
        Post.created_at >= cutoff_time
    ).order_by(
        Post.view_count.desc(),
        Post.created_at.desc()
    ).limit(limit).all()
    
    return posts


def increment_post_view_count(db: Session, post_id: int) -> Optional[Post]:
    from cache import cache_manager
    cache_manager.increment_view_count(post_id)
    
    db_post = get_post_by_id(db, post_id)
    if db_post:
        db_post.view_count = (db_post.view_count or 0) + 1
        db.commit()
        db.refresh(db_post)
        return db_post
    return None


def sync_view_counts_to_db(db: Session) -> int:
    from cache import cache_manager
    view_counts = cache_manager.get_all_view_counts()
    
    if not view_counts:
        return 0
    
    updated = 0
    for post_id, count in view_counts.items():
        db_post = get_post_by_id(db, post_id)
        if db_post:
            db_post.view_count = (db_post.view_count or 0) + count
            cache_manager.clear_view_count(post_id)
            updated += 1
    
    if updated > 0:
        db.commit()
    
    return updated


def delete_post(db: Session, post_id: int, user_id: Optional[int] = None) -> bool:
    db_post = get_post_by_id(db, post_id)
    if not db_post:
        return False
    
    if user_id is not None and db_post.author_id != user_id:
        return False
    
    db.delete(db_post)
    db.commit()
    return True


def delete_post_with_owner_check(
    db: Session,
    post_id: int,
    user_id: int
) -> Optional[Post]:
    db_post = get_post_by_id(db, post_id)
    if not db_post:
        return None
    
    if db_post.author_id != user_id:
        return db_post
    
    db.delete(db_post)
    db.commit()
    return db_post

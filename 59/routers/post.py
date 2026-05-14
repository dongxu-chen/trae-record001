from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from schemas import (
    PostCreate,
    PostUpdate,
    PostResponse,
    SearchResult,
    TagCloudItem
)
from crud import (
    create_post,
    get_posts,
    get_post_by_id,
    update_post_with_owner_check,
    delete_post_with_owner_check,
    search_posts,
    get_hot_posts,
    increment_post_view_count
)
from dependencies import get_db, get_current_user
from models import User
from cache import (
    get_hot_posts_from_cache,
    set_hot_posts_to_cache,
    invalidate_hot_posts_cache
)
from tags import get_tag_cloud, get_posts_by_tag

router = APIRouter(
    prefix="/posts",
    tags=["posts"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=List[PostResponse])
def read_posts(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    posts = get_posts(db, skip=skip, limit=limit)
    return posts


@router.get("/search/", response_model=List[SearchResult])
def search_posts_endpoint(
    q: str = Query(..., min_length=1, description="Search query"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db)
):
    posts, total = search_posts(db, query=q, skip=skip, limit=limit)
    results = []
    for post in posts:
        score = getattr(post, '_search_score', None)
        results.append({
            'id': post.id,
            'title': post.title,
            'content': post.content,
            'tags': post.tags or [],
            'view_count': post.view_count,
            'author_id': post.author_id,
            'author_name': post.author.username if post.author else 'Unknown',
            'created_at': post.created_at,
            'score': score
        })
    return results


@router.get("/tags/cloud/", response_model=List[TagCloudItem])
def get_tag_cloud_endpoint(
    days: Optional[int] = Query(None, description="Time range in days for recent tags"),
    limit: int = Query(100, ge=1, le=500),
    min_font_size: int = Query(12, ge=8),
    max_font_size: int = Query(36, le=72),
    db: Session = Depends(get_db)
):
    tag_cloud = get_tag_cloud(
        db,
        days=days,
        limit=limit,
        min_font_size=min_font_size,
        max_font_size=max_font_size
    )
    return tag_cloud


@router.get("/tag/{tag}", response_model=List[PostResponse])
def get_posts_by_tag_endpoint(
    tag: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db)
):
    posts = get_posts_by_tag(db, tag=tag.lower(), skip=skip, limit=limit)
    return posts


@router.get("/hot/", response_model=List[PostResponse])
def get_hot_posts_endpoint(
    limit: int = Query(10, ge=1, le=50),
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db)
):
    cached_hot = get_hot_posts_from_cache()
    if cached_hot is not None:
        return cached_hot
    
    posts = get_hot_posts(db, limit=limit, days=days)
    
    posts_data = []
    for post in posts:
        post_dict = {
            'id': post.id,
            'title': post.title,
            'content': post.content,
            'tags': post.tags or [],
            'view_count': post.view_count,
            'author_id': post.author_id,
            'created_at': post.created_at,
            'updated_at': post.updated_at,
            'author': {
                'id': post.author.id,
                'username': post.author.username,
                'email': post.author.email,
                'created_at': post.author.created_at
            }
        }
        posts_data.append(post_dict)
    
    set_hot_posts_to_cache(posts_data)
    return posts


@router.get("/{post_id}", response_model=PostResponse)
def read_post(
    post_id: int,
    db: Session = Depends(get_db)
):
    db_post = get_post_by_id(db, post_id=post_id)
    if db_post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    
    increment_post_view_count(db, post_id=post_id)
    return db_post


@router.post("/", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_new_post(
    post: PostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_post = create_post(db=db, post=post, user_id=current_user.id)
    invalidate_hot_posts_cache()
    return new_post


@router.put("/{post_id}", response_model=PostResponse)
def update_existing_post(
    post_id: int,
    post_update: PostUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = update_post_with_owner_check(
        db=db,
        post_id=post_id,
        post_update=post_update,
        user_id=current_user.id
    )
    
    if result is None:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if result.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this post"
        )
    
    invalidate_hot_posts_cache()
    return result


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = delete_post_with_owner_check(
        db=db,
        post_id=post_id,
        user_id=current_user.id
    )
    
    if result is None:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if result.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this post"
        )
    
    invalidate_hot_posts_cache()

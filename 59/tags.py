from typing import List, Dict, Tuple, Optional
from collections import Counter
from datetime import datetime, timedelta
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from models import Post
from database import is_postgresql


def extract_tags_from_text(text: str) -> List[str]:
    if not text:
        return []
    
    import re
    tags = re.findall(r'#(\w+)', text)
    return [tag.lower() for tag in tags]


def get_all_tags(db: Session) -> List[str]:
    if is_postgresql():
        stmt = select(func.unnest(Post.tags)).distinct()
        result = db.execute(stmt)
        tags = [row[0] for row in result if row[0]]
        return sorted(tags)
    else:
        posts = db.query(Post).all()
        all_tags = set()
        for post in posts:
            if post.tags:
                for tag in post.tags:
                    if tag:
                        all_tags.add(tag)
        return sorted(all_tags)


def get_tag_frequency(db: Session, limit: Optional[int] = None) -> List[Tuple[str, int]]:
    if is_postgresql():
        stmt = select(
            func.unnest(Post.tags).label('tag'),
            func.count().label('count')
        ).group_by('tag').order_by(func.count().desc())
        
        if limit:
            stmt = stmt.limit(limit)
        
        result = db.execute(stmt)
        return [(row[0], row[1]) for row in result if row[0]]
    else:
        tag_counter: Counter = Counter()
        posts = db.query(Post).all()
        for post in posts:
            if post.tags:
                for tag in post.tags:
                    if tag:
                        tag_counter[tag] += 1
        
        sorted_tags = tag_counter.most_common(limit) if limit else tag_counter.most_common()
        return sorted_tags


def get_tag_frequency_with_time(
    db: Session,
    days: int = 30,
    limit: Optional[int] = None
) -> List[Tuple[str, int]]:
    cutoff_time = datetime.utcnow() - timedelta(days=days)
    
    if is_postgresql():
        stmt = select(
            func.unnest(Post.tags).label('tag'),
            func.count().label('count')
        ).where(Post.created_at >= cutoff_time).group_by('tag').order_by(func.count().desc())
        
        if limit:
            stmt = stmt.limit(limit)
        
        result = db.execute(stmt)
        return [(row[0], row[1]) for row in result if row[0]]
    else:
        tag_counter: Counter = Counter()
        posts = db.query(Post).filter(Post.created_at >= cutoff_time).all()
        for post in posts:
            if post.tags:
                for tag in post.tags:
                    if tag:
                        tag_counter[tag] += 1
        
        sorted_tags = tag_counter.most_common(limit) if limit else tag_counter.most_common()
        return sorted_tags


def calculate_tag_weights(
    tag_frequency: List[Tuple[str, int]],
    min_font_size: int = 12,
    max_font_size: int = 36
) -> List[Dict[str, object]]:
    if not tag_frequency:
        return []
    
    counts = [count for _, count in tag_frequency]
    min_count = min(counts)
    max_count = max(counts)
    
    tag_cloud: List[Dict[str, object]] = []
    
    for tag, count in tag_frequency:
        if max_count == min_count:
            weight = 0.5
        else:
            weight = (count - min_count) / (max_count - min_count)
        
        font_size = int(min_font_size + weight * (max_font_size - min_font_size))
        
        tag_cloud.append({
            'tag': tag,
            'count': count,
            'weight': round(weight, 2),
            'font_size': font_size
        })
    
    return tag_cloud


def get_tag_cloud(
    db: Session,
    days: Optional[int] = None,
    limit: Optional[int] = 100,
    min_font_size: int = 12,
    max_font_size: int = 36
) -> List[Dict[str, object]]:
    if days:
        tag_frequency = get_tag_frequency_with_time(db, days=days, limit=limit)
    else:
        tag_frequency = get_tag_frequency(db, limit=limit)
    
    return calculate_tag_weights(
        tag_frequency,
        min_font_size=min_font_size,
        max_font_size=max_font_size
    )


def get_posts_by_tag(db: Session, tag: str, skip: int = 0, limit: int = 100) -> List[Post]:
    if is_postgresql():
        stmt = select(Post).where(
            Post.tags.contains([tag])
        ).order_by(Post.created_at.desc()).offset(skip).limit(limit)
        result = db.execute(stmt)
        return [row[0] for row in result]
    else:
        posts = db.query(Post).order_by(Post.created_at.desc()).all()
        filtered_posts = [
            post for post in posts 
            if post.tags and tag in post.tags
        ]
        return filtered_posts[skip:skip + limit]


def merge_tags(existing_tags: List[str], new_tags: List[str]) -> List[str]:
    if not new_tags:
        return existing_tags or []
    
    existing_set = set(existing_tags) if existing_tags else set()
    new_set = set(tag.lower() for tag in new_tags if tag)
    
    merged = existing_set | new_set
    return sorted(merged)

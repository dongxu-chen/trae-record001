from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

from config import Config

Base = declarative_base()


class SocialMediaPost(Base):
    __tablename__ = 'social_media_posts'
    
    id = Column(Integer, primary_key=True)
    platform = Column(String(50), nullable=False, index=True)
    post_id = Column(String(100), nullable=False, index=True)
    content = Column(Text, nullable=False)
    author = Column(String(200))
    author_id = Column(String(100))
    post_url = Column(String(500))
    timestamp = Column(DateTime, nullable=False, index=True)
    likes = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    views = Column(Integer, default=0)
    raw_data = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    sentiment = relationship('SentimentResult', back_populates='post', uselist=False, cascade='all, delete-orphan')
    topics = relationship('TopicResult', back_populates='post', cascade='all, delete-orphan')
    
    __table_args__ = (
        Index('idx_platform_timestamp', 'platform', 'timestamp'),
    )


class SentimentResult(Base):
    __tablename__ = 'sentiment_results'
    
    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey('social_media_posts.id'), nullable=False, index=True)
    sentiment = Column(String(20), nullable=False, index=True)
    positive_score = Column(Float, default=0.0)
    negative_score = Column(Float, default=0.0)
    neutral_score = Column(Float, default=0.0)
    confidence = Column(Float, default=0.0)
    analyzed_at = Column(DateTime, default=datetime.utcnow)
    
    post = relationship('SocialMediaPost', back_populates='sentiment')


class TopicResult(Base):
    __tablename__ = 'topic_results'
    
    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey('social_media_posts.id'), nullable=False, index=True)
    topic_id = Column(Integer, nullable=False)
    topic_keywords = Column(String(500))
    topic_weight = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    post = relationship('SocialMediaPost', back_populates='topics')


class Alert(Base):
    __tablename__ = 'alerts'
    
    id = Column(Integer, primary_key=True)
    alert_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    platform = Column(String(50), index=True)
    related_post_ids = Column(String(500))
    metrics = Column(Text)
    triggered_at = Column(DateTime, default=datetime.utcnow, index=True)
    acknowledged = Column(Integer, default=0)
    acknowledged_at = Column(DateTime)


class TrendData(Base):
    __tablename__ = 'trend_data'
    
    id = Column(Integer, primary_key=True)
    platform = Column(String(50), nullable=False, index=True)
    date_hour = Column(DateTime, nullable=False, index=True)
    total_posts = Column(Integer, default=0)
    positive_count = Column(Integer, default=0)
    negative_count = Column(Integer, default=0)
    neutral_count = Column(Integer, default=0)
    avg_sentiment_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_platform_date', 'platform', 'date_hour', unique=True),
    )


class KeywordTrend(Base):
    __tablename__ = 'keyword_trends'
    
    id = Column(Integer, primary_key=True)
    keyword = Column(String(100), nullable=False, index=True)
    platform = Column(String(50), index=True)
    date_hour = Column(DateTime, nullable=False, index=True)
    frequency = Column(Integer, default=0)
    sentiment_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_keyword_platform_date', 'keyword', 'platform', 'date_hour', unique=True),
    )


class PropagationPath(Base):
    __tablename__ = 'propagation_paths'
    
    id = Column(Integer, primary_key=True)
    root_post_id = Column(String(100), nullable=False, index=True)
    platform = Column(String(50), nullable=False)
    source_node = Column(String(200), nullable=False)
    target_node = Column(String(200), nullable=False)
    depth = Column(Integer, default=0)
    propagation_time = Column(DateTime)
    content_snippet = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    engine = create_engine(Config.DATABASE_URL, echo=False, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    return engine


def get_session():
    engine = init_db()
    Session = sessionmaker(bind=engine)
    return Session()


def save_post(session, post_data):
    post = SocialMediaPost(
        platform=post_data.get('platform'),
        post_id=post_data.get('post_id'),
        content=post_data.get('content', ''),
        author=post_data.get('author'),
        author_id=post_data.get('author_id'),
        post_url=post_data.get('post_url'),
        timestamp=post_data.get('timestamp'),
        likes=post_data.get('likes', 0),
        shares=post_data.get('shares', 0),
        comments=post_data.get('comments', 0),
        views=post_data.get('views', 0),
        raw_data=post_data.get('raw_data')
    )
    session.add(post)
    session.flush()
    return post


def save_sentiment(session, post_db_id, sentiment_data):
    sentiment = SentimentResult(
        post_id=post_db_id,
        sentiment=sentiment_data.get('sentiment'),
        positive_score=sentiment_data.get('positive', 0.0),
        negative_score=sentiment_data.get('negative', 0.0),
        neutral_score=sentiment_data.get('neutral', 0.0),
        confidence=sentiment_data.get('confidence', 0.0)
    )
    session.add(sentiment)
    return sentiment


def save_topics(session, post_db_id, topics_data):
    for topic in topics_data:
        topic_result = TopicResult(
            post_id=post_db_id,
            topic_id=topic.get('topic_id'),
            topic_keywords=','.join(topic.get('keywords', [])),
            topic_weight=topic.get('weight', 0.0)
        )
        session.add(topic_result)


def save_alert(session, alert_data):
    alert = Alert(
        alert_type=alert_data.get('alert_type'),
        severity=alert_data.get('severity'),
        title=alert_data.get('title'),
        description=alert_data.get('description'),
        platform=alert_data.get('platform'),
        related_post_ids=alert_data.get('related_post_ids'),
        metrics=alert_data.get('metrics')
    )
    session.add(alert)
    session.commit()
    return alert


def save_propagation_path(session, path_data):
    path = PropagationPath(
        root_post_id=path_data.get('root_post_id'),
        platform=path_data.get('platform'),
        source_node=path_data.get('source_node'),
        target_node=path_data.get('target_node'),
        depth=path_data.get('depth', 0),
        propagation_time=path_data.get('propagation_time'),
        content_snippet=path_data.get('content_snippet')
    )
    session.add(path)
    return path

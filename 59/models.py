from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index, event, DDL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    posts = relationship("Post", back_populates="author")


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    tags = Column(ARRAY(String), default=list, nullable=False)
    search_vector = Column(TSVECTOR, nullable=True)
    view_count = Column(Integer, default=0, nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    author = relationship("User", back_populates="posts")

    __table_args__ = (
        Index(
            'ix_posts_search_vector',
            'search_vector',
            postgresql_using='gin'
        ),
    )


post_search_trigger = DDL(
    """
    CREATE TRIGGER posts_search_vector_update
    BEFORE INSERT OR UPDATE ON posts
    FOR EACH ROW EXECUTE FUNCTION
    tsvector_update_trigger(search_vector, 'pg_catalog.english', title, content)
    """
)

event.listen(
    Post.__table__,
    'after_create',
    post_search_trigger.execute_if(dialect='postgresql')
)

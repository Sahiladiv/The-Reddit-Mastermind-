from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime,
    ForeignKey
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


# -------------------------
# Users
# -------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    posts = relationship("Post", back_populates="author", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="author", cascade="all, delete-orphan")


# -------------------------
# Subreddits
# -------------------------
class Subreddit(Base):
    __tablename__ = "subreddits"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)  # e.g. "presentations"
    title = Column(String(255))
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    posts = relationship("Post", back_populates="subreddit", cascade="all, delete-orphan")


# -------------------------
# Posts
# -------------------------
class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    subreddit_id = Column(Integer, ForeignKey("subreddits.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    query_id = Column(Integer, ForeignKey("queries.id"), nullable=True)  # <--- NEW
    query_text = Column(String(500))  # <--- OPTIONAL convenience copy

    title = Column(String(500), nullable=False)
    body = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    subreddit = relationship("Subreddit", back_populates="posts")
    author = relationship("User", back_populates="posts")

    query = relationship("Query", back_populates="posts")  # <--- NEW

    comments = relationship(
        "Comment",
        back_populates="post",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

# -------------------------
# Comments (threaded)
# -------------------------
class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    parent_comment_id = Column(Integer, ForeignKey("comments.id"), nullable=True)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    post = relationship("Post", back_populates="comments")
    author = relationship("User", back_populates="comments")

    # Threaded relationship
    parent = relationship(
        "Comment",
        remote_side=[id],
        back_populates="children",
        uselist=False,
    )
    children = relationship(
        "Comment",
        back_populates="parent",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

# -------------------------
# Queries
# -------------------------
class Query(Base):
    __tablename__ = "queries"

    id = Column(Integer, primary_key=True)
    text = Column(String(500), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    posts = relationship("Post", back_populates="query")

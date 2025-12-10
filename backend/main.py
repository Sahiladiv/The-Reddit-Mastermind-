from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from datetime import date, timedelta
from typing import Optional
import os
import json

# ----------------------------
# DB + Models
# ----------------------------
from database import SessionLocal
from models import User, Subreddit, Post, Comment, Query
from sqlalchemy.orm import Session

# ----------------------------
# Planning Engine
# ----------------------------
from planning_engine import (
    load_config,
    generate_conversation_calendar,
    LargeLangModel as GroqLLM,
)

from fastapi.middleware.cors import CORSMiddleware

# ------------------------------------------------------------
# FastAPI initialization
# ------------------------------------------------------------

app = FastAPI(
    title="OGTool Conversation Engine API",
    version="1.0.0",
    description="FastAPI wrapper for Slideforge NLG conversation engine."
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------
# Load config at startup
# ------------------------------------------------------------

CONFIG_PATH = os.environ.get("OGTOOL_CONFIG_PATH", "dataset/data.json")

try:
    CONFIG = load_config(CONFIG_PATH)
except Exception as e:
    raise RuntimeError(f"Failed to load config from {CONFIG_PATH}: {e}")

LLM = GroqLLM()


# ------------------------------------------------------------
# Request Models
# ------------------------------------------------------------

class WeekRequest(BaseModel):
    start_date: Optional[date] = None
    max_comments_per_thread: int = Field(default=6, ge=1, le=30)
    override_posts_per_week: Optional[int] = None


class MultiWeekRequest(BaseModel):
    num_weeks: int = Field(..., ge=1, le=52)
    output_dir: str = Field(default="output_weeks")
    max_comments_per_thread: int = 6


# ------------------------------------------------------------
# Helper DB Functions
# ------------------------------------------------------------

def get_or_create_user(db: Session, username: str):
    user = db.query(User).filter_by(username=username).first()
    if not user:
        user = User(username=username)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def get_or_create_subreddit(db: Session, name: str):
    clean = name.replace("r/", "")
    subreddit = db.query(Subreddit).filter_by(name=clean).first()
    if not subreddit:
        subreddit = Subreddit(name=clean, title=f"r/{clean}")
        db.add(subreddit)
        db.commit()
        db.refresh(subreddit)
    return subreddit


def get_or_create_query(db: Session, query_text: str):
    """Create or fetch query row."""
    q = db.query(Query).filter_by(text=query_text).first()
    if not q:
        q = Query(text=query_text)
        db.add(q)
        db.commit()
        db.refresh(q)
    return q


def build_comment_tree(comments):
    comment_map = {c.id: c for c in comments}

    for c in comments:
        c.children = []

    roots = []
    for c in comments:
        if c.parent_comment_id:
            parent = comment_map.get(c.parent_comment_id)
            if parent and c not in parent.children:
                parent.children.append(c)
        else:
            roots.append(c)

    return roots


# ------------------------------------------------------------
# Save generated week to DB
# ------------------------------------------------------------

def save_generated_week_to_db(db: Session, week_json: list):
    """
    Inserts generated JSON into DB:
    - queries
    - subreddits
    - posts
    - users
    - threaded comments
    """

    for entry in week_json:
        subreddit_name = entry["subreddit"]
        post_data = entry["post"]
        comments_data = entry["comments"]

        # Subreddit
        subreddit = get_or_create_subreddit(db, subreddit_name)

        # User
        author = get_or_create_user(db, post_data["author"])

        # Query (NEW)
        query_row = get_or_create_query(db, post_data["query"])

        # Post
        post = Post(
            subreddit_id=subreddit.id,
            user_id=author.id,
            title=post_data["title"],
            body=post_data["body"],
            query_id=query_row.id,         # <-- NEW
            query_text=post_data["query"]  # <-- NEW (optional convenience field)
        )
        db.add(post)
        db.commit()
        db.refresh(post)

        # Comments
        comment_map = {}

        for c in comments_data:
            comment_author = get_or_create_user(db, c["author"])

            parent_db_id = (
                comment_map[c["parent_comment_id"]].id
                if c["parent_comment_id"] in comment_map
                else None
            )

            comment = Comment(
                post_id=post.id,
                user_id=comment_author.id,
                parent_comment_id=parent_db_id,
                text=c["text"]
            )
            db.add(comment)
            db.commit()
            db.refresh(comment)

            comment_map[c["comment_id"]] = comment


# ------------------------------------------------------------
# Backend Endpoints
# ------------------------------------------------------------

@app.get("/subreddits")
def get_subreddits():
    db = SessionLocal()
    subs = db.query(Subreddit).all()
    db.close()
    return [
        {"id": s.id, "name": s.name, "title": s.title}
        for s in subs
    ]


@app.get("/subreddit/{name}/posts")
def get_posts_in_subreddit(name: str):
    db = SessionLocal()
    clean = name.replace("r/", "")

    subreddit = db.query(Subreddit).filter_by(name=clean).first()
    if not subreddit:
        db.close()
        raise HTTPException(status_code=404, detail="Subreddit not found")

    posts = db.query(Post).filter_by(subreddit_id=subreddit.id).all()
    db.close()

    return [
        {
            "id": p.id,
            "title": p.title,
            "body": p.body,
            "query_id": p.query_id,
            "query_text": p.query_text,
            "created_at": p.created_at
        }
        for p in posts
    ]


@app.get("/post/{post_id}")
def get_post_with_comments(post_id: int):
    db = SessionLocal()

    post = db.query(Post).filter_by(id=post_id).first()
    if not post:
        db.close()
        raise HTTPException(status_code=404, detail="Post not found")

    comments = db.query(Comment).filter_by(post_id=post.id).all()
    threaded = build_comment_tree(comments)

    def serialize_comment(c):
        return {
            "id": c.id,
            "text": c.text,
            "author": db.query(User).filter_by(id=c.user_id).first().username,
            "parent_comment_id": c.parent_comment_id,
            "children": [serialize_comment(child) for child in getattr(c, "children", [])]
        }

    result = {
        "id": post.id,
        "title": post.title,
        "body": post.body,
        "query_id": post.query_id,
        "query_text": post.query_text,
        "created_at": post.created_at,
        "comments": [serialize_comment(c) for c in threaded]
    }

    db.close()
    return result


# ------------------------------------------------------------
# Generation Endpoints
# ------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "engine": "running"}


@app.post("/generate-week")
def generate_week(req: WeekRequest):
    cfg = dict(CONFIG)

    if req.override_posts_per_week:
        cfg["posts_per_week"] = req.override_posts_per_week

    try:
        result = generate_conversation_calendar(
            config=cfg,
            llm=LLM,
            start_date=req.start_date,
            max_comments_per_thread=req.max_comments_per_thread,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating week: {e}")

    db = SessionLocal()
    try:
        save_generated_week_to_db(db, result)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"DB error: {e}")
    finally:
        db.close()

    return {"status": "saved", "data": result}


@app.post("/generate-weeks-and-save")
def generate_weeks_and_save(req: MultiWeekRequest):
    os.makedirs(req.output_dir, exist_ok=True)

    paths = []
    start = date.today()

    for week in range(1, req.num_weeks + 1):
        try:
            calendar = generate_conversation_calendar(
                config=CONFIG,
                llm=LLM,
                start_date=start,
                max_comments_per_thread=req.max_comments_per_thread,
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error generating week {week}: {e}"
            )

        filename = f"week_{week:02d}.json"
        path = os.path.join(req.output_dir, filename)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(calendar, f, indent=4, ensure_ascii=False)

        paths.append(path)
        start += timedelta(days=7)

    return {
        "status": "success",
        "weeks_generated": req.num_weeks,
        "files": paths,
    }

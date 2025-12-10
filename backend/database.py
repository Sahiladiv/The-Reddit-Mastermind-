import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()
# Load DATABASE_URL from Render environment variables
DATABASE_URL = (
    os.getenv("DATABASE_URL_INTERNAL") or
    os.getenv("DATABASE_URL")  # external for local
)

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set!")

# Create SQLAlchemy engine for PostgreSQL
engine = create_engine(
    DATABASE_URL,
    echo=True,       # optional: logs SQL queries
    future=True
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

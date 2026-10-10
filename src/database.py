"""
Database connection and session management for AI Farmer Assistant.

Supports PostgreSQL via psycopg2 / psycopg, with SQLite fallback for local test environments.
Uses SQLAlchemy 2.x declarative Base and sessionmaker.
"""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from src.config import get_settings

settings = get_settings()

db_url = settings.DATABASE_URL

# Configure engine arguments based on dialect
connect_args = {}
if db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    db_url,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for obtaining a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initializes database schema tables."""
    # Ensure models are imported before creating tables
    import src.models  # noqa: F401
    Base.metadata.create_all(bind=engine)

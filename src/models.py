"""
SQLAlchemy ORM models for AI Farmer Assistant.

Models:
- User: Account details, secure password hashes, preferred language
- UserSession: Server-side managed browser sessions with expiry and revocation
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Float
)
from sqlalchemy.orm import relationship

from src.database import Base


def utcnow() -> datetime:
    """Returns current UTC datetime with timezone."""
    return datetime.now(timezone.utc)


class User(Base):
    """User account entity."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(512), nullable=False)
    preferred_language = Column(String(10), default="en", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    analyses = relationship("Analysis", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"


class UserSession(Base):
    """Server-side browser session tracking."""
    __tablename__ = "user_sessions"

    id = Column(String(128), primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    csrf_token = Column(String(128), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    is_revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    user = relationship("User", back_populates="sessions")

    def is_expired(self) -> bool:
        """Checks if session has passed its expiration time."""
        now = utcnow()
        # Handle naive datetimes if sqlite returned naive
        exp = self.expires_at
        if exp.tzinfo is None:
            now = now.replace(tzinfo=None)
        return now >= exp

    def is_valid(self) -> bool:
        """Session is valid if not revoked and not expired."""
        return (not self.is_revoked) and (not self.is_expired())

    def __repr__(self) -> str:
        return f"<UserSession id={self.id} user_id={self.user_id} revoked={self.is_revoked}>"


class Analysis(Base):
    """Historical crop disease prediction record."""
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    crop = Column(String(100), nullable=False)
    disease_code = Column(String(128), nullable=False)
    disease_name = Column(String(255), nullable=False)
    confidence = Column(Float, nullable=False)
    model_version = Column(String(128), nullable=False)
    image_url = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    user = relationship("User", back_populates="analyses")

    def __repr__(self) -> str:
        return f"<Analysis id={self.id} user_id={self.user_id} disease={self.disease_code} conf={self.confidence}>"

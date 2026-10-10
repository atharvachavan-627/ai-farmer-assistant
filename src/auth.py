"""
Authentication, Session Management, and Security Services for AI Farmer Assistant.

Features:
- Argon2id password hashing and verification
- Persistent server-managed session storage
- HttpOnly secure session cookies
- Double-Submit CSRF cookie validation for state-changing requests
- FastAPI dependency injection for protected endpoints
"""

import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from fastapi import Request, Response, Depends, status
from sqlalchemy.orm import Session

from src.config import get_settings
from src.database import get_db
from src.models import User, UserSession

settings = get_settings()
_hasher = PasswordHasher()


class AuthException(Exception):
    """Custom authentication exception with code and message."""
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


def hash_password(password: str) -> str:
    """Hashes a plaintext password using Argon2id."""
    return _hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against a stored Argon2id hash."""
    try:
        return _hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
    except Exception:
        return False


def create_user_session(db: Session, user: User) -> UserSession:
    """
    Creates a new persistent server-side session for a user.
    Generates a secure random session ID and a matching CSRF token.
    """
    session_id = secrets.token_urlsafe(48)
    csrf_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.SESSION_EXPIRE_SECONDS)

    session_record = UserSession(
        id=session_id,
        user_id=user.id,
        csrf_token=csrf_token,
        expires_at=expires_at,
        is_revoked=False
    )
    db.add(session_record)
    db.commit()
    db.refresh(session_record)
    return session_record


def get_session_by_token(db: Session, token: str) -> Optional[UserSession]:
    """Retrieves an active, valid, non-expired session by token."""
    if not token:
        return None
    session_record = db.query(UserSession).filter(UserSession.id == token).first()
    if session_record and session_record.is_valid():
        return session_record
    return None


def revoke_user_session(db: Session, token: str) -> bool:
    """Revokes a session by token so it cannot be used again."""
    if not token:
        return False
    session_record = db.query(UserSession).filter(UserSession.id == token).first()
    if session_record:
        session_record.is_revoked = True
        db.commit()
        return True
    return False


def set_auth_cookies(response: Response, session: UserSession) -> None:
    """Sets session cookie (HttpOnly) and CSRF cookie (readable by frontend) on the response."""
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=session.id,
        httponly=True,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        secure=settings.SESSION_COOKIE_SECURE,
        max_age=settings.SESSION_EXPIRE_SECONDS,
        path="/"
    )
    # CSRF cookie is non-HttpOnly so client JS can read it and send X-CSRF-Token header
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=session.csrf_token,
        httponly=False,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        secure=settings.SESSION_COOKIE_SECURE,
        max_age=settings.SESSION_EXPIRE_SECONDS,
        path="/"
    )


def clear_auth_cookies(response: Response) -> None:
    """Clears both session and CSRF cookies on logout."""
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path="/"
    )
    response.delete_cookie(
        key=settings.CSRF_COOKIE_NAME,
        path="/"
    )


def extract_session_token(request: Request) -> Optional[str]:
    """
    Extracts session token from cookie (primary for web browsers)
    or Authorization: Bearer header (for API clients/automated test suites).
    """
    # 1. Check HttpOnly cookie
    cookie_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if cookie_token:
        return cookie_token

    # 2. Check Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:].strip()

    return None


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency that authenticates the user via session token.
    Validates CSRF token on state-changing requests when session is cookie-based.
    """
    session_token = extract_session_token(request)
    if not session_token:
        raise AuthException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="UNAUTHORIZED",
            message="Authentication required. Please sign in."
        )

    session_record = get_session_by_token(db, session_token)
    if not session_record:
        raise AuthException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="SESSION_EXPIRED",
            message="Session is invalid or expired. Please sign in again."
        )

    # CSRF validation: If request was authenticated via Cookie and is a state-changing method
    is_cookie_auth = settings.SESSION_COOKIE_NAME in request.cookies
    if is_cookie_auth and request.method in ("POST", "PUT", "PATCH", "DELETE"):
        csrf_header = request.headers.get(settings.CSRF_HEADER_NAME)
        csrf_cookie = request.cookies.get(settings.CSRF_COOKIE_NAME)
        
        # Verify CSRF header matches either cookie or stored session token
        if not csrf_header or (csrf_header != session_record.csrf_token and csrf_header != csrf_cookie):
            raise AuthException(
                status_code=status.HTTP_403_FORBIDDEN,
                code="CSRF_ERROR",
                message="CSRF protection token missing or invalid."
            )

    user = db.query(User).filter(User.id == session_record.user_id).first()
    if not user:
        raise AuthException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="USER_NOT_FOUND",
            message="Associated user account no longer exists."
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Verifies that the authenticated user account is active."""
    if not current_user.is_active:
        raise AuthException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="USER_INACTIVE",
            message="Account has been deactivated."
        )
    return current_user

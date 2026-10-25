import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Request, Response, WebSocket, Depends, status
from sqlalchemy.orm import Session
from ..config import settings
from ..database import get_db
from ..models import User, UserSession
from ..errors import AppException


def generate_session_token() -> str:
    """Generate a high-entropy URL-safe cryptographic session token (256 bits)."""
    return secrets.token_urlsafe(32)


def create_user_session(
    db: Session,
    user_id: int,
    request: Optional[Request] = None,
) -> UserSession:
    """
    Create a new server-side session for a user.
    Handles duplicate logins cleanly:
    - Prunes expired sessions for this user.
    - If user has >= MAX_SESSIONS_PER_USER, evicts the oldest active session.
    """
    now = datetime.utcnow()

    # 1. Prune expired sessions for this user
    db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.expires_at <= now,
    ).delete()

    # 2. Check active session count and prune oldest if limit reached
    active_sessions = (
        db.query(UserSession)
        .filter(UserSession.user_id == user_id, UserSession.expires_at > now)
        .order_by(UserSession.created_at.asc())
        .all()
    )

    if len(active_sessions) >= settings.MAX_SESSIONS_PER_USER:
        excess = len(active_sessions) - settings.MAX_SESSIONS_PER_USER + 1
        for old_session in active_sessions[:excess]:
            db.delete(old_session)

    # 3. Create fresh session
    token = generate_session_token()
    expires_at = now + timedelta(hours=settings.SESSION_EXPIRE_HOURS)

    ip_address = None
    user_agent = None
    if request:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")[:255] if request.headers.get("user-agent") else None

    session = UserSession(
        id=token,
        user_id=user_id,
        expires_at=expires_at,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def delete_user_session(db: Session, session_id: str):
    """Delete a specific session token from database."""
    db.query(UserSession).filter(UserSession.id == session_id).delete()
    db.commit()


def set_session_cookie(response: Response, session_id: str):
    """
    Attach HTTP-only session cookie with settings appropriate for LAN deployment.
    Does NOT leak session tokens into URLs or log streams.
    """
    max_age_seconds = settings.SESSION_EXPIRE_HOURS * 3600
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=session_id,
        max_age=max_age_seconds,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        path="/",
    )


def clear_session_cookie(response: Response):
    """Clear the session cookie from the browser."""
    response.delete_cookie(
        key=settings.COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
    )


def extract_session_token(request: Request) -> Optional[str]:
    """Extract session token primarily from HTTP-only cookie, or fallback to Authorization header or query param."""
    # 1. Primary: HTTP-only cookie
    token = request.cookies.get(settings.COOKIE_NAME)
    if token:
        return token

    # 2. Secondary fallback: Authorization header (Bearer <token>) for API clients/tests
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()

    # 3. Tertiary fallback: Query parameter for direct downloads or media links
    query_token = request.query_params.get("token") or request.query_params.get(settings.COOKIE_NAME)
    if query_token:
        return query_token

    return None


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency: Authenticates user from HTTP-only session cookie or raises 401."""
    token = extract_session_token(request)
    if not token:
        raise AppException(
            message="Authentication required. Please sign in.",
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="UNAUTHORIZED",
        )

    session = db.query(UserSession).filter(UserSession.id == token).first()
    if not session or session.is_expired():
        if session:
            db.delete(session)
            db.commit()
        raise AppException(
            message="Session expired or invalid. Please sign in again.",
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="SESSION_EXPIRED",
        )

    user = db.query(User).filter(User.id == session.user_id, User.is_active == True).first()
    if not user:
        raise AppException(
            message="User account not found or inactive.",
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="USER_INACTIVE",
        )

    return user


def get_ws_authenticated_user(
    websocket: WebSocket,
    db: Session,
) -> Optional[User]:
    """
    Authenticates WebSocket connections using HTTP-only cookies sent during the handshake.
    Never requires or exposes tokens in query parameters/URLs.
    """
    token = websocket.cookies.get(settings.COOKIE_NAME)
    if not token:
        return None

    session = db.query(UserSession).filter(UserSession.id == token).first()
    if not session or session.is_expired():
        return None

    user = db.query(User).filter(User.id == session.user_id, User.is_active == True).first()
    return user

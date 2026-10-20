from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User
from ..schemas.auth import RegisterRequest, LoginRequest, AuthUserResponse
from ..security import (
    hash_password,
    verify_password,
    needs_rehash,
    create_user_session,
    delete_user_session,
    set_session_cookie,
    clear_session_cookie,
    get_current_user,
)
from ..security.sessions import extract_session_token
from ..services.rate_limiter import auth_rate_limiter
from ..errors import AppException, ConflictException

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=AuthUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register New LAN User",
)
def register(
    req: RegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Register a new unique username on the local LAN.
    Stores Argon2id salted password hash and establishes a secure browser session.
    """
    # 0. Brute-force & registration spam protection
    client_ip = request.client.host if request.client else "127.0.0.1"
    if not auth_rate_limiter.is_allowed(client_ip):
        raise AppException(
            message="Too many registration attempts. Please wait a minute before trying again.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code="RATE_LIMITED",
        )

    # 1. Check for duplicate username
    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise ConflictException(
            message=f"Username '{req.username}' is already taken on this network.",
            details={"field": "username"},
        )

    # 2. Hash password with Argon2id
    hashed_pwd = hash_password(req.password)

    # 3. Derive display name and avatar initials
    display_name = req.display_name.strip() if req.display_name else req.username
    avatar = display_name[:2].upper()

    # 4. Create and persist user
    user = User(
        username=req.username,
        password_hash=hashed_pwd,
        display_name=display_name,
        avatar=avatar,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 5. Establish session & set HTTP-only cookie
    session = create_user_session(db, user.id, request)
    set_session_cookie(response, session.id)

    return AuthUserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=AuthUserResponse,
    status_code=status.HTTP_200_OK,
    summary="Sign In with LAN Username and Password",
)
def login(
    req: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Authenticate username and password against stored Argon2id hash.
    Sets an HTTP-only cookie for secure browser access.
    """
    # 0. Brute-force & credential stuffing protection
    client_ip = request.client.host if request.client else "127.0.0.1"
    if not auth_rate_limiter.is_allowed(client_ip):
        raise AppException(
            message="Too many login attempts. Please wait a minute before trying again.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code="RATE_LIMITED",
        )

    # 1. Lookup user
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not user.password_hash:
        raise AppException(
            message="Invalid username or password.",
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="INVALID_CREDENTIALS",
        )

    # 2. Verify password with Argon2id
    if not verify_password(req.password, user.password_hash):
        raise AppException(
            message="Invalid username or password.",
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="INVALID_CREDENTIALS",
        )

    # 3. Check if password needs rehashing to upgraded cost parameters
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(req.password)
        db.commit()

    # 4. Establish session & set HTTP-only cookie
    session = create_user_session(db, user.id, request)
    set_session_cookie(response, session.id)

    return AuthUserResponse.model_validate(user)


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Sign Out of LAN Session",
)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Invalidate current session in database and delete browser session cookie.
    """
    token = extract_session_token(request)
    if token:
        delete_user_session(db, token)

    clear_session_cookie(response)
    return {"success": True, "message": "Successfully signed out."}


@router.get(
    "/me",
    response_model=AuthUserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Current Authenticated User",
)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Returns current authenticated user identity verified from HTTP-only session cookie.
    """
    return AuthUserResponse.model_validate(current_user)

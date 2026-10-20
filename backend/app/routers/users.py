from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from ..database import get_db
from ..models import User
from ..schemas.auth import UserWithPresence
from ..security import get_current_user
from ..websocket.manager import ws_manager

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get(
    "",
    response_model=List[UserWithPresence],
    status_code=status.HTTP_200_OK,
    summary="List and Search LAN Users with Real-Time Presence",
)
def list_users(
    q: Optional[str] = Query(None, description="Search query by username or display name"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Search and retrieve list of available users on the local network.
    Includes dynamically computed real-time presence (online/offline) from active WebSocket sessions.
    Requires authenticated session.
    """
    query = db.query(User).filter(User.is_active == True)

    if q and q.strip():
        term = f"%{q.strip().lower()}%"
        query = query.filter(
            or_(
                User.username.ilike(term),
                User.display_name.ilike(term),
            )
        )

    users = query.order_by(User.username.asc()).all()

    return [
        UserWithPresence(
            id=u.id,
            username=u.username,
            display_name=u.display_name,
            avatar=u.avatar,
            is_online=ws_manager.is_user_online(u.id),
            last_seen=u.last_seen,
        )
        for u in users
    ]

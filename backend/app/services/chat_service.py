import re
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from ..models import Conversation, ConversationMember, Message, User
from ..errors import AppException
from ..logging_config import logger


def validate_conversation_id_format(conversation_id: str) -> str:
    """Validate conversation identifier format to prevent injection and traversal attempts."""
    if not conversation_id or not isinstance(conversation_id, str):
        raise AppException(
            status_code=400,
            message="Invalid conversation identifier.",
            error_code="INVALID_CONVERSATION_ID",
        )
    clean_id = conversation_id.strip()
    if not re.match(r"^[a-zA-Z0-9_\-]{3,64}$", clean_id) or ".." in clean_id:
        raise AppException(
            status_code=400,
            message="Invalid conversation identifier format.",
            error_code="INVALID_CONVERSATION_ID",
        )
    return clean_id


def get_canonical_dm_id(user_a_id: int, user_b_id: int) -> str:
    """Generate deterministic, canonical identifier for 1-to-1 direct conversations."""
    low, high = sorted([user_a_id, user_b_id])
    return f"dm_{low}_{high}"


def get_or_create_broadcast_channel(db: Session) -> Conversation:
    """Retrieve or initialize the global '#general-lan' broadcast channel."""
    broadcast = db.query(Conversation).filter(Conversation.id == "broadcast-general").first()
    if not broadcast:
        broadcast = Conversation(
            id="broadcast-general",
            type="broadcast",
            name="#general-lan",
        )
        db.add(broadcast)
        db.commit()
        db.refresh(broadcast)
    return broadcast


def get_or_create_direct_conversation(db: Session, user_a_id: int, user_b_id: int) -> Conversation:
    """
    Retrieve or create a direct 1-to-1 conversation between two registered LAN users.
    Ensures Conversation and ConversationMember records exist.
    """
    if user_a_id == user_b_id:
        raise AppException(
            status_code=400,
            message="Cannot establish a direct conversation with yourself.",
            error_code="INVALID_RECIPIENT",
        )

    # Verify both users exist in database
    target_user = db.query(User).filter(User.id == user_b_id).first()
    if not target_user:
        raise AppException(
            status_code=404,
            message="Recipient user not found.",
            error_code="USER_NOT_FOUND",
        )

    dm_id = get_canonical_dm_id(user_a_id, user_b_id)
    conversation = db.query(Conversation).filter(Conversation.id == dm_id).first()

    if not conversation:
        conversation = Conversation(
            id=dm_id,
            type="direct",
            name=None,
        )
        db.add(conversation)
        db.flush()

        # Add membership records for both users
        member_a = ConversationMember(conversation_id=dm_id, user_id=user_a_id, role="member")
        member_b = ConversationMember(conversation_id=dm_id, user_id=user_b_id, role="member")
        db.add_all([member_a, member_b])
        db.commit()
        db.refresh(conversation)

    return conversation


def verify_conversation_access(db: Session, user_id: int, conversation_id: str) -> Conversation:
    """
    Verify that a user is authorized to access a conversation.
    - Broadcast channels are accessible to all authenticated users.
    - Direct and group channels require verified membership.
    Raises AppException(400) if format is invalid, AppException(404) if not found, or AppException(403) if unauthorized.
    """
    clean_id = validate_conversation_id_format(conversation_id)
    conversation = db.query(Conversation).filter(Conversation.id == clean_id).first()
    if not conversation:
        raise AppException(
            status_code=404,
            message="Conversation not found.",
            error_code="CONVERSATION_NOT_FOUND",
        )

    if conversation.type == "broadcast":
        return conversation

    # Check membership for private direct / group conversations
    membership = (
        db.query(ConversationMember)
        .filter(
            ConversationMember.conversation_id == conversation_id,
            ConversationMember.user_id == user_id,
        )
        .first()
    )

    if not membership:
        raise AppException(
            status_code=403,
            message="Access forbidden. You are not a member of this private conversation.",
            error_code="ACCESS_FORBIDDEN",
        )

    return conversation


def get_conversation_member_ids(db: Session, conversation_id: str) -> List[int]:
    """Retrieve user IDs of all members in a conversation."""
    members = (
        db.query(ConversationMember.user_id)
        .filter(ConversationMember.conversation_id == conversation_id)
        .all()
    )
    return [m[0] for m in members]


def save_message(
    db: Session,
    sender_id: int,
    conversation_id: str,
    content: str,
    client_msg_id: Optional[str] = None,
    message_type: str = "text",
) -> Tuple[Message, bool]:
    """
    Validate, deduplicate, and persist a chat message to SQLite.
    Returns (message, is_new: bool).
    If client_msg_id already exists in this conversation, returns the existing record (idempotency).
    """
    clean_content = content.strip()
    if not clean_content:
        raise AppException(
            status_code=400,
            message="Message content cannot be empty.",
            error_code="EMPTY_CONTENT",
        )

    if len(clean_content) > 2000:
        raise AppException(
            status_code=400,
            message="Message exceeds maximum allowed length of 2000 characters.",
            error_code="CONTENT_TOO_LONG",
        )

    # Idempotency / deduplication check
    if client_msg_id:
        existing = (
            db.query(Message)
            .filter(
                Message.conversation_id == conversation_id,
                Message.client_msg_id == client_msg_id,
            )
            .first()
        )
        if existing:
            logger.info(
                f"Idempotent message replay detected: client_msg_id={client_msg_id}, message_id={existing.id}"
            )
            return existing, False

    # Persist new message
    msg = Message(
        conversation_id=conversation_id,
        sender_id=sender_id,
        content=clean_content,
        message_type=message_type,
        client_msg_id=client_msg_id,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    # Safe logging: log event metadata only, avoid logging user message bodies
    logger.info(
        f"Message persisted: id={msg.id}, conv={conversation_id}, sender={sender_id}, type={message_type}"
    )
    return msg, True


def get_conversation_messages(
    db: Session,
    conversation_id: str,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[Message], int, bool]:
    """
    Retrieve paginated messages for a conversation in chronological order (oldest -> newest).
    Returns (messages, total_count, has_more).
    """
    limit = min(max(1, limit), 100)
    offset = max(0, offset)

    total = db.query(func.count(Message.id)).filter(Message.conversation_id == conversation_id).scalar() or 0

    # Retrieve most recent messages up to limit + offset, ordered descending then reversed
    query_results = (
        db.query(Message)
        .options(joinedload(Message.file_record), joinedload(Message.sender))
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    chronological = list(reversed(query_results))
    has_more = (offset + len(query_results)) < total

    return chronological, total, has_more


def get_user_conversations(
    db: Session,
    current_user_id: int,
    is_user_online_fn=None,
) -> List[Dict[str, Any]]:
    """
    Retrieve all conversations accessible to the current user (broadcast + direct peers).
    Includes latest message preview, unread status, and peer metadata.
    """
    results: List[Dict[str, Any]] = []

    # 1. Global Broadcast Channel
    broadcast = get_or_create_broadcast_channel(db)
    last_broadcast_msg = (
        db.query(Message)
        .filter(Message.conversation_id == broadcast.id)
        .order_by(Message.id.desc())
        .first()
    )

    results.append({
        "id": broadcast.id,
        "type": "channel",
        "name": broadcast.name,
        "subtitle": "Public LAN Broadcast Channel",
        "avatar": "#",
        "status": "online",
        "ipAddress": "LAN Broadcast",
        "encryptionStatus": "LAN Broadcast (Public)",
        "last_message": last_broadcast_msg,
        "peer": None,
    })

    # 2. Direct Conversations where current_user is a member
    memberships = (
        db.query(ConversationMember)
        .filter(ConversationMember.user_id == current_user_id)
        .all()
    )

    for mem in memberships:
        conv = db.query(Conversation).filter(Conversation.id == mem.conversation_id).first()
        if not conv or conv.type == "broadcast":
            continue

        # Find the other peer in this direct conversation
        peer_member = (
            db.query(ConversationMember)
            .filter(
                ConversationMember.conversation_id == conv.id,
                ConversationMember.user_id != current_user_id,
            )
            .first()
        )

        if not peer_member:
            continue

        peer_user = db.query(User).filter(User.id == peer_member.user_id).first()
        if not peer_user:
            continue

        last_dm_msg = (
            db.query(Message)
            .filter(Message.conversation_id == conv.id)
            .order_by(Message.id.desc())
            .first()
        )

        is_online = is_user_online_fn(peer_user.id) if is_user_online_fn else False

        results.append({
            "id": conv.id,
            "type": "direct",
            "name": peer_user.display_name or peer_user.username,
            "username": peer_user.username,
            "subtitle": f"Direct chat with @{peer_user.username}",
            "avatar": peer_user.avatar or peer_user.username[:2].upper(),
            "status": "online" if is_online else "offline",
            "ipAddress": "192.168.1.xxx",
            "encryptionStatus": "Private LAN Session",
            "last_message": last_dm_msg,
            "peer": peer_user,
        })

    return results

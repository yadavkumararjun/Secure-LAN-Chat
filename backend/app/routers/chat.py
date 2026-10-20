from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, Message
from ..errors import AppException
from ..security.sessions import get_current_user
from ..websocket.manager import ws_manager
from ..services.rate_limiter import chat_rate_limiter
from ..services import chat_service
from ..schemas.file import FileAttachmentInfo, format_file_size
from ..schemas.chat import (
    ConversationSummaryResponse,
    DirectConversationRequest,
    ChatMessageResponse,
    MessageSenderInfo,
    SendMessageRequest,
    PaginatedMessagesResponse,
)

router = APIRouter(prefix="/api/conversations", tags=["Conversations & Real-Time Chat"])


def serialize_message(msg: Message) -> ChatMessageResponse:
    sender_info = None
    if msg.sender:
        sender_info = MessageSenderInfo(
            id=msg.sender.id,
            username=msg.sender.username,
            display_name=msg.sender.display_name,
            avatar=msg.sender.avatar or msg.sender.username[:2].upper(),
        )
    file_info = None
    if msg.file_record:
        file_info = FileAttachmentInfo(
            id=msg.file_record.id,
            name=msg.file_record.original_name,
            size=format_file_size(msg.file_record.file_size),
            bytes=msg.file_record.file_size,
            type=msg.file_record.mime_type,
            checksum=msg.file_record.checksum_sha256,
            download_url=f"/api/files/{msg.file_record.id}/download",
        )
    return ChatMessageResponse(
        id=msg.id,
        conversation_id=msg.conversation_id,
        sender=sender_info,
        content=msg.content,
        message_type=msg.message_type,
        client_msg_id=msg.client_msg_id,
        file=file_info,
        created_at=msg.created_at,
    )


# Alias for internal backwards compatibility
_serialize_message = serialize_message


@router.get("", response_model=List[ConversationSummaryResponse])
def get_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve all conversations accessible to the current user.
    Includes the public '#general-lan' broadcast channel and all active direct peer chats.
    """
    raw_convs = chat_service.get_user_conversations(
        db=db,
        current_user_id=current_user.id,
        is_user_online_fn=ws_manager.is_user_online,
    )

    summaries = []
    for c in raw_convs:
        last_msg = _serialize_message(c["last_message"]) if c["last_message"] else None
        peer_info = None
        if c["peer"]:
            peer_info = MessageSenderInfo(
                id=c["peer"].id,
                username=c["peer"].username,
                display_name=c["peer"].display_name,
                avatar=c["peer"].avatar or c["peer"].username[:2].upper(),
            )

        summaries.append(
            ConversationSummaryResponse(
                id=c["id"],
                type=c["type"],
                name=c["name"],
                username=c.get("username"),
                subtitle=c.get("subtitle"),
                avatar=c.get("avatar"),
                status=c.get("status", "offline"),
                ipAddress=c.get("ipAddress", "192.168.1.xxx"),
                encryptionStatus=c.get("encryptionStatus", "Private LAN Session"),
                last_message=last_msg,
                peer=peer_info,
            )
        )

    return summaries


@router.post("/direct", response_model=ConversationSummaryResponse, status_code=status.HTTP_200_OK)
def open_direct_conversation(
    payload: DirectConversationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get or create a verified 1-to-1 direct conversation with a LAN peer.
    Ensures conversation and membership records exist in SQLite.
    """
    conv = chat_service.get_or_create_direct_conversation(
        db=db,
        user_a_id=current_user.id,
        user_b_id=payload.recipient_id,
    )

    peer_user = db.query(User).filter(User.id == payload.recipient_id).first()
    if not peer_user:
        raise AppException(status_code=404, message="Recipient peer not found.")

    last_msg = (
        db.query(Message)
        .filter(Message.conversation_id == conv.id)
        .order_by(Message.id.desc())
        .first()
    )

    is_online = ws_manager.is_user_online(peer_user.id)

    return ConversationSummaryResponse(
        id=conv.id,
        type="direct",
        name=peer_user.display_name or peer_user.username,
        username=peer_user.username,
        subtitle=f"Direct chat with @{peer_user.username}",
        avatar=peer_user.avatar or peer_user.username[:2].upper(),
        status="online" if is_online else "offline",
        ipAddress="192.168.1.xxx",
        encryptionStatus="Private LAN Session",
        last_message=_serialize_message(last_msg) if last_msg else None,
        peer=MessageSenderInfo(
            id=peer_user.id,
            username=peer_user.username,
            display_name=peer_user.display_name,
            avatar=peer_user.avatar or peer_user.username[:2].upper(),
        ),
    )


@router.get("/{conversation_id}/messages", response_model=PaginatedMessagesResponse)
def get_conversation_history(
    conversation_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Load paginated message history for a conversation.
    Strictly verifies conversation membership on every request (prevents unauthorized reading).
    """
    # Verify membership & authorization
    chat_service.verify_conversation_access(db, current_user.id, conversation_id)

    messages, total, has_more = chat_service.get_conversation_messages(
        db=db,
        conversation_id=conversation_id,
        limit=limit,
        offset=offset,
    )

    return PaginatedMessagesResponse(
        conversation_id=conversation_id,
        total=total,
        limit=limit,
        offset=offset,
        has_more=has_more,
        messages=[_serialize_message(m) for m in messages],
    )


@router.post("/{conversation_id}/messages", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message_rest(
    conversation_id: str,
    payload: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    REST fallback endpoint to send a message.
    Validates authorization, rate limits, persists to SQLite, and broadcasts real-time WebSocket events.
    """
    # 1. Rate limiting check
    if not chat_rate_limiter.is_allowed(current_user.id):
        raise AppException(
            status_code=429,
            message="Rate limit exceeded. Please wait a moment before sending more messages.",
            error_code="RATE_LIMITED",
        )

    # 2. Authorization check
    conv = chat_service.verify_conversation_access(db, current_user.id, conversation_id)

    # 3. Persist and deduplicate
    msg, is_new = chat_service.save_message(
        db=db,
        sender_id=current_user.id,
        conversation_id=conversation_id,
        content=payload.content,
        client_msg_id=payload.client_msg_id,
        message_type=payload.message_type,
    )

    # 4. Dispatch WebSocket event to connected peers if newly persisted
    if is_new:
        serialized_msg = _serialize_message(msg).model_dump(mode="json")
        ws_event_payload = {
            "message": serialized_msg,
            "conversation_id": conversation_id,
        }

        if conv.type == "broadcast":
            await ws_manager.broadcast_event("NEW_MESSAGE", ws_event_payload)
        else:
            member_ids = chat_service.get_conversation_member_ids(db, conversation_id)
            await ws_manager.send_to_users(member_ids, "NEW_MESSAGE", ws_event_payload)

    return _serialize_message(msg)

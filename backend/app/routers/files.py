from typing import Optional
from urllib.parse import quote
from fastapi import APIRouter, Depends, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, Conversation
from ..errors import AppException
from ..logging_config import logger
from ..security.sessions import get_current_user
from ..services.rate_limiter import upload_rate_limiter
from ..websocket.manager import ws_manager
from ..services import file_service, chat_service
from ..schemas.file import FileRecordResponse, format_file_size
from .chat import serialize_message

router = APIRouter(prefix="/api/files", tags=["File Sharing"])


@router.post("/upload", response_model=FileRecordResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    conversation_id: str = Form(...),
    caption: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload a file stream into a conversation.
    - Validates conversation access.
    - Enforces upload rate limits per user.
    - Streams chunk-by-chunk to isolated disk storage (enforcing 50 MB quota).
    - Calculates SHA-256 integrity hash during ingest.
    - Creates FileRecord and linked Message in SQLite.
    - Dispatches real-time NEW_MESSAGE WebSocket event to conversation members.
    """
    logger.info(f"Incoming file upload: '{file.filename}', conv={conversation_id}, user={current_user.username} (ID {current_user.id})")

    if not upload_rate_limiter.is_allowed(current_user.id):
        raise AppException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            message="Upload rate limit reached. Please wait a moment before sharing more files.",
            error_code="RATE_LIMITED",
        )

    # Support placeholder 'user-{id}' conversation identifiers by automatically resolving them
    if conversation_id.startswith("user-"):
        try:
            target_user_id = int(conversation_id.split("-", 1)[1])
            dm_conv = chat_service.get_or_create_direct_conversation(db, current_user.id, target_user_id)
            conversation_id = dm_conv.id
        except (ValueError, IndexError):
            raise AppException(
                status_code=400,
                message="Invalid conversation identifier.",
                error_code="INVALID_CONVERSATION_ID",
            )

    file_record, message = await file_service.save_upload_stream(
        file=file,
        conversation_id=conversation_id,
        uploader_id=current_user.id,
        db=db,
        caption=caption,
    )

    # Dispatch real-time WebSocket event to active conversation peers
    serialized_msg = serialize_message(message)
    serialized_msg_dict = serialized_msg.model_dump(mode="json")
    ws_event_payload = {
        "message": serialized_msg_dict,
        "conversation_id": conversation_id,
    }

    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conv and conv.type == "broadcast":
        await ws_manager.broadcast_event("NEW_MESSAGE", ws_event_payload)
    else:
        member_ids = chat_service.get_conversation_member_ids(db, conversation_id)
        await ws_manager.send_to_users(member_ids, "NEW_MESSAGE", ws_event_payload)

    return FileRecordResponse(
        id=file_record.id,
        conversation_id=file_record.conversation_id,
        message_id=file_record.message_id,
        uploader_id=file_record.uploader_id,
        original_name=file_record.original_name,
        stored_filename=file_record.stored_filename,
        file_size=file_record.file_size,
        size_formatted=format_file_size(file_record.file_size),
        mime_type=file_record.mime_type,
        checksum_sha256=file_record.checksum_sha256,
        download_url=f"/api/files/{file_record.id}/download",
        created_at=file_record.created_at,
        message=serialized_msg,
    )


@router.get("/{file_id}/download")
def download_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Stream download of an authorized file.
    - Enforces conversation membership authorization (unrelated users get 403 Forbidden).
    - Prevents directory traversal attacks.
    - Includes SHA-256 integrity header and Content-Disposition attachment.
    """
    file_path, file_record = file_service.get_file_for_download(
        file_id=file_id,
        user_id=current_user.id,
        db=db,
    )

    safe_name = file_record.original_name.replace('"', '\\"')
    encoded_filename = quote(file_record.original_name)
    headers = {
        "Content-Disposition": f'attachment; filename="{safe_name}"; filename*=UTF-8\'\'{encoded_filename}',
        "X-Content-Type-Options": "nosniff",
        "X-File-Checksum-SHA256": file_record.checksum_sha256,
        "Access-Control-Expose-Headers": "Content-Disposition, X-File-Checksum-SHA256",
    }

    return FileResponse(
        path=str(file_path),
        filename=file_record.original_name,
        media_type=file_record.mime_type,
        headers=headers,
    )


@router.get("/{file_id}", response_model=FileRecordResponse)
def get_file_metadata(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve metadata for a shared file.
    Validates that requester has access to the associated conversation.
    """
    _, file_record = file_service.get_file_for_download(
        file_id=file_id,
        user_id=current_user.id,
        db=db,
    )

    return FileRecordResponse(
        id=file_record.id,
        conversation_id=file_record.conversation_id,
        message_id=file_record.message_id,
        uploader_id=file_record.uploader_id,
        original_name=file_record.original_name,
        stored_filename=file_record.stored_filename,
        file_size=file_record.file_size,
        size_formatted=format_file_size(file_record.file_size),
        mime_type=file_record.mime_type,
        checksum_sha256=file_record.checksum_sha256,
        download_url=f"/api/files/{file_record.id}/download",
        created_at=file_record.created_at,
    )

import re
import uuid
import hashlib
import mimetypes
from pathlib import Path
from typing import Optional, Tuple
from fastapi import UploadFile
from sqlalchemy.orm import Session
from ..config import settings
from ..models import FileRecord, Message
from ..errors import AppException
from ..logging_config import logger
from . import chat_service


def sanitize_filename(filename: Optional[str]) -> str:
    """
    Sanitize an untrusted user-supplied filename:
    - Strips path components (directory traversal attempts like '../' or '..\\').
    - Removes null bytes and non-printable control characters.
    - Strips unsafe filesystem characters while preserving valid extensions.
    - Caps total length at 255 characters.
    """
    if not filename:
        return "attachment.bin"

    # 1. Extract purely the base name to eliminate any path separators
    base = Path(filename).name
    # Further ensure both POSIX and Windows separators are stripped
    base = base.replace("\\", "/").split("/")[-1]

    # 2. Strip null bytes and control characters
    base = re.sub(r"[\x00-\x1f\x7f]", "", base)

    # 3. Replace potentially harmful characters (colon, pipe, angle brackets, etc.) with underscore
    base = re.sub(r'[<>:"/\\|?*]', "_", base).strip(" .")

    if not base:
        return "attachment.bin"

    # 4. Truncate to maximum 255 characters while preserving file extension
    if len(base) > 255:
        ext = Path(base).suffix[:20]  # keep reasonable extension
        stem = base[: 255 - len(ext)]
        base = stem + ext

    return base


def get_safe_storage_path(stored_filename: str) -> Path:
    """
    Resolve a stored file path and guarantee it resides strictly inside
    the configured sandboxed uploads directory.
    Mitigates path traversal attempts.
    """
    upload_dir = settings.get_absolute_upload_dir().resolve()
    target_path = (upload_dir / stored_filename).resolve()

    # Verify that the target path is strictly a direct child of the upload directory
    if target_path.parent != upload_dir:
        logger.warning(f"Path traversal blocked for stored filename: {stored_filename}")
        raise AppException(
            status_code=400,
            message="Invalid or unsafe storage identifier.",
            error_code="PATH_TRAVERSAL_DETECTED",
        )

    return target_path


async def save_upload_stream(
    file: UploadFile,
    conversation_id: str,
    uploader_id: int,
    db: Session,
    caption: Optional[str] = None,
) -> Tuple[FileRecord, Message]:
    """
    Stream an uploaded file chunk-by-chunk to a temporary file on disk,
    compute SHA-256 checksum during ingest, enforce strict file size limits,
    atomically promote to permanent UUID storage, and persist metadata in SQLite.
    """
    # 1. Verify access to target conversation before ingesting file
    chat_service.verify_conversation_access(db, uploader_id, conversation_id)

    # 2. Sanitize user-provided filename
    clean_filename = sanitize_filename(file.filename)

    # 3. Resolve upload directories
    upload_dir = settings.get_absolute_upload_dir()
    upload_dir.mkdir(parents=True, exist_ok=True)

    storage_id = uuid.uuid4().hex
    temp_filename = f"{storage_id}.tmp"
    stored_filename = f"{storage_id}.bin"

    temp_path = upload_dir / temp_filename
    final_path = upload_dir / stored_filename

    hasher = hashlib.sha256()
    total_bytes = 0
    chunk_size = 64 * 1024  # 64 KB streaming buffer

    try:
        with open(temp_path, "wb") as f_out:
            while chunk := await file.read(chunk_size):
                total_bytes += len(chunk)
                if total_bytes > settings.MAX_UPLOAD_SIZE_BYTES:
                    max_mb = settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
                    raise AppException(
                        status_code=413,
                        message=f"File exceeds maximum allowed upload quota of {max_mb} MB.",
                        error_code="FILE_TOO_LARGE",
                    )
                f_out.write(chunk)
                hasher.update(chunk)

        if total_bytes == 0:
            raise AppException(
                status_code=400,
                message="Uploaded file cannot be empty (0 bytes).",
                error_code="EMPTY_FILE",
            )

        # Atomically promote temporary file to final isolated storage
        temp_path.rename(final_path)

    except Exception as e:
        # Guarantee cleanup of incomplete or abandoned temporary files on client disconnect or error
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        if not isinstance(e, AppException):
            logger.error(f"Error during file upload ingest: {e}", exc_info=True)
            raise AppException(
                status_code=500,
                message="Failed to process file upload.",
                error_code="UPLOAD_INGEST_ERROR",
            )
        raise e

    # 4. Resolve MIME type
    detected_mime, _ = mimetypes.guess_type(clean_filename)
    mime_type = file.content_type or detected_mime or "application/octet-stream"
    checksum = hasher.hexdigest()

    # 5. Persist FileRecord and Message in SQLite
    file_record = FileRecord(
        conversation_id=conversation_id,
        uploader_id=uploader_id,
        original_name=clean_filename,
        stored_filename=stored_filename,
        file_size=total_bytes,
        mime_type=mime_type,
        checksum_sha256=checksum,
    )
    db.add(file_record)
    db.flush()

    msg_content = caption.strip() if (caption and caption.strip()) else f"Shared file: {clean_filename}"
    message = Message(
        conversation_id=conversation_id,
        sender_id=uploader_id,
        content=msg_content,
        message_type="file",
    )
    db.add(message)
    db.flush()

    # Link file record to message
    file_record.message_id = message.id
    db.commit()
    db.refresh(file_record)
    db.refresh(message)

    logger.info(
        f"File shared successfully: id={file_record.id}, conv={conversation_id}, "
        f"name='{clean_filename}', size={total_bytes} bytes, sha256={checksum[:12]}..."
    )

    return file_record, message


def get_file_for_download(file_id: int, user_id: int, db: Session) -> Tuple[Path, FileRecord]:
    """
    Retrieve and authorize a file for download:
    - Verifies file record exists in SQLite.
    - Enforces conversation membership authorization (unrelated users get 403 Forbidden).
    - Safely resolves the storage path on disk.
    Returns (Path, FileRecord).
    """
    file_record = db.query(FileRecord).filter(FileRecord.id == file_id).first()
    if not file_record:
        raise AppException(
            status_code=404,
            message="Requested file record was not found.",
            error_code="FILE_NOT_FOUND",
        )

    # Authorization Check: verify requester has access to the conversation
    chat_service.verify_conversation_access(db, user_id, file_record.conversation_id)

    # Safe storage path verification
    file_path = get_safe_storage_path(file_record.stored_filename)
    if not file_path.is_file():
        logger.error(f"Missing file on disk: {file_path} for record ID {file_id}")
        raise AppException(
            status_code=404,
            message="File binary content is missing from server storage.",
            error_code="FILE_CONTENT_NOT_FOUND",
        )

    return file_path, file_record

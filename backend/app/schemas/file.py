from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict


def format_file_size(bytes_count: int) -> str:
    """Format byte count into human-readable representation."""
    if bytes_count < 1024:
        return f"{bytes_count} B"
    elif bytes_count < 1024 * 1024:
        return f"{(bytes_count / 1024):.1f} KB"
    elif bytes_count < 1024 * 1024 * 1024:
        return f"{(bytes_count / (1024 * 1024)):.1f} MB"
    return f"{(bytes_count / (1024 * 1024 * 1024)):.1f} GB"


class FileAttachmentInfo(BaseModel):
    id: int
    name: str
    size: str
    bytes: int
    type: str
    checksum: str
    download_url: str

    model_config = ConfigDict(from_attributes=True)


class FileRecordResponse(BaseModel):
    id: int
    conversation_id: Optional[str] = None
    message_id: Optional[int] = None
    uploader_id: Optional[int] = None
    original_name: str
    stored_filename: str
    file_size: int
    size_formatted: Optional[str] = None
    mime_type: str
    checksum_sha256: str
    download_url: Optional[str] = None
    created_at: datetime
    message: Optional[Any] = None

    model_config = ConfigDict(from_attributes=True)

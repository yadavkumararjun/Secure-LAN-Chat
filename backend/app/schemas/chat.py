from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator
from .file import FileAttachmentInfo


class MessageSenderInfo(BaseModel):
    id: int
    username: str
    display_name: Optional[str] = None
    avatar: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ChatMessageResponse(BaseModel):
    id: int
    conversation_id: str
    sender: Optional[MessageSenderInfo] = None
    content: str
    message_type: str = "text"
    client_msg_id: Optional[str] = None
    file: Optional[FileAttachmentInfo] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000, description="Message text content")
    client_msg_id: Optional[str] = Field(None, max_length=64, description="Unique client ID for deduplication and delivery ack")
    message_type: str = Field(default="text", max_length=20)

    @field_validator("content")
    @classmethod
    def validate_content_not_empty(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Message content cannot be empty.")
        if len(clean) > 2000:
            raise ValueError("Message exceeds maximum allowed length of 2000 characters.")
        return clean


class DirectConversationRequest(BaseModel):
    recipient_id: int = Field(..., description="Target user ID for 1-to-1 conversation")


class ConversationSummaryResponse(BaseModel):
    id: str
    type: str  # 'channel' or 'direct'
    name: Optional[str] = None
    username: Optional[str] = None
    subtitle: Optional[str] = None
    avatar: Optional[str] = None
    status: Optional[str] = "offline"
    ipAddress: Optional[str] = "192.168.1.xxx"
    encryptionStatus: Optional[str] = "Private LAN Session"
    last_message: Optional[ChatMessageResponse] = None
    peer: Optional[MessageSenderInfo] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedMessagesResponse(BaseModel):
    conversation_id: str
    total: int
    limit: int
    offset: int
    has_more: bool
    messages: List[ChatMessageResponse]


class WebSocketChatMessagePayload(BaseModel):
    conversation_id: str = Field(..., min_length=1, max_length=64)
    content: str = Field(..., min_length=1, max_length=2000)
    client_msg_id: Optional[str] = Field(None, max_length=64)
    message_type: str = Field(default="text", max_length=20)

    @field_validator("content")
    @classmethod
    def validate_content_not_empty(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Message content cannot be empty.")
        if len(clean) > 2000:
            raise ValueError("Message exceeds maximum allowed length of 2000 characters.")
        return clean


class WebSocketTypingPayload(BaseModel):
    conversation_id: str = Field(..., min_length=1, max_length=64)
    is_typing: bool = True

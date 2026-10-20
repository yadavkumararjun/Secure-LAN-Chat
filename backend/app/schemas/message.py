from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class MessageCreate(BaseModel):
    conversation_id: str
    content: str = Field(..., min_length=1)
    message_type: str = Field(default="text")


class MessageResponse(BaseModel):
    id: int
    conversation_id: str
    sender_id: Optional[int] = None
    content: str
    message_type: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

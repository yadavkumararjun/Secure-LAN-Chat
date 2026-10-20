from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class ConversationMemberResponse(BaseModel):
    id: int
    user_id: int
    role: str
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationResponse(BaseModel):
    id: str
    type: str
    name: Optional[str] = None
    created_at: datetime
    members: List[ConversationMemberResponse] = []

    model_config = ConfigDict(from_attributes=True)

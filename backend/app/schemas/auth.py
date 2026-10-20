import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class RegisterRequest(BaseModel):
    username: str = Field(
        ...,
        min_length=3,
        max_length=32,
        description="Unique alphanumeric username (3-32 chars)",
    )
    password: str = Field(
        ...,
        min_length=6,
        max_length=128,
        description="User password (min 6 chars)",
    )
    display_name: Optional[str] = Field(None, max_length=100)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not re.match(r"^[a-zA-Z0-9_]{3,32}$", cleaned):
            raise ValueError("Username must contain only letters, numbers, and underscores (3-32 chars).")
        return cleaned

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 6:
            raise ValueError("Password must be at least 6 characters long.")
        return value


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)

    @field_validator("username")
    @classmethod
    def clean_username(cls, value: str) -> str:
        return value.strip().lower()


class AuthUserResponse(BaseModel):
    id: int
    username: str
    display_name: Optional[str] = None
    avatar: Optional[str] = None
    is_active: bool
    created_at: datetime
    last_seen: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserWithPresence(BaseModel):
    id: int
    username: str
    display_name: Optional[str] = None
    avatar: Optional[str] = None
    is_online: bool
    last_seen: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    error: Optional[ErrorDetail] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DatabaseHealth(BaseModel):
    status: str
    dialect: Optional[str] = None
    file: Optional[str] = None
    tables: Optional[List[str]] = None
    error: Optional[str] = None


class StorageHealth(BaseModel):
    status: str
    upload_dir: str
    exists: bool
    is_writable: bool
    free_space_mb: Optional[float] = None


class HealthResponse(BaseModel):
    status: str = "healthy"
    app_name: str
    app_env: str
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    database: DatabaseHealth
    storage: StorageHealth

from datetime import datetime
from sqlalchemy import Column, DateTime


class TimestampMixin:
    """Standard created_at timestamp mixin."""
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

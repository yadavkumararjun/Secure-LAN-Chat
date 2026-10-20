from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base
from .base import TimestampMixin


class UserSession(Base, TimestampMixin):
    __tablename__ = "user_sessions"

    id = Column(String(64), primary_key=True, index=True)  # Cryptographic session token
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)

    # Relationship
    user = relationship("User", back_populates="sessions")

    def is_expired(self) -> bool:
        return datetime.utcnow() >= self.expires_at

    def __repr__(self):
        return f"<UserSession(id='{self.id[:8]}...', user_id={self.user_id}, expired={self.is_expired()})>"

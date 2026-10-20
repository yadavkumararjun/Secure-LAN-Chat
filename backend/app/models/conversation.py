import uuid
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from ..database import Base
from .base import TimestampMixin


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    type = Column(String(20), default="direct", nullable=False)  # 'broadcast', 'direct', 'group'
    name = Column(String(100), nullable=True)  # e.g. '#general-lan' for channels

    # Relationships
    members = relationship("ConversationMember", back_populates="conversation", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Conversation(id='{self.id}', type='{self.type}', name='{self.name}')>"


class ConversationMember(Base, TimestampMixin):
    __tablename__ = "conversation_members"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), default="member", nullable=False)  # 'admin', 'member'

    # Relationships
    conversation = relationship("Conversation", back_populates="members")
    user = relationship("User", back_populates="memberships")

    def __repr__(self):
        return f"<ConversationMember(conv='{self.conversation_id}', user_id={self.user_id}, role='{self.role}')>"

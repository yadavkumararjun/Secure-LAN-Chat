from sqlalchemy import Column, Integer, String, BigInteger, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base
from .base import TimestampMixin


class FileRecord(Base, TimestampMixin):
    __tablename__ = "file_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="SET NULL"), nullable=True, index=True)
    uploader_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    original_name = Column(String(255), nullable=False)
    stored_filename = Column(String(255), unique=True, nullable=False)  # Isolated UUID name on disk
    file_size = Column(BigInteger, nullable=False)  # Size in bytes
    mime_type = Column(String(100), default="application/octet-stream", nullable=False)
    checksum_sha256 = Column(String(64), nullable=False)

    # Relationships
    message = relationship("Message", back_populates="file_record")
    uploader = relationship("User", back_populates="uploaded_files")

    def __repr__(self):
        return f"<FileRecord(id={self.id}, name='{self.original_name}', size={self.file_size})>"

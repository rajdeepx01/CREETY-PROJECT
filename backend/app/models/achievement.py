import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, Text, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database import Base

def utcnow():
    return datetime.now(timezone.utc)

class Achievement(Base):
    __tablename__ = "achievements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Details
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True, default="Certificate")
    # Categories: Certificate, Award, Badge, Project Completion, License, Hackathon, Publication, Degree
    
    issuer: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    issue_date: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    expiration_date: Mapped[str | None] = mapped_column(String(20), nullable=True, default="")
    
    # Credential Verification
    credential_id: Mapped[str | None] = mapped_column(String(100), nullable=True, default="")
    credential_url: Mapped[str | None] = mapped_column(String(500), nullable=True, default="")
    
    # Media / File attachments
    media_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    media_type: Mapped[str | None] = mapped_column(String(50), nullable=True) # e.g. "application/pdf", "image/png"
    media_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    media_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    
    # Privacy & Highlighting
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # JSON list of tags/skills e.g. ["Python", "Machine Learning", "Cloud"]
    tags_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    
    # Custom metadata or score / grade
    score_or_grade: Mapped[str | None] = mapped_column(String(50), nullable=True, default="")
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    user = relationship("User", back_populates="achievements")

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

class AchievementBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field("", max_length=5000)
    category: str = Field(..., max_length=50) # Certificate, Award, Badge, Project Completion, License, Hackathon, Publication, Degree
    issuer: str = Field(..., min_length=1, max_length=150)
    issue_date: str = Field(..., max_length=20) # YYYY-MM-DD or Month YYYY
    expiration_date: Optional[str] = Field(None, max_length=20)
    credential_id: Optional[str] = Field(None, max_length=100)
    credential_url: Optional[str] = Field(None, max_length=500)
    is_public: bool = True
    is_featured: bool = False
    tags: List[str] = Field(default_factory=list)
    score_or_grade: Optional[str] = Field(None, max_length=50)

class AchievementCreate(AchievementBase):
    pass

class AchievementUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    category: Optional[str] = Field(None, max_length=50)
    issuer: Optional[str] = Field(None, min_length=1, max_length=150)
    issue_date: Optional[str] = Field(None, max_length=20)
    expiration_date: Optional[str] = Field(None, max_length=20)
    credential_id: Optional[str] = Field(None, max_length=100)
    credential_url: Optional[str] = Field(None, max_length=500)
    is_public: Optional[bool] = None
    is_featured: Optional[bool] = None
    tags: Optional[List[str]] = None
    score_or_grade: Optional[str] = Field(None, max_length=50)

class AchievementResponse(BaseModel):
    id: str
    user_id: str
    title: str
    description: str
    category: str
    issuer: str
    issue_date: str
    expiration_date: Optional[str] = None
    credential_id: Optional[str] = None
    credential_url: Optional[str] = None
    media_path: Optional[str] = None
    media_type: Optional[str] = None
    media_filename: Optional[str] = None
    media_size_bytes: Optional[int] = 0
    has_media: bool = False
    media_url: Optional[str] = None
    is_public: bool
    is_featured: bool
    tags: List[str]
    score_or_grade: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AchievementListResponse(BaseModel):
    items: List[AchievementResponse]
    total: int
    categories: List[str]
    all_tags: List[str]
    stats: dict

class AchievementVisibilityToggle(BaseModel):
    is_public: bool

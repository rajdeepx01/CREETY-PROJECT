from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

class UserSummary(BaseModel):
    id: str
    email: EmailStr
    username: str
    full_name: str
    headline: Optional[str] = ""
    avatar_url: Optional[str] = ""
    is_verified: bool
    is_profile_public: bool
    is_2fa_enabled: bool

    class Config:
        from_attributes = True

class UserProfileResponse(BaseModel):
    id: str
    email: EmailStr
    username: str
    full_name: str
    headline: Optional[str] = ""
    bio: Optional[str] = ""
    avatar_url: Optional[str] = ""
    is_verified: bool
    is_profile_public: bool
    is_2fa_enabled: bool
    website_url: Optional[str] = ""
    github_url: Optional[str] = ""
    linkedin_url: Optional[str] = ""
    twitter_url: Optional[str] = ""
    created_at: datetime
    updated_at: datetime
    achievements_count: Optional[int] = 0
    public_achievements_count: Optional[int] = 0

    class Config:
        from_attributes = True

class UserProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    headline: Optional[str] = Field(None, max_length=255)
    bio: Optional[str] = Field(None, max_length=2000)
    avatar_url: Optional[str] = Field(None, max_length=500)
    is_profile_public: Optional[bool] = None
    website_url: Optional[str] = Field(None, max_length=255)
    github_url: Optional[str] = Field(None, max_length=255)
    linkedin_url: Optional[str] = Field(None, max_length=255)
    twitter_url: Optional[str] = Field(None, max_length=255)

class PublicUserProfileResponse(BaseModel):
    id: str
    username: str
    full_name: str
    headline: Optional[str] = ""
    bio: Optional[str] = ""
    avatar_url: Optional[str] = ""
    is_verified: bool
    website_url: Optional[str] = ""
    github_url: Optional[str] = ""
    linkedin_url: Optional[str] = ""
    twitter_url: Optional[str] = ""
    created_at: datetime
    public_achievements_count: int
    categories: List[str]
    skills_tags: List[str]

    class Config:
        from_attributes = True

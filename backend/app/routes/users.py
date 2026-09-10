import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.models.achievement import Achievement
from backend.app.schemas.user import (
    UserProfileResponse,
    UserProfileUpdateRequest,
    PublicUserProfileResponse,
)
from backend.app.schemas.achievement import AchievementResponse
from backend.app.security.deps import get_current_user, get_optional_current_user
from backend.app.security.sanitization import sanitize_plain_text

router = APIRouter(prefix="/api/users", tags=["Users"])

@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve currently authenticated user's private profile details and statistics."""
    # Count total achievements
    total_res = await db.execute(
        select(func.count(Achievement.id)).where(Achievement.user_id == current_user.id)
    )
    total_count = total_res.scalar() or 0
    
    # Count public achievements
    pub_res = await db.execute(
        select(func.count(Achievement.id)).where(
            Achievement.user_id == current_user.id,
            Achievement.is_public == True
        )
    )
    public_count = pub_res.scalar() or 0
    
    profile_data = UserProfileResponse.model_validate(current_user)
    profile_data.achievements_count = total_count
    profile_data.public_achievements_count = public_count
    return profile_data

@router.put("/me", response_model=UserProfileResponse)
async def update_my_profile(
    payload: UserProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update profile fields such as headline, bio, avatar, and public/private visibility toggle."""
    if payload.full_name is not None:
        current_user.full_name = sanitize_plain_text(payload.full_name)
    if payload.headline is not None:
        current_user.headline = sanitize_plain_text(payload.headline)
    if payload.bio is not None:
        current_user.bio = sanitize_plain_text(payload.bio)
    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url.strip()
    if payload.is_profile_public is not None:
        current_user.is_profile_public = payload.is_profile_public
    if payload.website_url is not None:
        current_user.website_url = payload.website_url.strip()
    if payload.github_url is not None:
        current_user.github_url = payload.github_url.strip()
    if payload.linkedin_url is not None:
        current_user.linkedin_url = payload.linkedin_url.strip()
    if payload.twitter_url is not None:
        current_user.twitter_url = payload.twitter_url.strip()
        
    await db.commit()
    await db.refresh(current_user)
    
    total_res = await db.execute(
        select(func.count(Achievement.id)).where(Achievement.user_id == current_user.id)
    )
    total_count = total_res.scalar() or 0
    
    pub_res = await db.execute(
        select(func.count(Achievement.id)).where(
            Achievement.user_id == current_user.id,
            Achievement.is_public == True
        )
    )
    public_count = pub_res.scalar() or 0
    
    profile_data = UserProfileResponse.model_validate(current_user)
    profile_data.achievements_count = total_count
    profile_data.public_achievements_count = public_count
    return profile_data

@router.get("/public/{username}")
async def get_public_profile(
    username: str,
    db: AsyncSession = Depends(get_db),
    optional_user: User | None = Depends(get_optional_current_user)
):
    """Retrieve public portfolio details for a specific user and their public achievements."""
    clean_username = username.strip().lower()
    user_res = await db.execute(select(User).where(User.username == clean_username))
    target_user = user_res.scalar_one_or_none()
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{username}' was not found."
        )
    
    is_owner = optional_user is not None and optional_user.id == target_user.id
    
    # If profile is private and visitor is not the owner
    if not target_user.is_profile_public and not is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This user's portfolio profile is private."
        )
    
    # Query public achievements (or all if owner is viewing their own public preview)
    ach_query = select(Achievement).where(Achievement.user_id == target_user.id)
    if not is_owner:
        ach_query = ach_query.where(Achievement.is_public == True)
    ach_query = ach_query.order_by(Achievement.is_featured.desc(), Achievement.issue_date.desc())
    
    ach_res = await db.execute(ach_query)
    achievements = ach_res.scalars().all()
    
    # Aggregate tags and categories
    categories = list(set(a.category for a in achievements if a.category))
    skills_set = set()
    formatted_items = []
    
    for a in achievements:
        tags = []
        try:
            tags = json.loads(a.tags_json) if a.tags_json else []
        except Exception:
            tags = []
        for t in tags:
            skills_set.add(t)
            
        formatted_items.append({
            "id": a.id,
            "user_id": a.user_id,
            "title": a.title,
            "description": a.description,
            "category": a.category,
            "issuer": a.issuer,
            "issue_date": a.issue_date,
            "expiration_date": a.expiration_date,
            "credential_id": a.credential_id,
            "credential_url": a.credential_url,
            "media_type": a.media_type,
            "media_filename": a.media_filename,
            "media_size_bytes": a.media_size_bytes,
            "has_media": bool(a.media_path),
            "media_url": f"/api/achievements/media/{a.id}" if a.media_path else None,
            "is_public": a.is_public,
            "is_featured": a.is_featured,
            "tags": tags,
            "score_or_grade": a.score_or_grade,
            "created_at": a.created_at,
            "updated_at": a.updated_at
        })
        
    return {
        "user": {
            "id": target_user.id,
            "username": target_user.username,
            "full_name": target_user.full_name,
            "headline": target_user.headline,
            "bio": target_user.bio,
            "avatar_url": target_user.avatar_url,
            "is_verified": target_user.is_verified,
            "is_profile_public": target_user.is_profile_public,
            "website_url": target_user.website_url,
            "github_url": target_user.github_url,
            "linkedin_url": target_user.linkedin_url,
            "twitter_url": target_user.twitter_url,
            "created_at": target_user.created_at,
            "public_achievements_count": len(formatted_items),
            "categories": sorted(categories),
            "skills_tags": sorted(list(skills_set))
        },
        "achievements": formatted_items,
        "is_owner": is_owner
    }

import os
import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func, and_

from backend.app.config import settings, UPLOAD_DIR
from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.models.achievement import Achievement
from backend.app.schemas.achievement import (
    AchievementResponse,
    AchievementListResponse,
    AchievementVisibilityToggle,
)
from backend.app.security.deps import get_current_user, get_optional_current_user
from backend.app.security.rate_limiter import rate_limit
from backend.app.security.sanitization import sanitize_plain_text, sanitize_text
from backend.app.services.file_service import save_uploaded_file, delete_stored_file

router = APIRouter(prefix="/api/achievements", tags=["Achievements"])

def format_achievement_response(a: Achievement) -> AchievementResponse:
    tags = []
    try:
        tags = json.loads(a.tags_json) if a.tags_json else []
    except Exception:
        tags = []
    
    return AchievementResponse(
        id=a.id,
        user_id=a.user_id,
        title=a.title,
        description=a.description,
        category=a.category,
        issuer=a.issuer,
        issue_date=a.issue_date,
        expiration_date=a.expiration_date,
        credential_id=a.credential_id,
        credential_url=a.credential_url,
        media_path=a.media_path,
        media_type=a.media_type,
        media_filename=a.media_filename,
        media_size_bytes=a.media_size_bytes or 0,
        has_media=bool(a.media_path),
        media_url=f"/api/achievements/media/{a.id}" if a.media_path else None,
        is_public=a.is_public,
        is_featured=a.is_featured,
        tags=tags,
        score_or_grade=a.score_or_grade,
        created_at=a.created_at,
        updated_at=a.updated_at
    )

@router.get("", response_model=AchievementListResponse)
async def list_my_achievements(
    q: Optional[str] = Query(None, description="Search keyword in title, issuer, or description"),
    category: Optional[str] = Query(None, description="Filter by category"),
    tag: Optional[str] = Query(None, description="Filter by skill/tag"),
    visibility: Optional[str] = Query(None, description="all, public, or private"),
    sort_by: Optional[str] = Query("date_desc", description="date_desc, date_asc, title_asc, recent"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List authenticated user's achievements with filtering, searching, and statistics."""
    query = select(Achievement).where(Achievement.user_id == current_user.id)
    
    if q:
        search_pattern = f"%{q.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(Achievement.title).like(search_pattern),
                func.lower(Achievement.issuer).like(search_pattern),
                func.lower(Achievement.description).like(search_pattern),
                func.lower(Achievement.tags_json).like(search_pattern)
            )
        )
        
    if category and category.lower() != "all":
        query = query.where(Achievement.category == category)
        
    if tag:
        tag_pattern = f"%\"{tag.strip()}\"%"
        query = query.where(Achievement.tags_json.like(tag_pattern))
        
    if visibility:
        if visibility.lower() == "public":
            query = query.where(Achievement.is_public == True)
        elif visibility.lower() == "private":
            query = query.where(Achievement.is_public == False)
            
    # Sorting
    if sort_by == "date_asc":
        query = query.order_by(Achievement.issue_date.asc())
    elif sort_by == "title_asc":
        query = query.order_by(Achievement.title.asc())
    elif sort_by == "recent":
        query = query.order_by(Achievement.created_at.desc())
    else: # date_desc
        query = query.order_by(Achievement.is_featured.desc(), Achievement.issue_date.desc(), Achievement.created_at.desc())
        
    result = await db.execute(query)
    achievements = result.scalars().all()
    
    # Compute all categories and tags for the user
    all_res = await db.execute(select(Achievement).where(Achievement.user_id == current_user.id))
    all_user_items = all_res.scalars().all()
    
    categories_set = set()
    all_tags_set = set()
    total_public = 0
    total_private = 0
    
    for item in all_user_items:
        if item.category:
            categories_set.add(item.category)
        if item.is_public:
            total_public += 1
        else:
            total_private += 1
        try:
            tags = json.loads(item.tags_json) if item.tags_json else []
            for t in tags:
                all_tags_set.add(t)
        except Exception:
            pass
            
    items_formatted = [format_achievement_response(a) for a in achievements]
    
    return AchievementListResponse(
        items=items_formatted,
        total=len(items_formatted),
        categories=sorted(list(categories_set)),
        all_tags=sorted(list(all_tags_set)),
        stats={
            "total": len(all_user_items),
            "public": total_public,
            "private": total_private,
            "categories_count": len(categories_set),
            "featured": sum(1 for x in all_user_items if x.is_featured)
        }
    )

@router.post("", response_model=AchievementResponse, dependencies=[Depends(rate_limit(max_requests=20, window_seconds=60))])
async def create_achievement(
    title: str = Form(...),
    description: Optional[str] = Form(""),
    category: str = Form("Certificate"),
    issuer: str = Form(...),
    issue_date: str = Form(...),
    expiration_date: Optional[str] = Form(None),
    credential_id: Optional[str] = Form(None),
    credential_url: Optional[str] = Form(None),
    is_public: bool = Form(True),
    is_featured: bool = Form(False),
    tags: Optional[str] = Form("[]"), # JSON array string or comma separated
    score_or_grade: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new achievement record with optional certificate/badge file upload."""
    # Process tags
    clean_tags = []
    if tags:
        try:
            parsed = json.loads(tags)
            if isinstance(parsed, list):
                clean_tags = [sanitize_plain_text(str(t)) for t in parsed if str(t).strip()]
        except Exception:
            # Fallback for comma-separated string
            clean_tags = [sanitize_plain_text(t.strip()) for t in tags.split(",") if t.strip()]
            
    # Process file upload if provided
    media_path = None
    media_type = None
    media_filename = None
    media_size = 0
    
    if file and file.filename:
        upload_data = await save_uploaded_file(file)
        media_path = upload_data["relative_path"]
        media_type = upload_data["media_type"]
        media_filename = upload_data["original_filename"]
        media_size = upload_data["size_bytes"]
        
    achievement = Achievement(
        user_id=current_user.id,
        title=sanitize_plain_text(title),
        description=sanitize_text(description),
        category=sanitize_plain_text(category) or "Certificate",
        issuer=sanitize_plain_text(issuer),
        issue_date=sanitize_plain_text(issue_date),
        expiration_date=sanitize_plain_text(expiration_date) if expiration_date else None,
        credential_id=sanitize_plain_text(credential_id) if credential_id else None,
        credential_url=credential_url.strip() if credential_url else None,
        is_public=is_public,
        is_featured=is_featured,
        tags_json=json.dumps(clean_tags),
        score_or_grade=sanitize_plain_text(score_or_grade) if score_or_grade else None,
        media_path=media_path,
        media_type=media_type,
        media_filename=media_filename,
        media_size_bytes=media_size
    )
    
    db.add(achievement)
    await db.commit()
    await db.refresh(achievement)
    
    return format_achievement_response(achievement)

@router.get("/{achievement_id}", response_model=AchievementResponse)
async def get_achievement(
    achievement_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve single achievement details owned by current user."""
    res = await db.execute(select(Achievement).where(Achievement.id == achievement_id))
    achievement = res.scalar_one_or_none()
    
    if not achievement:
        raise HTTPException(status_code=404, detail="Achievement not found.")
        
    if achievement.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have permission to access this achievement.")
        
    return format_achievement_response(achievement)

@router.put("/{achievement_id}", response_model=AchievementResponse)
async def update_achievement(
    achievement_id: str,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    issuer: Optional[str] = Form(None),
    issue_date: Optional[str] = Form(None),
    expiration_date: Optional[str] = Form(None),
    credential_id: Optional[str] = Form(None),
    credential_url: Optional[str] = Form(None),
    is_public: Optional[bool] = Form(None),
    is_featured: Optional[bool] = Form(None),
    tags: Optional[str] = Form(None),
    score_or_grade: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    remove_file: Optional[bool] = Form(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update achievement fields and optionally replace/remove attached credential media."""
    res = await db.execute(select(Achievement).where(Achievement.id == achievement_id))
    achievement = res.scalar_one_or_none()
    
    if not achievement:
        raise HTTPException(status_code=404, detail="Achievement not found.")
        
    if achievement.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not authorized to modify this achievement.")
        
    if title is not None:
        achievement.title = sanitize_plain_text(title)
    if description is not None:
        achievement.description = sanitize_text(description)
    if category is not None:
        achievement.category = sanitize_plain_text(category)
    if issuer is not None:
        achievement.issuer = sanitize_plain_text(issuer)
    if issue_date is not None:
        achievement.issue_date = sanitize_plain_text(issue_date)
    if expiration_date is not None:
        achievement.expiration_date = sanitize_plain_text(expiration_date)
    if credential_id is not None:
        achievement.credential_id = sanitize_plain_text(credential_id)
    if credential_url is not None:
        achievement.credential_url = credential_url.strip()
    if is_public is not None:
        achievement.is_public = is_public
    if is_featured is not None:
        achievement.is_featured = is_featured
    if score_or_grade is not None:
        achievement.score_or_grade = sanitize_plain_text(score_or_grade)
        
    if tags is not None:
        clean_tags = []
        try:
            parsed = json.loads(tags)
            if isinstance(parsed, list):
                clean_tags = [sanitize_plain_text(str(t)) for t in parsed if str(t).strip()]
        except Exception:
            clean_tags = [sanitize_plain_text(t.strip()) for t in tags.split(",") if t.strip()]
        achievement.tags_json = json.dumps(clean_tags)
        
    if remove_file and achievement.media_path:
        delete_stored_file(achievement.media_path)
        achievement.media_path = None
        achievement.media_type = None
        achievement.media_filename = None
        achievement.media_size_bytes = 0
        
    if file and file.filename:
        # Delete old media file if existing
        if achievement.media_path:
            delete_stored_file(achievement.media_path)
        upload_data = await save_uploaded_file(file)
        achievement.media_path = upload_data["relative_path"]
        achievement.media_type = upload_data["media_type"]
        achievement.media_filename = upload_data["original_filename"]
        achievement.media_size_bytes = upload_data["size_bytes"]
        
    await db.commit()
    await db.refresh(achievement)
    return format_achievement_response(achievement)

@router.delete("/{achievement_id}")
async def delete_achievement(
    achievement_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an achievement and remove its associated files from disk."""
    res = await db.execute(select(Achievement).where(Achievement.id == achievement_id))
    achievement = res.scalar_one_or_none()
    
    if not achievement:
        raise HTTPException(status_code=404, detail="Achievement not found.")
        
    if achievement.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have permission to delete this achievement.")
        
    if achievement.media_path:
        delete_stored_file(achievement.media_path)
        
    await db.delete(achievement)
    await db.commit()
    return {"message": "Achievement deleted successfully."}

@router.patch("/{achievement_id}/visibility", response_model=AchievementResponse)
async def toggle_achievement_visibility(
    achievement_id: str,
    payload: AchievementVisibilityToggle,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Quickly toggle an achievement between public and private visibility."""
    res = await db.execute(select(Achievement).where(Achievement.id == achievement_id))
    achievement = res.scalar_one_or_none()
    
    if not achievement:
        raise HTTPException(status_code=404, detail="Achievement not found.")
        
    if achievement.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized.")
        
    achievement.is_public = payload.is_public
    await db.commit()
    await db.refresh(achievement)
    return format_achievement_response(achievement)

@router.patch("/{achievement_id}/feature", response_model=AchievementResponse)
async def toggle_achievement_featured(
    achievement_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Toggle pin/featured highlight status of an achievement."""
    res = await db.execute(select(Achievement).where(Achievement.id == achievement_id))
    achievement = res.scalar_one_or_none()
    
    if not achievement:
        raise HTTPException(status_code=404, detail="Achievement not found.")
        
    if achievement.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized.")
        
    achievement.is_featured = not achievement.is_featured
    await db.commit()
    await db.refresh(achievement)
    return format_achievement_response(achievement)

@router.get("/media/{achievement_id}")
async def get_achievement_media(
    achievement_id: str,
    db: AsyncSession = Depends(get_db),
    optional_user: User | None = Depends(get_optional_current_user)
):
    """Stream or download the attached certificate/badge media with permission checks."""
    res = await db.execute(select(Achievement).where(Achievement.id == achievement_id))
    achievement = res.scalar_one_or_none()
    
    if not achievement or not achievement.media_path:
        raise HTTPException(status_code=404, detail="No media file attached to this achievement.")
        
    # Check permissions: owner can always view; guest can view only if achievement and profile are public
    is_owner = optional_user is not None and optional_user.id == achievement.user_id
    if not is_owner:
        if not achievement.is_public:
            raise HTTPException(status_code=403, detail="This file is private.")
            
        # Check if owner profile is public
        owner_res = await db.execute(select(User).where(User.id == achievement.user_id))
        owner = owner_res.scalar_one_or_none()
        if not owner or not owner.is_profile_public:
            raise HTTPException(status_code=403, detail="This user's profile is private.")
            
    filename = os.path.basename(achievement.media_path)
    file_path = UPLOAD_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Attached media file was not found on disk.")
        
    media_type = achievement.media_type or "application/octet-stream"
    headers = {
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "public, max-age=3600",
    }
    
    # Inline viewing for images & PDFs
    content_disposition = f'inline; filename="{achievement.media_filename or filename}"'
    headers["Content-Disposition"] = content_disposition
    
    return FileResponse(
        path=file_path,
        media_type=media_type,
        headers=headers
    )

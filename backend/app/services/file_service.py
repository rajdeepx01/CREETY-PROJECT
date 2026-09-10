import os
import uuid
import io
from pathlib import Path
from fastapi import UploadFile, HTTPException, status
from PIL import Image
from backend.app.config import settings, UPLOAD_DIR
from backend.app.security.sanitization import sanitize_filename

# Magic signatures
MAGIC_SIGNATURES = {
    "pdf": [b"%PDF-"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "jpeg": [b"\xff\xd8\xff"],
    "webp": [b"RIFF"] # plus WEBP at offset 8
}

def validate_magic_bytes(content: bytes, ext: str) -> bool:
    """Verify that file header bytes match the expected format signature."""
    if len(content) < 12:
        return False
    
    ext_clean = ext.lower().replace(".", "")
    if ext_clean == "jpg":
        ext_clean = "jpeg"
        
    if ext_clean == "pdf":
        return content.startswith(b"%PDF-")
    
    if ext_clean == "png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    
    if ext_clean == "jpeg":
        return content.startswith(b"\xff\xd8\xff")
    
    if ext_clean == "webp":
        return content.startswith(b"RIFF") and content[8:12] == b"WEBP"
    
    return False

def validate_image_integrity(content: bytes):
    """Attempt to parse image with Pillow to ensure it is not corrupt or malformed."""
    try:
        with Image.open(io.BytesIO(content)) as img:
            img.verify()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Uploaded image is corrupt or invalid: {str(e)}"
        )

async def save_uploaded_file(file: UploadFile) -> dict:
    """
    Perform multi-step validation and store file safely:
    1. Check filename & extension
    2. Read & check size limit
    3. Validate binary magic bytes signature
    4. Validate image parsing if image
    5. Save with randomized UUID in secure upload directory
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided in upload."
        )
    
    original_filename = sanitize_filename(file.filename)
    _, ext = os.path.splitext(original_filename.lower())
    
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )
    
    # Read content
    content = await file.read()
    size_bytes = len(content)
    
    if size_bytes > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_BYTES // (1024*1024)}MB."
        )
    
    if size_bytes == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty."
        )
    
    # Check Magic Bytes
    if not validate_magic_bytes(content, ext):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content does not match its claimed file extension. Upload rejected."
        )
    
    # Verify image integrity if applicable
    if ext in {".png", ".jpg", ".jpeg", ".webp"}:
        validate_image_integrity(content)
    
    # Generate unique UUID filename
    unique_name = f"{uuid.uuid4().hex}{ext}"
    dest_path = UPLOAD_DIR / unique_name
    
    with open(dest_path, "wb") as f:
        f.write(content)
    
    # Determine MIME type
    mime_map = {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp"
    }
    media_type = mime_map.get(ext, file.content_type or "application/octet-stream")
    
    return {
        "saved_filename": unique_name,
        "relative_path": f"uploads/{unique_name}",
        "original_filename": original_filename,
        "media_type": media_type,
        "size_bytes": size_bytes
    }

def delete_stored_file(relative_path: str | None):
    """Delete a stored file safely from uploads vault."""
    if not relative_path:
        return
    try:
        filename = os.path.basename(relative_path)
        target = UPLOAD_DIR / filename
        if target.exists() and target.is_file():
            target.unlink()
    except Exception:
        pass

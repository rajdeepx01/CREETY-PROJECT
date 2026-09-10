import re
import html
import bleach

# Allowed tags if rich text is ever needed, otherwise empty for pure safe text
ALLOWED_TAGS = ['b', 'i', 'u', 'em', 'strong', 'p', 'br', 'ul', 'ol', 'li', 'a', 'code', 'pre']
ALLOWED_ATTRIBUTES = {'a': ['href', 'title', 'target', 'rel']}

def sanitize_text(text: str | None) -> str:
    """Sanitize general text to strip dangerous scripts and inject entities safely."""
    if not text:
        return ""
    # Clean with bleach
    cleaned = bleach.clean(
        text,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True
    )
    return cleaned.strip()

def sanitize_plain_text(text: str | None) -> str:
    """Strip all HTML tags and escape dangerous characters for plain text fields."""
    if not text:
        return ""
    # Strip all tags
    cleaned = bleach.clean(text, tags=[], strip=True)
    # Convert special entities safely
    return html.escape(cleaned).strip()

def sanitize_filename(filename: str) -> str:
    """Sanitize uploaded filenames to prevent directory traversal and special chars."""
    if not filename:
        return "file"
    # Remove directory separators and null bytes
    filename = filename.replace("\\", "/").split("/")[-1]
    # Replace non-alphanumeric with underscore, keep extension dot
    cleaned = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
    # Avoid leading dots or empty
    cleaned = re.sub(r'^\.+', '', cleaned)
    return cleaned[:100] or "file"

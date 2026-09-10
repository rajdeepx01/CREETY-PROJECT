import secrets
from datetime import datetime, timezone
from backend.app.config import settings

# Live in-memory sandbox mailbox for instant local verification testing
mailbox_log: list[dict] = []

def generate_verification_token() -> str:
    """Generate a high-entropy URL-safe verification token."""
    return secrets.token_urlsafe(32)

async def send_verification_email(to_email: str, username: str, token: str, app_url: str = "http://127.0.0.1:8000"):
    """Send verification email via SMTP or store in dev mailbox sandbox."""
    verify_link = f"{app_url}/?verify_token={token}#verify"
    
    email_entry = {
        "id": secrets.token_hex(4),
        "to": to_email,
        "username": username,
        "token": token,
        "verify_link": verify_link,
        "subject": "Verify your Credence Showcase Account",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "body_text": f"Hi {username},\n\nPlease verify your email for Credence by clicking:\n{verify_link}\n\nToken: {token}"
    }
    
    # Store in memory sandbox
    mailbox_log.insert(0, email_entry)
    if len(mailbox_log) > 50:
        mailbox_log.pop()
        
    # If real SMTP is configured
    if settings.SMTP_ENABLED and settings.SMTP_USER and settings.SMTP_PASSWORD:
        try:
            import aiosmtplib
            from email.message import EmailMessage
            
            msg = EmailMessage()
            msg["Subject"] = email_entry["subject"]
            msg["From"] = settings.EMAIL_FROM
            msg["To"] = to_email
            msg.set_content(email_entry["body_text"])
            
            await aiosmtplib.send(
                msg,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                use_tls=(settings.SMTP_PORT == 465),
                start_tls=(settings.SMTP_PORT == 587),
            )
        except Exception as e:
            print(f"SMTP send notice: {e}. Saved in Dev Sandbox Mailbox instead.")

def get_recent_emails() -> list[dict]:
    """Retrieve recent sandbox emails for interactive testing."""
    return mailbox_log[:20]

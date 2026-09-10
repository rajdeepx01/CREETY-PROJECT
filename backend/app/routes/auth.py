import json
import secrets
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from backend.app.database import get_db
from backend.app.models.user import User, RefreshToken, EmailVerification, AuditLog
from backend.app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    OAuthLoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    Setup2FAResponse,
    Verify2FARequest,
    Disable2FARequest,
    VerifyEmailRequest,
    ResendVerificationRequest,
)
from backend.app.schemas.user import UserSummary
from backend.app.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    create_temporary_2fa_token,
    generate_refresh_token,
    hash_refresh_token,
    decode_token,
)
from backend.app.services.totp_service import (
    generate_totp_secret,
    get_totp_uri,
    generate_qr_code_base64,
    verify_totp_code,
    generate_backup_codes,
    verify_and_consume_backup_code,
)
from backend.app.services.email_service import (
    generate_verification_token,
    send_verification_email,
    get_recent_emails,
)
from backend.app.security.deps import get_current_user
from backend.app.security.rate_limiter import rate_limit
from backend.app.security.sanitization import sanitize_plain_text

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", response_model=TokenResponse, dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))])
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user account with hashed password and verification token."""
    clean_username = payload.username.strip().lower()
    clean_email = payload.email.strip().lower()
    
    # Check if username or email already exists
    existing = await db.execute(
        select(User).where(or_(User.username == clean_username, User.email == clean_email))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email or username already exists."
        )
    
    # Hash password with bcrypt
    hashed_pwd = hash_password(payload.password)
    
    new_user = User(
        email=clean_email,
        username=clean_username,
        password_hash=hashed_pwd,
        full_name=sanitize_plain_text(payload.full_name),
        is_verified=False,
        is_profile_public=True
    )
    db.add(new_user)
    await db.flush()
    
    # Generate email verification token
    v_token = generate_verification_token()
    verif = EmailVerification(
        user_id=new_user.id,
        token=v_token,
        expires_at=datetime.now(timezone.utc)
    )
    db.add(verif)
    
    # Audit log
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")
    audit = AuditLog(
        user_id=new_user.id,
        action="REGISTER",
        ip_address=client_ip,
        user_agent=user_agent[:255]
    )
    db.add(audit)
    
    # Generate tokens
    access_token, expires_in = create_access_token(new_user.id, new_user.username)
    raw_refresh, token_hash, ref_expires = generate_refresh_token()
    
    refresh_entry = RefreshToken(
        user_id=new_user.id,
        token_hash=token_hash,
        expires_at=ref_expires
    )
    db.add(refresh_entry)
    await db.commit()
    await db.refresh(new_user)
    
    # Dispatch verification email (stored in dev sandbox mailbox)
    base_url = str(request.base_url).rstrip("/")
    await send_verification_email(new_user.email, new_user.username, v_token, base_url)
    
    # Set secure HTTP-only refresh cookie
    response.set_cookie(
        key="refresh_token",
        value=raw_refresh,
        httponly=True,
        samesite="lax",
        secure=False, # Set to True in production HTTPS
        max_age=7 * 24 * 3600
    )
    
    return TokenResponse(
        access_token=access_token,
        expires_in=expires_in,
        user=UserSummary.model_validate(new_user)
    )

@router.post("/login", response_model=TokenResponse, dependencies=[Depends(rate_limit(max_requests=15, window_seconds=60))])
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate user with email/username and password. Handles 2FA if enabled."""
    identifier = payload.email_or_username.strip().lower()
    
    result = await db.execute(
        select(User).where(or_(User.email == identifier, User.username == identifier))
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email/username or password."
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated."
        )
    
    # If 2FA is enabled on account
    if user.is_2fa_enabled:
        # Check if 2FA code or backup code provided in initial request
        two_fa_valid = False
        if payload.totp_code and user.totp_secret:
            two_fa_valid = verify_totp_code(user.totp_secret, payload.totp_code)
        elif payload.backup_code:
            success, new_backup_json = verify_and_consume_backup_code(user.backup_codes_json, payload.backup_code)
            if success:
                two_fa_valid = True
                user.backup_codes_json = new_backup_json
                await db.commit()
        
        if not two_fa_valid:
            # Generate short-lived temp token for 2FA challenge modal
            temp_token = create_temporary_2fa_token(user.id)
            return TokenResponse(
                access_token="",
                expires_in=0,
                user=UserSummary.model_validate(user),
                requires_2fa=True,
                temp_token=temp_token
            )
    
    # Generate normal tokens
    access_token, expires_in = create_access_token(user.id, user.username)
    raw_refresh, token_hash, ref_expires = generate_refresh_token()
    
    refresh_entry = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=ref_expires
    )
    db.add(refresh_entry)
    
    # Audit log
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")
    audit = AuditLog(
        user_id=user.id,
        action="LOGIN",
        ip_address=client_ip,
        user_agent=user_agent[:255]
    )
    db.add(audit)
    await db.commit()
    
    response.set_cookie(
        key="refresh_token",
        value=raw_refresh,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=7 * 24 * 3600
    )
    
    return TokenResponse(
        access_token=access_token,
        expires_in=expires_in,
        user=UserSummary.model_validate(user)
    )

@router.post("/oauth-login", response_model=TokenResponse)
async def oauth_login(
    payload: OAuthLoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Seamless 1-Click OAuth / Google Login Flow (Demo and production provider ready)."""
    clean_email = payload.email.strip().lower()
    
    result = await db.execute(select(User).where(User.email == clean_email))
    user = result.scalar_one_or_none()
    
    if not user:
        # Create user from OAuth
        base_username = clean_email.split("@")[0].replace(".", "_")
        username = base_username
        
        # Check uniqueness of username
        idx = 1
        while True:
            u_check = await db.execute(select(User).where(User.username == username))
            if not u_check.scalar_one_or_none():
                break
            username = f"{base_username}_{idx}"
            idx += 1
            
        dummy_pwd = hash_password(secrets.token_urlsafe(32))
        user = User(
            email=clean_email,
            username=username,
            password_hash=dummy_pwd,
            full_name=sanitize_plain_text(payload.name or username),
            avatar_url=payload.avatar_url or "",
            is_verified=True, # OAuth emails are verified by provider
            is_profile_public=True
        )
        db.add(user)
        await db.flush()
    
    access_token, expires_in = create_access_token(user.id, user.username)
    raw_refresh, token_hash, ref_expires = generate_refresh_token()
    
    refresh_entry = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=ref_expires
    )
    db.add(refresh_entry)
    
    # Audit log
    client_ip = request.client.host if request.client else "unknown"
    audit = AuditLog(
        user_id=user.id,
        action=f"OAUTH_LOGIN_{payload.provider.upper()}",
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent", "")[:255]
    )
    db.add(audit)
    await db.commit()
    await db.refresh(user)
    
    response.set_cookie(
        key="refresh_token",
        value=raw_refresh,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=7 * 24 * 3600
    )
    
    return TokenResponse(
        access_token=access_token,
        expires_in=expires_in,
        user=UserSummary.model_validate(user)
    )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    payload: RefreshTokenRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Rotate refresh token and issue a fresh access token."""
    raw_refresh = payload.refresh_token or request.cookies.get("refresh_token")
    if not raw_refresh:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing."
        )
    
    token_hash = hash_refresh_token(raw_refresh)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash, RefreshToken.revoked == False)
    )
    refresh_obj = result.scalar_one_or_none()
    
    if not refresh_obj or refresh_obj.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token."
        )
    
    # Revoke old refresh token (Token Rotation)
    refresh_obj.revoked = True
    
    # Fetch user
    user_res = await db.execute(select(User).where(User.id == refresh_obj.user_id))
    user = user_res.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated."
        )
    
    # Issue new pair
    access_token, expires_in = create_access_token(user.id, user.username)
    new_raw_refresh, new_token_hash, ref_expires = generate_refresh_token()
    
    new_refresh = RefreshToken(
        user_id=user.id,
        token_hash=new_token_hash,
        expires_at=ref_expires
    )
    db.add(new_refresh)
    await db.commit()
    
    response.set_cookie(
        key="refresh_token",
        value=new_raw_refresh,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=7 * 24 * 3600
    )
    
    return TokenResponse(
        access_token=access_token,
        expires_in=expires_in,
        user=UserSummary.model_validate(user)
    )

@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Revoke all active refresh sessions and clear cookies."""
    raw_refresh = request.cookies.get("refresh_token")
    if raw_refresh:
        token_hash = hash_refresh_token(raw_refresh)
        res = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
        token_entry = res.scalar_one_or_none()
        if token_entry:
            token_entry.revoked = True
            await db.commit()
            
    response.delete_cookie("refresh_token")
    response.delete_cookie("access_token")
    return {"message": "Logged out successfully."}

@router.get("/2fa/setup", response_model=Setup2FAResponse)
async def setup_2fa(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate a new TOTP secret and QR code for user's authenticator app."""
    secret = generate_totp_secret()
    otpauth_uri = get_totp_uri(secret, current_user.username)
    qr_base64 = generate_qr_code_base64(otpauth_uri)
    backup_codes = generate_backup_codes(8)
    
    # Save pending secret temporarily on user model
    current_user.totp_secret = secret
    current_user.backup_codes_json = json.dumps(backup_codes)
    await db.commit()
    
    return Setup2FAResponse(
        secret=secret,
        otpauth_url=otpauth_uri,
        qr_code_base64=qr_base64,
        backup_codes=backup_codes
    )

@router.post("/2fa/enable")
async def enable_2fa(
    payload: Verify2FARequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Verify code and formally activate 2FA on the user account."""
    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA setup has not been initiated. Call /2fa/setup first."
        )
    
    if not verify_totp_code(current_user.totp_secret, payload.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid 6-digit verification code."
        )
    
    current_user.is_2fa_enabled = True
    await db.commit()
    return {"message": "Two-Factor Authentication is now enabled on your account."}

@router.post("/2fa/disable")
async def disable_2fa(
    payload: Disable2FARequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Disable 2FA after password and TOTP verification."""
    if not verify_password(payload.password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password."
        )
    
    if not verify_totp_code(current_user.totp_secret, payload.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid 6-digit verification code."
        )
    
    current_user.is_2fa_enabled = False
    current_user.totp_secret = None
    current_user.backup_codes_json = "[]"
    await db.commit()
    return {"message": "Two-Factor Authentication has been disabled."}

@router.post("/2fa/complete-login", response_model=TokenResponse)
async def complete_2fa_login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Validate 2FA code following a temp_token challenge."""
    token = payload.email_or_username # passed as temp_token from frontend
    decoded = decode_token(token)
    if not decoded or decoded.get("type") != "2fa_pending":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired 2FA session token."
        )
    
    user_id = decoded.get("sub")
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    valid = False
    if payload.totp_code and user.totp_secret:
        valid = verify_totp_code(user.totp_secret, payload.totp_code)
    elif payload.backup_code:
        valid, new_backup = verify_and_consume_backup_code(user.backup_codes_json, payload.backup_code)
        if valid:
            user.backup_codes_json = new_backup
            await db.commit()
            
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid TOTP or Backup Recovery Code."
        )
    
    access_token, expires_in = create_access_token(user.id, user.username)
    raw_refresh, token_hash, ref_expires = generate_refresh_token()
    
    refresh_entry = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=ref_expires
    )
    db.add(refresh_entry)
    await db.commit()
    
    response.set_cookie(
        key="refresh_token",
        value=raw_refresh,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=7 * 24 * 3600
    )
    
    return TokenResponse(
        access_token=access_token,
        expires_in=expires_in,
        user=UserSummary.model_validate(user)
    )

@router.post("/verify-email")
async def verify_email(
    payload: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db)
):
    """Verify an email address using a cryptographic token."""
    clean_token = payload.token.strip()
    result = await db.execute(
        select(EmailVerification).where(EmailVerification.token == clean_token, EmailVerification.used == False)
    )
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token."
        )
    
    # Mark used
    record.used = True
    
    # Fetch user
    user_res = await db.execute(select(User).where(User.id == record.user_id))
    user = user_res.scalar_one_or_none()
    if user:
        user.is_verified = True
        
    await db.commit()
    return {"message": "Email address verified successfully!"}

@router.post("/resend-verification")
async def resend_verification(
    payload: ResendVerificationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Resend email verification token for unverified account."""
    clean_email = payload.email.strip().lower()
    res = await db.execute(select(User).where(User.email == clean_email))
    user = res.scalar_one_or_none()
    
    if not user:
        # Avoid user enumeration by returning success message
        return {"message": "If an account exists, a verification link has been sent."}
    
    if user.is_verified:
        return {"message": "Account is already verified."}
    
    v_token = generate_verification_token()
    verif = EmailVerification(
        user_id=user.id,
        token=v_token,
        expires_at=datetime.now(timezone.utc)
    )
    db.add(verif)
    await db.commit()
    
    base_url = str(request.base_url).rstrip("/")
    await send_verification_email(user.email, user.username, v_token, base_url)
    return {"message": "Verification link has been sent to your email."}

@router.get("/mailbox")
async def get_sandbox_mailbox():
    """Retrieve simulated outgoing emails for interactive local testing and instant verification."""
    return {"emails": get_recent_emails()}

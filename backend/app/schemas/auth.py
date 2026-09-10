from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field

class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=100)

class LoginRequest(BaseModel):
    email_or_username: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)
    totp_code: Optional[str] = Field(None, max_length=10)
    backup_code: Optional[str] = Field(None, max_length=20)

class OAuthLoginRequest(BaseModel):
    provider: str = Field(..., pattern="^(google|github|demo)$")
    email: EmailStr
    name: str
    avatar_url: Optional[str] = None
    provider_id: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserSummary"
    requires_2fa: bool = False
    temp_token: Optional[str] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: Optional[str] = None

class Setup2FAResponse(BaseModel):
    secret: str
    otpauth_url: str
    qr_code_base64: str
    backup_codes: List[str]

class Verify2FARequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)

class Disable2FARequest(BaseModel):
    password: str
    code: str = Field(..., min_length=6, max_length=6)

class VerifyEmailRequest(BaseModel):
    token: str

class ResendVerificationRequest(BaseModel):
    email: EmailStr

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)

from backend.app.schemas.user import UserSummary
TokenResponse.model_rebuild()

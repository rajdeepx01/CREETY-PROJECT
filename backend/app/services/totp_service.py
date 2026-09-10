import base64
import io
import json
import secrets
import pyotp
import qrcode
from backend.app.config import settings

def generate_totp_secret() -> str:
    """Generate a random Base32 TOTP secret."""
    return pyotp.random_base32()

def get_totp_uri(secret: str, username: str, issuer: str = "Credence Showcase") -> str:
    """Generate the standard otpauth:// provisioning URI."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=username, issuer_name=issuer)

def generate_qr_code_base64(otpauth_uri: str) -> str:
    """Render a QR code image as base64 PNG data URL."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=3,
    )
    qr.add_data(otpauth_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="#4f46e5", back_color="#ffffff")
    
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64_str}"

def verify_totp_code(secret: str, code: str) -> bool:
    """Verify a 6-digit TOTP code against secret with 1-step drift tolerance."""
    if not secret or not code:
        return False
    # Clean whitespace or dashes
    clean_code = code.replace(" ", "").replace("-", "").strip()
    totp = pyotp.TOTP(secret)
    return totp.verify(clean_code, valid_window=1)

def generate_backup_codes(count: int = 8) -> list[str]:
    """Generate a set of 8-character human-readable alphanumeric backup codes."""
    codes = []
    for _ in range(count):
        # Format: XXXX-XXXX
        part1 = secrets.token_hex(2).upper()
        part2 = secrets.token_hex(2).upper()
        codes.append(f"{part1}-{part2}")
    return codes

def verify_and_consume_backup_code(backup_codes_json: str | None, code: str) -> tuple[bool, str]:
    """Check if provided code matches an active backup code, and consume it."""
    if not backup_codes_json:
        return False, "[]"
    
    try:
        codes_list = json.loads(backup_codes_json)
    except Exception:
        return False, "[]"
    
    target_code = code.strip().upper()
    if target_code in codes_list:
        codes_list.remove(target_code)
        return True, json.dumps(codes_list)
    
    return False, backup_codes_json

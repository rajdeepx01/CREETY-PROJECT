# 🛡️ Credence — Security Decisions & Threat Model

This document outlines the architectural security decisions, threat mitigations, and defensive design choices implemented across the Credence platform.

---

## 1. Password Hashing & Credential Security

- **Algorithm**: `bcrypt` with work factor 12 (4096 iterations).
- **Salt**: Cryptographically secure pseudo-random salt generated per password.
- **Threat Mitigated**: Rainbow table attacks, offline dictionary attacks, and database breach credential dumps.
- **Implementation**: Plaintext passwords are never logged, never cached in memory, and never included in JSON serialized responses.

---

## 2. Session Management & Dual-Token Architecture

- **Access Token**: Short-lived (30 minutes) JSON Web Token (JWT) signed with HMAC-SHA256 (`HS256`). Contains minimal claims (`sub`, `username`, `exp`, `iat`, `type`).
- **Refresh Token**: High-entropy 64-character URL-safe random string (`secrets.token_urlsafe(64)`).
- **Token Storage**:
  - The database only stores the cryptographic **SHA-256 hash** of the refresh token. Even in a database compromise, attackers cannot forge refresh tokens.
  - Refresh tokens are transmitted via `HttpOnly`, `SameSite=Lax` cookies.
- **Token Rotation**: Every call to `/api/auth/refresh` immediately marks the previous refresh token as `revoked = True` and issues a brand-new refresh token, neutralizing replay and session hijacking attacks.

---

## 3. Deep Magic-Byte File Inspection & Vault Isolation

Attackers commonly attempt to bypass upload filters by renaming malicious `.exe`, `.php`, or shell scripts to `.png` or `.pdf`. Credence enforces a 4-tier upload validation pipeline:

```
1. Extension Whitelist (.pdf, .png, .jpg, .jpeg, .webp)
      │
2. Content-Type Header Inspection
      │
3. Binary Header / Magic-Byte Signature Validation
   - PDF:  %PDF- (0x25 0x50 0x44 0x46 0x2D)
   - PNG:  \x89PNG\r\n\x1a\n (0x89 0x50 0x4E 0x47 0x0D 0x0A 0x1A 0x0A)
   - JPEG: \xFF\xD8\xFF
   - WEBP: RIFF....WEBP
      │
4. Image Structural Verification (Pillow Image.verify())
      │
5. Randomized UUID Storage Outside Web Execution Root
```

- **Serving Strategy**: Files are never served directly as static executable assets. They are streamed via `/api/achievements/media/{id}` with:
  - Strict ownership and privacy authorization checks
  - `X-Content-Type-Options: nosniff` header to prevent MIME-sniffing exploits
  - `Content-Disposition: inline; filename="..."` with sanitized filenames

---

## 4. Two-Factor Authentication (2FA TOTP)

- **Standard**: RFC 6238 Time-based One-Time Password (TOTP).
- **Secret Generation**: Base32 random 160-bit key generated with `pyotp.random_base32()`.
- **Drift Tolerance**: 1-step window (±30 seconds) to accommodate slight clock drift on user devices.
- **Emergency Recovery**: Generates 8 single-use 8-character backup recovery codes (`XXXX-XXXX`). Once used during emergency login, the code is permanently consumed.

---

## 5. Input Sanitization & Anti-XSS Protection

- **Input Validation**: Strongly typed Pydantic models validate incoming formats, types, lengths, and regex patterns.
- **Anti-XSS**: All user-provided free-text (descriptions, titles, bios) is sanitized using `bleach` and escaped with `html.escape()`. Malicious `<script>`, `onerror=`, or `<iframe onload=>` tags are cleanly stripped.
- **SQL Injection Prevention**: SQLAlchemy Async ORM with parameterized queries prevents SQL injection.

---

## 6. HTTP Security Headers & Content Security Policy (CSP)

The server enforces strict HTTP response headers on every request:

```http
Content-Security-Policy: default-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com https://fonts.googleapis.com https://fonts.gstatic.com https://cdn.jsdelivr.net data: blob:; img-src 'self' data: blob: https:; font-src 'self' https://fonts.gstatic.com data:; frame-src 'self' blob:; object-src 'self' blob:; connect-src 'self' https:;
X-Content-Type-Options: nosniff
X-Frame-Options: SAMEORIGIN
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

---

## 7. Rate Limiting & Anti-Brute-Force

An in-memory sliding-window token bucket limiter throttles sensitive endpoints per client IP:
- `POST /api/auth/login`: 15 requests / minute
- `POST /api/auth/register`: 10 requests / minute
- `POST /api/achievements` (Uploads): 20 requests / minute

Violations immediately trigger HTTP 429 Too Many Requests.

---

## 8. Role-Based Access Control (RBAC) & Privacy Enforcement

- **Zero-Trust Resource Ownership**:
  - `PUT /api/achievements/{id}` and `DELETE /api/achievements/{id}` verify `achievement.user_id == current_user.id`.
- **Public vs. Private Exposure**:
  - If a user has `is_profile_public = False`, all unauthenticated requests to `/u/{username}` are blocked with 403 Forbidden.
  - If a profile is public, only achievements with `is_public = True` are included in public queries and media streaming. Private items are completely hidden from public queries.

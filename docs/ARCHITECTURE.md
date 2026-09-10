# 🏛️ Credence — System Architecture Documentation

Credence is an enterprise-grade achievement, credential, and certificate showcase platform engineered with strict security boundaries, fine-grained role-based access control, cryptographic verification, and modern glassmorphic web aesthetics.

---

## 1. High-Level Architecture Diagram

```
                               ┌────────────────────────────────────────┐
                               │           Client Browser / SPA         │
                               │  - Responsive Glassmorphism Interface  │
                               │  - Gallery Grid & Timeline Views       │
                               │  - Public Portfolios (/u/:username)    │
                               │  - Fullscreen Document/PDF Viewer      │
                               │  - 2FA QR Scanner & Backup Codes Modal │
                               └───────────────────┬────────────────────┘
                                                   │ HTTPS / REST API / Bearer JWT
                                                   ▼
                               ┌────────────────────────────────────────┐
                               │         FastAPI Web Application        │
                               │  ├── Security Headers & CSP Middleware │
                               │  ├── Sliding-Window Rate Limiter       │
                               │  ├── Auth & Refresh Token Rotator      │
                               │  ├── File Magic-Byte Security Scanner  │
                               │  ├── Anti-XSS Sanitizer (Bleach/HTML)  │
                               │  └── Privacy & RBAC Policy Engine      │
                               └───────────┬────────────────┬───────────┘
                                           │                │
                        ┌──────────────────┴──┐          ┌──┴──────────────────┐
                        ▼                     ▼          ▼                     ▼
             ┌─────────────────────┐   ┌──────────────┐ ┌────────────────┐ ┌────────────────┐
             │ SQLAlchemy Database │   │  PyOTP 2FA   │ │ Secure Vault   │ │ Email Sandbox  │
             │ (SQLite / Postgres) │   │ (RFC 6238)   │ │ (Isolated UUID │ │ & Live Mailbox │
             │ Users & Credentials │   │ QR Generator │ │  Storage)      │ │ Outbound Log   │
             └─────────────────────┘   └──────────────┘ └────────────────┘ └────────────────┘
```

---

## 2. Directory Structure

```
GEMINI-PROJECT/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # Application entry point, CSP middleware, SPA routes
│   │   ├── config.py                # Environment variables, token expirations, upload rules
│   │   ├── database.py              # Async SQLAlchemy engine & session dependency
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py              # User, RefreshToken, EmailVerification, AuditLog
│   │   │   └── achievement.py       # Achievement metadata, category, privacy flags
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py              # Login, Register, 2FA, OAuth schemas
│   │   │   ├── user.py              # Profile update & public profile schemas
│   │   │   └── achievement.py       # Achievement CRUD schemas & responses
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py              # /api/auth endpoints (login, register, 2fa, verify)
│   │   │   ├── users.py             # /api/users endpoints (profile, public profile)
│   │   │   └── achievements.py      # /api/achievements endpoints (CRUD, media stream)
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py      # Bcrypt password hashing & JWT generation
│   │   │   ├── totp_service.py      # PyOTP 2FA, Base64 QR code rendering, backup codes
│   │   │   ├── file_service.py      # Binary magic-byte inspection, Pillow, secure storage
│   │   │   └── email_service.py     # Verification emails & dev sandbox mailbox
│   │   └── security/
│   │       ├── __init__.py
│   │       ├── deps.py              # get_current_user & auth dependencies
│   │       ├── rate_limiter.py      # Sliding-window IP rate limiting
│   │       └── sanitization.py      # Bleach XSS cleaner & filename sanitizer
│   └── uploads/                     # Vault directory for sanitized certificate media
├── frontend/
│   ├── index.html                   # Single Page Application entrypoint
│   ├── css/
│   │   ├── styles.css               # Obsidian theme, design tokens, layout, glassmorphism
│   │   └── components.css           # Profile cards, timeline, modals, 2FA QR, dropzone
│   └── js/
│       ├── api.js                   # API client with token auto-refresh & retry logic
│       ├── auth.js                  # Authentication, 2FA challenge & setup modal
│       ├── achievements.js          # Gallery/Timeline renderer, filter, CRUD, document viewer
│       ├── profile.js               # Public portfolio viewer (/u/:username) & QR share modal
│       └── app.js                   # Main application router, toast notifications, modals
├── docs/
│   ├── ARCHITECTURE.md              # System design & architecture documentation
│   ├── DATABASE_SCHEMA.md           # Schema models, relationships & index designs
│   └── SECURITY_DECISIONS.md        # Comprehensive security audit & risk mitigations
├── requirements.txt                 # Backend Python dependencies
├── run.py                           # 1-click startup runner
└── README.md                        # Quick start & documentation
```

---

## 3. Data Flow & Execution Lifecycles

### 1. Registration & Verification
1. User submits email, username, full name, and password.
2. Backend validates format, hashes password via `bcrypt` (12 rounds).
3. Database creates `User` and `EmailVerification` record with high-entropy token.
4. Email is logged to the Sandbox Mailbox (and optionally sent via SMTP).
5. User receives short-lived Access JWT + HTTP-only Refresh Token.

### 2. File Upload & Magic-Byte Validation
1. Client selects a certificate file (PDF, PNG, JPG, WEBP).
2. Backend checks file size (<10MB) and file extension.
3. Backend reads the first 12 binary bytes and checks header signatures (`%PDF-`, `\x89PNG`, `\xFF\xD8\xFF`, `RIFF...WEBP`).
4. If valid image, Pillow verifies internal structural integrity.
5. The file is saved with a non-guessable UUID in the isolated `uploads/` directory.
6. The file is streamed through `/api/achievements/media/{id}` after verifying ownership and privacy permissions.

### 3. Public Portfolio View (`/u/{username}`)
1. Guest visits `/u/{username}`.
2. Backend checks if `user.is_profile_public == True`.
3. Backend filters only achievements where `is_public == True`.
4. Frontend renders public gallery/timeline with shareable QR code and verified credential links.

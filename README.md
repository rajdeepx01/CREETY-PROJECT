# 💎 Credence — Secure Achievement & Credential Showcase Platform

Credence is an enterprise-grade digital credential vault and showcase web application designed for professionals, developers, students, and creators to upload, verify, manage, and showcase their certificates, awards, badges, licenses, and project milestones with cryptographic verification, granular privacy controls, and instant shareable public portfolio links (`/u/username`).

---

## ✨ Key Features & Capabilities

### 🏆 Achievement & Credential Management
- **Multi-Format Support**: Upload PDF certificates, high-resolution badge images (PNG, JPG, WEBP), and link external verification credentials.
- **Rich Metadata**: Categorize achievements (*Certificate, Award, Badge, Project Completion, License, Hackathon, Publication, Degree*), issue dates, expiration dates, credential IDs, grade/score, skills tags, and issuer details.
- **Gallery & Timeline Switcher**: Toggle effortlessly between a responsive **3D-accented Gallery Grid** and a chronological **Milestone Journey Timeline**.
- **Interactive Document Viewer**: In-browser fullscreen viewer for PDF certificates and high-resolution credentials with 1-click download.
- **Search & Multi-Filtering**: Instant debounced full-text search, category pills, visibility filtering (Public/Private), and multiple sorting modes (Newest, Oldest, Title A-Z, Recently Added).

### 🔒 Enterprise Security & Privacy Controls
- **Bcrypt Password Hashing**: Passwords are salted and hashed using `bcrypt` (12 rounds) — never stored or logged in plain text.
- **Dual-Token Session Architecture**: Short-lived Access Tokens (30m) + HTTP-only Refresh Tokens (7d) with automatic token rotation and instant revocation.
- **Two-Factor Authentication (2FA TOTP)**: RFC 6238 compliant TOTP integration. Scan QR codes with Google Authenticator, 1Password, or Authy, with generated emergency single-use backup recovery codes.
- **Magic-Byte File Inspection**: Binary header inspection validates genuine file content (`%PDF-`, `\x89PNG`, `\xFF\xD8\xFF`, `RIFF...WEBP`), rejecting renamed executables or malicious payloads.
- **Isolated File Vault**: Uploads are saved with randomized UUIDs outside the web root and served exclusively through authorized streaming endpoints with `Content-Disposition: inline` and `X-Content-Type-Options: nosniff`.
- **Zero-Trust Access Control (RBAC)**: Strict owner authorization checks for all mutations (edit, delete, toggle privacy).
- **Public / Private Privacy Controls**:
  - Per-achievement visibility toggle (Public 🌐 vs Private 🔒).
  - Master profile privacy toggle (allows complete portfolio unlisting).
- **Rate Limiting**: Sliding-window IP rate limiting on login, registration, and upload endpoints.
- **Strict HTTP Security Headers**: Content-Security-Policy (CSP), Strict-Transport-Security (HSTS), X-Frame-Options (SAMEORIGIN), and anti-XSS text sanitization via `bleach`.
- **Email Verification & Sandbox Mailbox**: Cryptographic verification tokens with a live visual in-app Dev Mailbox for 1-click local testing.

---

## 🛠️ Quick Start Guide

### 1. Install Dependencies
```powershell
.\venv\Scripts\python -m pip install -r requirements.txt
```

### 2. Launch the Application
Run the 1-click runner:
```powershell
.\venv\Scripts\python run.py
```
Or with uvicorn directly:
```powershell
.\venv\Scripts\python -m uvicorn backend.app.main:app --reload --port 8000
```

### 3. Open in Browser
Visit **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 📁 Project Architecture

```
GEMINI-PROJECT/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entry point, CSP middleware, SPA routes
│   │   ├── config.py                # Environment configurations & upload rules
│   │   ├── database.py              # Async SQLAlchemy engine & session dependency
│   │   ├── models/                  # User, Achievement, RefreshToken, Verification models
│   │   ├── schemas/                 # Pydantic validation models
│   │   ├── routes/                  # REST API routes (/api/auth, /api/users, /api/achievements)
│   │   ├── services/                # Bcrypt, JWT, PyOTP 2FA, Magic-byte File Service
│   │   └── security/                # Rate limiter, Anti-XSS sanitizers, Auth dependencies
│   └── uploads/                     # Secure isolated media vault
├── frontend/
│   ├── index.html                   # Responsive Single Page Application
│   ├── css/
│   │   ├── styles.css               # Obsidian Dark & Indigo Glassmorphism theme
│   │   └── components.css           # Cards, timeline, dropzone, modals, 2FA QR
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
└── README.md                        # Documentation & setup guide
```

---

## 🧪 Documentation & References
- [Architecture Details](docs/ARCHITECTURE.md)
- [Database Schema & ERD](docs/DATABASE_SCHEMA.md)
- [Security Audit & Decisions](docs/SECURITY_DECISIONS.md)

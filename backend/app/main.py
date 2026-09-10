import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from backend.app.config import settings, FRONTEND_DIR
from backend.app.database import init_db
from backend.app.routes import auth_router, users_router, achievements_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables
    await init_db()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    
    # Secure HTTP response headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    # Modern Content Security Policy (allowing necessary CDN fonts, icons, pdf renderer)
    csp = (
        "default-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com https://fonts.googleapis.com https://fonts.gstatic.com https://cdn.jsdelivr.net data: blob:; "
        "img-src 'self' data: blob: https:; "
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com data:; "
        "frame-src 'self' blob:; "
        "object-src 'self' blob:; "
        "connect-src 'self' https:;"
    )
    response.headers["Content-Security-Policy"] = csp
    
    return response

# Register API Routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(achievements_router)

# Healthcheck endpoint
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION
    }

# Mount static frontend assets
if FRONTEND_DIR.exists():
    app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
    app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")
    
    # Serve SPA index for frontend client routes
    @app.get("/")
    async def serve_index():
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/u/{username}")
    @app.get("/profile/{username}")
    @app.get("/dashboard")
    @app.get("/login")
    @app.get("/register")
    @app.get("/settings")
    @app.get("/mailbox")
    async def serve_spa_routes(request: Request):
        return FileResponse(FRONTEND_DIR / "index.html")

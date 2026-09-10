import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import (
    APP_NAME,
    APP_TAGLINE,
    GEMINI_API_KEY,
    DEFAULT_MODEL,
    AVAILABLE_MODELS,
)
from app.schemas.chat import ChatRequest, ChatResponse, StatusResponse
from app.services.gemini_service import GeminiFriendService

app = FastAPI(
    title=f"{APP_NAME} API",
    description=f"{APP_TAGLINE} - Powered by Google Gemini",
    version="1.0.0",
)

# Enable CORS for flexible hosting & local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

service = GeminiFriendService()


# Status & Configuration API
@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    """Returns application status, configured models, and API key availability."""
    return StatusResponse(
        status="ok",
        app_name=f"{APP_NAME} - {APP_TAGLINE}",
        api_key_configured=bool(GEMINI_API_KEY),
        default_model=DEFAULT_MODEL,
        available_models=AVAILABLE_MODELS,
    )


@app.get("/api/starters")
async def get_starter_prompts():
    """Returns curated starter conversation topics."""
    return service.get_starters()


# Chat Endpoints
@app.post("/api/chat", response_model=ChatResponse)
async def chat_sync(request: ChatRequest):
    """Synchronous chat endpoint returning the complete reply."""
    result = await service.chat_sync(request)
    if result.status == "error":
        raise HTTPException(status_code=400, detail=result.error)
    return result


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """Real-time token streaming chat endpoint via Server-Sent Events (SSE)."""
    return StreamingResponse(
        service.chat_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# Serve Static UI Files
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    async def serve_index():
        index_file = os.path.join(STATIC_DIR, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": f"{APP_NAME} Backend is running. static/index.html not found."}

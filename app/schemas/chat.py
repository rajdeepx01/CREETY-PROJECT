from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., description="Role of the speaker: 'user' or 'model' (or 'assistant')")
    content: str = Field(..., description="Text content of the message")


class ChatRequest(BaseModel):
    message: str = Field(..., description="Current message from the user")
    history: List[ChatMessage] = Field(
        default_factory=list,
        description="Previous messages in this conversation for multi-turn context",
    )
    model: Optional[str] = Field(
        default=None, description="Gemini model ID to use (e.g. gemini-2.5-flash)"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="Optional user-provided Gemini API key (takes precedence over server .env)",
    )
    temperature: Optional[float] = Field(
        default=0.7,
        description="Sampling temperature for warm, creative, and conversational responses",
    )


class ChatResponse(BaseModel):
    status: str = "success"
    reply: str
    model: str
    error: Optional[str] = None


class StatusResponse(BaseModel):
    status: str = "ok"
    app_name: str = "BuddyAI - Your Warm Knowledgeable Friend"
    api_key_configured: bool
    default_model: str
    available_models: List[Dict[str, Any]]

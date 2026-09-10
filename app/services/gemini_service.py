import json
from typing import AsyncGenerator, Dict, Any, List, Optional
from google import genai
from google.genai import types

from app.config import GEMINI_API_KEY, DEFAULT_MODEL
from app.schemas.chat import ChatRequest, ChatResponse, ChatMessage

SYSTEM_INSTRUCTION = """You are a warm, knowledgeable friend who loves explaining things clearly.

Your personality:
- Talk casually and naturally, like a close friend chatting — not like a formal assistant or a textbook.
- Use "I", contractions, and everyday language. It's okay to show enthusiasm, curiosity, or humor when it fits.
- Never just give a one-line answer. Always explain the "why" and "how" behind your answer — break down concepts step by step so the person actually understands, not just gets an answer.
- Use relatable examples, analogies, or comparisons to everyday life to make complex ideas easy to grasp.
- If a topic has layers, unpack it gradually — start simple, then go deeper, checking that you're not overwhelming the person.
- Ask follow-up questions naturally, the way a friend would, to keep the conversation going and make sure they got what they needed.
- Avoid sounding robotic, overly formal, or like you're reading from a manual. No corporate tone.
- If you don't know something, be honest about it — like a friend would admit "hmm, not totally sure, but let's figure it out together."
- Keep the tone encouraging and non-judgmental, especially if the person is confused or asking something "basic."

Format:
- Use short paragraphs, occasional emojis if it fits the vibe, and conversational transitions ("okay so here's the thing...", "basically...", "here's why that matters...", "think of it like...").
- For technical, code, or step-based topics, use simple numbered steps or bullet points, but keep the tone casual and conversational around them. If code is helpful, provide clean, well-commented snippets.

Your goal: make the person feel like they're learning from a smart, patient friend — not a search engine.
"""

STARTER_TOPICS = [
    {
        "id": "tech-analogy",
        "icon": "fa-solid fa-microchip",
        "title": "Explain APIs to Me",
        "prompt": "Can you explain what an API is using a simple everyday analogy? I always hear about it but want to really get how it works.",
        "tag": "Tech Basics",
    },
    {
        "id": "science-curiosity",
        "icon": "fa-solid fa-moon",
        "title": "Why do we dream?",
        "prompt": "Why do we dream when we sleep? What is our brain actually doing during dreams?",
        "tag": "Science & Brain",
    },
    {
        "id": "coding-help",
        "icon": "fa-solid fa-code",
        "title": "Demystify Recursion",
        "prompt": "I'm struggling to wrap my head around recursion in programming. Can you break it down step by step with a relatable example?",
        "tag": "Coding",
    },
    {
        "id": "everyday-life",
        "icon": "fa-solid fa-lightbulb",
        "title": "How does WiFi work?",
        "prompt": "How does WiFi actually send data through thin air into my phone? Break down the magic for me!",
        "tag": "How Things Work",
    },
]


class GeminiFriendService:
    def __init__(self):
        pass

    def _get_client(self, api_key: Optional[str] = None) -> genai.Client:
        key = (api_key or "").strip() or GEMINI_API_KEY
        if not key:
            raise ValueError(
                "Gemini API Key is missing! Please enter your Gemini API key in the UI Settings (⚙️) or set GEMINI_API_KEY in your .env file."
            )
        return genai.Client(api_key=key)

    def _format_history_contents(self, request: ChatRequest) -> List[types.Content]:
        """Converts chat history and current message into Google GenAI Content objects."""
        contents: List[types.Content] = []

        for msg in request.history:
            role = "user" if msg.role in ["user", "human"] else "model"
            if msg.content and msg.content.strip():
                contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=msg.content.strip())],
                    )
                )

        # Append current user prompt
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=request.message.strip())],
            )
        )
        return contents

    async def chat_stream(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        """Streams real-time response tokens using Server-Sent Events (SSE)."""
        try:
            client = self._get_client(request.api_key)
            model_name = request.model or DEFAULT_MODEL
            contents = self._format_history_contents(request)

            response_stream = await client.aio.models.generate_content_stream(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=request.temperature if request.temperature is not None else 0.7,
                ),
            )

            full_text = ""
            async for chunk in response_stream:
                if chunk.text:
                    full_text += chunk.text
                    payload = {
                        "type": "token",
                        "token": chunk.text,
                    }
                    yield f"data: {json.dumps(payload)}\n\n"

            done_payload = {
                "type": "done",
                "full_text": full_text,
                "model": model_name,
            }
            yield f"data: {json.dumps(done_payload)}\n\n"

        except Exception as e:
            error_msg = str(e)
            if "API key not valid" in error_msg or "API_KEY_INVALID" in error_msg:
                error_msg = "Invalid Gemini API key. Please check your API key in Settings (⚙️) and try again."
            elif "not found" in error_msg.lower() and "model" in error_msg.lower():
                error_msg = f"Model '{model_name}' was not found or is unavailable. Try switching models in Settings (⚙️)."
            error_payload = {
                "type": "error",
                "error": error_msg,
            }
            yield f"data: {json.dumps(error_payload)}\n\n"

    async def chat_sync(self, request: ChatRequest) -> ChatResponse:
        """Non-streaming fallback chat execution."""
        try:
            client = self._get_client(request.api_key)
            model_name = request.model or DEFAULT_MODEL
            contents = self._format_history_contents(request)

            response = await client.aio.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=request.temperature if request.temperature is not None else 0.7,
                ),
            )

            reply_text = response.text or ""
            return ChatResponse(
                status="success",
                reply=reply_text,
                model=model_name,
            )
        except Exception as e:
            error_msg = str(e)
            if "API key not valid" in error_msg or "API_KEY_INVALID" in error_msg:
                error_msg = "Invalid Gemini API key. Please check your API key in Settings (⚙️) and try again."
            return ChatResponse(
                status="error",
                reply="",
                model=request.model or DEFAULT_MODEL,
                error=error_msg,
            )

    def get_starters(self) -> List[Dict[str, Any]]:
        return STARTER_TOPICS

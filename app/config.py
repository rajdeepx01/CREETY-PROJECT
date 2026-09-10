import os
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

APP_NAME = "BuddyAI"
APP_TAGLINE = "Your Warm, Knowledgeable Friend"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-2.5-flash")

AVAILABLE_MODELS = [
    {
        "id": "gemini-2.5-flash",
        "name": "Gemini 2.5 Flash (Super Fast & Friendly)",
        "description": "Lightning fast, warm, and natural conversationalist. Recommended for everyday chat.",
        "recommended": True,
    },
    {
        "id": "gemini-2.5-pro",
        "name": "Gemini 2.5 Pro (Deep Thinker & Thorough)",
        "description": "Best for unpacking complex topics, in-depth breakdowns, and intricate questions.",
        "recommended": False,
    },
    {
        "id": "gemini-3.7-flash",
        "name": "Gemini 3.7 Flash (Next-Gen Intelligence)",
        "description": "Latest generation model with high responsiveness and reasoning capability.",
        "recommended": False,
    },
]

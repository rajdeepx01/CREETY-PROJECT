from backend.app.routes.auth import router as auth_router
from backend.app.routes.users import router as users_router
from backend.app.routes.achievements import router as achievements_router

__all__ = ["auth_router", "users_router", "achievements_router"]

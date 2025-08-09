# ==============================================================================
# routers/__init__.py — API Route Handlers
# ==============================================================================
# Purpose: FastAPI route handlers for the application
# ==============================================================================

from .url_router import router as url_router

__all__ = [
    'url_router',
]

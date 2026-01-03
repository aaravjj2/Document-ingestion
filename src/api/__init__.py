"""API module initialization."""

from fastapi import APIRouter

from src.api.dashboard import router as dashboard_router
from src.api.documents import router as documents_router
from src.api.search import router as search_router

# Create main API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(documents_router)
api_router.include_router(search_router)
api_router.include_router(dashboard_router)

__all__ = ["api_router"]

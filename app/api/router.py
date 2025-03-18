from fastapi import APIRouter

from app.api.notes import router as notes_router
from app.api.ai import router as ai_router
from app.api.analytics import router as analytics_router

# Create main API router
api_router = APIRouter()

# Include all sub-routers
api_router.include_router(notes_router, prefix="/notes", tags=["Notes"])
api_router.include_router(ai_router, prefix="/ai", tags=["AI"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
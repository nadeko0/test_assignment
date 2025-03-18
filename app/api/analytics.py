from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas import AnalyticsResponse
from app.services.analytics import analytics_service
from app.api.notes import get_or_create_user_id

# Create router
router = APIRouter()

@router.get("", response_model=AnalyticsResponse)
async def get_analytics(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session)
):
    """
    Get analytics data about notes using Gemini API for text analysis.
    Returns statistics including total word count, average note length,
    common words, and top longest/shortest notes.
    """
    # Get user ID from cookie (for authorization context, not used in analytics)
    user_id = await get_or_create_user_id(request, response)
    
    # Generate analytics
    analytics_data = await analytics_service.calculate_analytics(session)
    
    if "error" in analytics_data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=analytics_data["message"]
        )
    
    return analytics_data
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_session
from app.models import Note
from app.schemas import NoteSummary
from app.services.ai import ai_service, SUPPORTED_LANGUAGES
from app.api.notes import get_or_create_user_id

# Create router
router = APIRouter()

@router.get("/summarize/{note_id}", response_model=NoteSummary)
async def summarize_note(
    note_id: int,
    request: Request,
    response: Response,
    language: str = Query("en", description="Language code for summarization"),
    session: AsyncSession = Depends(get_session)
):
    # Validate language
    if language not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported language: {language}. Supported languages: {', '.join(SUPPORTED_LANGUAGES.keys())}"
        )
    
    # Get user ID from cookie
    user_id = await get_or_create_user_id(request, response)
    
    # Get the note
    query = select(Note).where(
        Note.id == note_id,
        Note.user_id == user_id,
        Note.is_deleted == False
    )
    result = await session.execute(query)
    note = result.scalar_one_or_none()
    
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note with ID {note_id} not found or is deleted"
        )
    
    # Generate summary
    summary_data = await ai_service.summarize_note(
        note_id=note.id,
        title=note.title,
        content=note.content,
        language=language
    )
    
    if not summary_data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate summary. Please try again later."
        )
    
    return summary_data

@router.get("/languages", response_model=dict)
async def get_supported_languages():
    return {
        "supported_languages": SUPPORTED_LANGUAGES
    }
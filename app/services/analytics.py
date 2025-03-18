import pandas as pd
from collections import Counter
import re
import logging
import json
import httpx
from typing import Dict, List, Any
from datetime import datetime, UTC
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Note
from app.services.cache import redis_service
from app.services.ai import GEMINI_API_KEY

# Configure logging
logger = logging.getLogger(__name__)

# Simple tokenizer for basic word counting
def simple_tokenize(text):
    """Simple word tokenizer that splits on whitespace and punctuation but preserves emails and URLs."""
    # First extract emails and URLs
    emails_urls = []
    
    # Find emails
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    emails_urls.extend(emails)
    
    # Find URLs
    url_pattern = r'https?://[^\s]+'
    urls = re.findall(url_pattern, text)
    emails_urls.extend(urls)
    
    # Create a copy of the text for processing
    processed_text = text
    
    # Remove emails and URLs from the text temporarily
    for item in emails_urls:
        processed_text = processed_text.replace(item, " ")
    
    # Process remaining text
    words = re.findall(r'\b\w+\b', processed_text.lower())
    
    # Add back emails and URLs (converted to lowercase for consistency)
    words.extend([item.lower() for item in emails_urls])
    
    return words

# Common stopwords for filtering (basic English only, without NLTK)
COMMON_STOPWORDS = {
    'a', 'an', 'the', 'and', 'or', 'but', 'if', 'because', 'as', 'what',
    'which', 'this', 'that', 'these', 'those', 'then', 'just', 'so', 'than',
    'such', 'both', 'through', 'about', 'for', 'is', 'of', 'while', 'during',
    'to', 'from', 'in', 'on', 'by', 'at', 'into', 'with', 'about', 'between'
}

# Gemini API for text analysis
async def analyze_text_with_gemini(contents: List[str]) -> Dict[str, Any]:
    """Use Gemini API for text analysis."""
    if not contents:
        return {
            "word_count": 0,
            "common_words": []
        }
    
    # Combine all contents for analysis
    full_text = " ".join(contents)
    
    # Gemini API endpoint
    api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    
    # Prompt for Gemini
    prompt = """
    Analyze the following text and provide a structured JSON response with:
    1. Total word count
    2. A list of the 10 most common meaningful words and their frequency counts (exclude common stopwords)
    
    Format the response as a valid JSON object with fields "word_count" and "common_words" (an array of objects with "word" and "count" fields).
    
    Example output format:
    {
      "word_count": 120,
      "common_words": [
        {"word": "example", "count": 5},
        {"word": "analysis", "count": 3}
      ]
    }
    
    Here's the text to analyze:
    
    {text}
    """
    
    # Replace placeholder with actual text
    prompt = prompt.replace("{text}", full_text[:8000])  # Limit text length
    
    try:
        # Make the API request
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{api_url}?key={GEMINI_API_KEY}",
                json={
                    "contents": [
                        {
                            "parts": [
                                {"text": prompt}
                            ]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.1,
                        "topK": 40,
                        "topP": 0.95,
                        "maxOutputTokens": 1024,
                    }
                },
                headers={"Content-Type": "application/json"},
                timeout=30.0
            )
            
            if response.status_code != 200:
                logger.error(f"Gemini API error: {response.status_code} - {response.text}")
                return self_analyze_text(full_text)
            
            result = response.json()
            
            # Extract the generated text
            if (
                "candidates" in result 
                and result["candidates"] 
                and "content" in result["candidates"][0]
                and "parts" in result["candidates"][0]["content"]
                and result["candidates"][0]["content"]["parts"]
            ):
                analysis_text = result["candidates"][0]["content"]["parts"][0]["text"]
                
                # Extract JSON from the response
                try:
                    # Find JSON object in the response
                    json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
                    if json_match:
                        analysis_json = json.loads(json_match.group(0))
                        return analysis_json
                except json.JSONDecodeError:
                    logger.error("Failed to parse JSON from Gemini response")
            
            return self_analyze_text(full_text)
            
    except Exception as e:
        logger.error(f"Error calling Gemini API for text analysis: {str(e)}")
        return self_analyze_text(full_text)

def self_analyze_text(text: str) -> Dict[str, Any]:
    """Perform simple text analysis without external dependencies."""
    words = simple_tokenize(text)
    
    # Filter out stopwords
    filtered_words = [w for w in words if w.isalpha() and w not in COMMON_STOPWORDS]
    
    # Count words
    word_count = len(words)
    
    # Get common words
    word_counter = Counter(filtered_words)
    common_words = [{"word": word, "count": count} for word, count in word_counter.most_common(10)]
    
    return {
        "word_count": word_count,
        "common_words": common_words
    }

class AnalyticsService:
    """Service for analyzing notes data and generating statistics."""
    
    CACHE_KEY = "analytics:data"
    CACHE_TTL = 3600  # 1 hour in seconds
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def calculate_analytics(self, session: AsyncSession, force_refresh=False) -> Dict[str, Any]:
        """
        Calculate analytics data from notes.
        - Total word count across all notes
        - Average note length
        - Most common words
        - Top 3 longest and shortest notes
        - Distribution of notes by date
        """
        # Check cache first unless force refresh is requested
        if not force_refresh:
            # Use injected cache in tests, otherwise use redis_service
            cache_service = getattr(self, '_cache', redis_service)
            
            try:
                cached_data = await cache_service.get_value(self.CACHE_KEY)
                if cached_data:
                    logger.info("Using cached analytics data")
                    # Parse JSON if it's a string
                    if isinstance(cached_data, str):
                        cached_data = json.loads(cached_data)
                    # Add cached flag to indicate this is from cache
                    cached_data["cached"] = True
                    return cached_data
            except Exception as e:
                logger.warning(f"Error retrieving from cache: {str(e)}")
        
        logger.info("Generating fresh analytics data")
        
        try:
            # Get analytics data
            analytics_data = await self._get_notes_analytics(session)
            
            # Cache the results
            try:
                # Use injected cache in tests, otherwise use redis_service
                cache_service = getattr(self, '_cache', redis_service)
                await cache_service.set_value(
                    self.CACHE_KEY, 
                    analytics_data, 
                    ttl=self.CACHE_TTL
                )
            except Exception as e:
                logger.warning(f"Error setting cache: {str(e)}")
            
            return analytics_data
            
        except Exception as e:
            logger.error(f"Error calculating analytics: {str(e)}")
            return {
                "error": "Failed to calculate analytics",
                "message": str(e)
            }
            
    async def _get_notes_analytics(self, session: AsyncSession) -> Dict[str, Any]:
        """Get analytics data from notes."""
        import asyncio
        
        # Query active notes
        active_notes_query = await session.execute(
            select(Note).where(Note.is_deleted == False)
        )
        
        # Handle both normal sessions and AsyncMock in tests
        if hasattr(active_notes_query, 'scalars'):
            scalars_result = active_notes_query.scalars()
            if asyncio.iscoroutine(scalars_result):
                scalars_result = await scalars_result
            all_result = scalars_result.all()
            if asyncio.iscoroutine(all_result):
                active_notes = await all_result
            else:
                active_notes = all_result
        else:
            # Fallback for simple mock scenarios
            active_notes = []
        
        # Query deleted notes
        try:
            deleted_notes_query = await session.execute(
                select(Note).where(Note.is_deleted == True)
            )
            
            # Handle both normal sessions and AsyncMock in tests
            if hasattr(deleted_notes_query, 'scalars'):
                scalars_result = deleted_notes_query.scalars()
                if asyncio.iscoroutine(scalars_result):
                    scalars_result = await scalars_result
                all_result = scalars_result.all()
                if asyncio.iscoroutine(all_result):
                    deleted_notes = await all_result
                else:
                    deleted_notes = all_result
            else:
                # Fallback for simple mock scenarios
                deleted_notes = []
        except Exception as e:
            logger.warning(f"Error getting deleted notes: {str(e)}")
            deleted_notes = []
        
        # Basic counts
        total_notes_count = len(active_notes) + len(deleted_notes)
        active_notes_count = len(active_notes)
        deleted_notes_count = len(deleted_notes)
        
        if not active_notes:
            logger.warning("No active notes found for analytics")
            return {
                "total_notes_count": total_notes_count,
                "active_notes_count": active_notes_count,
                "deleted_notes_count": deleted_notes_count,
                "total_word_count": 0,
                "average_note_length": 0,
                "top_common_words": [],
                "longest_notes": [],
                "shortest_notes": [],
                "notes_by_date": {},
                "generated_at": datetime.now(UTC).isoformat(),
                "analysis_method": "gemini_api"
            }
        
        # Convert to pandas DataFrame for basic analysis
        notes_data = []
        note_contents = []
        
        for note in active_notes:
            # Use simple word count for basic stats
            words = simple_tokenize(note.content.lower())
            word_count = len(words)
            note_contents.append(note.content)
            
            notes_data.append({
                "id": note.id,
                "title": note.title,
                "content": note.content,
                "word_count": word_count,
                "created_at": note.created_at,
                "updated_at": note.updated_at
            })
        
        df = pd.DataFrame(notes_data)
        
        # Calculate total word count (will be replaced by Gemini result if available)
        total_word_count = df["word_count"].sum() if len(df) > 0 else 0
        
        # Calculate average note length
        average_note_length = df["word_count"].mean() if len(df) > 0 else 0
        
        # Find longest and shortest notes
        df_sorted_by_length = df.sort_values("word_count", ascending=False)
        longest_notes = df_sorted_by_length.head(3)[["id", "title", "word_count"]].to_dict("records") if len(df) > 0 else []
        shortest_notes = df_sorted_by_length.tail(3)[["id", "title", "word_count"]].to_dict("records") if len(df) > 0 else []
        
        # Use Gemini API for text analysis
        logger.info("Using Gemini API for text analysis")
        text_analysis = await analyze_text_with_gemini(note_contents)
        top_common_words = text_analysis.get("common_words", [])
        
        # If Gemini returns word count, use it (more accurate)
        if "word_count" in text_analysis and text_analysis["word_count"] > 0:
            total_word_count = text_analysis["word_count"]
        
        # Group notes by date
        if len(df) > 0:
            df["date"] = df["created_at"].dt.date
            notes_by_date = df.groupby("date").size().to_dict()
            notes_by_date = {str(date): count for date, count in notes_by_date.items()}
        else:
            notes_by_date = {}
        
        # Prepare response
        return {
            "total_notes_count": total_notes_count,
            "active_notes_count": active_notes_count,
            "deleted_notes_count": deleted_notes_count,
            "total_word_count": int(total_word_count),
            "average_note_length": float(average_note_length),
            "top_common_words": top_common_words,
            "longest_notes": longest_notes,
            "shortest_notes": shortest_notes,
            "notes_by_date": notes_by_date,
            "generated_at": datetime.now(UTC).isoformat(),
            "analysis_method": "gemini_api"
        }

# Singleton instance
analytics_service = AnalyticsService()
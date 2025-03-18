import json
import logging
import google.generativeai as genai
import httpx
from typing import Dict, Optional
from datetime import datetime, UTC

# Import redis_service directly to use it with proper patching in tests
from app.services.cache import redis_service

# Configure logging
logger = logging.getLogger(__name__)

# Gemini API configuration
GEMINI_API_KEY = "Your api key"
GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

# Map of supported languages
SUPPORTED_LANGUAGES = {
    "en": "English",
    "ru": "Russian",
    "uk": "Ukrainian",
    "sk": "Slovak",
    "de": "German",
    "cs": "Czech"
}

# Prompts for different languages
SUMMARY_PROMPTS = {
    "en": "Summarize the following note concisely, capturing the main points:",
    "ru": "Кратко изложите следующую заметку, выделив основные моменты:",
    "uk": "Стисло підсумуйте наступну нотатку, виділяючи основні моменти:",
    "sk": "Stručne zhrňte nasledujúcu poznámku, zachytávajúc hlavné body:",
    "de": "Fassen Sie die folgende Notiz prägnant zusammen und erfassen Sie die Hauptpunkte:",
    "cs": "Stručně shrňte následující poznámku a zachyťte hlavní body:"
}

class AIService:
    
    def __init__(self, cache_service=None):
        self.api_key = GEMINI_API_KEY
        self.model = GEMINI_MODEL
        
        # Initialize Google Generative AI client
        genai.configure(api_key=self.api_key)
    
    async def summarize_note(self, note_id: int, title: str, content: str, language: str = "en") -> Optional[Dict]:
        # Validate language
        if language not in SUPPORTED_LANGUAGES:
            logger.warning(f"Unsupported language: {language}, falling back to English")
            language = "en"
        
        # Check cache first
        cached_summary = await redis_service.get_note_summary(note_id, language)
        if cached_summary:
            logger.info(f"Cache hit for note summary: {note_id} ({language})")
            return cached_summary
        
        logger.info(f"Generating summary for note {note_id} in {SUPPORTED_LANGUAGES[language]}")
        
        try:
            # Call Gemini API directly using httpx
            summary = await self._call_gemini_api(title, content, language)
            
            if not summary:
                logger.error(f"Failed to generate summary for note {note_id}")
                return None
            
            # Prepare response data
            summary_data = {
                "note_id": note_id,
                "original_title": title,
                "summary": summary,
                "generated_at": datetime.now(UTC).isoformat(),
                "language": language
            }
            
            # Cache the result
            await redis_service.set_note_summary(note_id, summary_data, language)
            
            return summary_data
            
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return None
    
    async def _call_gemini_api(self, title: str, content: str, language: str = "en") -> Optional[str]:
        try:
            prompt = SUMMARY_PROMPTS.get(language, SUMMARY_PROMPTS["en"])
            full_prompt = f"{prompt}\n\nTitle: {title}\n\nContent: {content}"
            
            # API request data
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": full_prompt}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.2,
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": 1024,
                }
            }
            
            # Make the API request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{GEMINI_API_URL}?key={self.api_key}",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    logger.error(f"Gemini API error: {response.status_code} - {response.text}")
                    return None
                
                response_data = response.json()
                
                # Extract the summary text from response
                if (
                    "candidates" in response_data 
                    and response_data["candidates"] 
                    and "content" in response_data["candidates"][0]
                    and "parts" in response_data["candidates"][0]["content"]
                    and response_data["candidates"][0]["content"]["parts"]
                ):
                    summary = response_data["candidates"][0]["content"]["parts"][0]["text"]
                    return summary.strip()
                
                logger.error(f"Unexpected Gemini API response format: {response_data}")
                return None
                
        except Exception as e:
            logger.error(f"Error calling Gemini API: {str(e)}")
            return None

# Singleton instance
ai_service = AIService()
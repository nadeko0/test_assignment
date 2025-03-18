from datetime import datetime
from typing import Dict, List, Optional, Any, ClassVar
from pydantic import BaseModel, Field, computed_field, TypeAdapter

class NoteBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Note title")
    content: str = Field(..., min_length=1, description="Note content text")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "Meeting notes",
                "content": "Discussed project timeline and next steps."
            }
        }
    }

class NoteCreate(NoteBase):
    pass

class NoteUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="Updated note title")
    content: Optional[str] = Field(None, min_length=1, description="Updated note content")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "Updated meeting notes",
                "content": "Revised project timeline and next steps."
            }
        }
    }

class NoteVersion(BaseModel):
    title: str
    content: str
    updated_at: datetime
    
    @computed_field
    def word_count(self) -> int:
        return len(self.content.split())

class NoteResponse(NoteBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_deleted: bool
    deleted_at: Optional[datetime] = None
    
    # Version history
    versions: Dict[str, NoteVersion] = Field(default_factory=dict)
    
    @computed_field
    def version_count(self) -> int:
        return len(self.versions)
    
    model_config = {
        "from_attributes": True
    }

class NoteSummary(BaseModel):
    note_id: int
    original_title: str
    summary: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    language: str = "en"
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "note_id": 1,
                "original_title": "Meeting notes",
                "summary": "Discussed project timeline and planned next steps.",
                "generated_at": "2025-03-15T12:00:00Z",
                "language": "en"
            }
        }
    }

class AnalyticsResponse(BaseModel):
    total_notes_count: int
    active_notes_count: int
    deleted_notes_count: int
    total_word_count: int
    average_note_length: float
    top_common_words: List[Dict[str, Any]]
    longest_notes: List[Dict[str, Any]]
    shortest_notes: List[Dict[str, Any]]
    notes_by_date: Dict[str, int]
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "total_notes_count": 24,
                "active_notes_count": 20,
                "deleted_notes_count": 4,
                "total_word_count": 4500,
                "average_note_length": 187.5,
                "top_common_words": [{"word": "meeting", "count": 42}, {"word": "project", "count": 35}],
                "longest_notes": [{"id": 5, "title": "Research summary", "word_count": 423}],
                "shortest_notes": [{"id": 12, "title": "Reminder", "word_count": 15}],
                "notes_by_date": {"2025-03-14": 5, "2025-03-15": 3}
            }
        }
    }

# Use TypeAdapter for validation of collections
NoteResponseList = TypeAdapter(List[NoteResponse])
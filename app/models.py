from datetime import datetime, UTC
from typing import Dict, List, Optional, Any, Annotated
from sqlalchemy import String, DateTime, Boolean, func, JSON
from sqlalchemy.orm import mapped_column, Mapped

from app.database import Base

# Helper function for SQLAlchemy defaults
def utc_now():
    return datetime.now(UTC)

class Note(Base):
    """Note model with version history in JSONB field."""
    
    __tablename__ = "notes"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=utc_now, 
        nullable=False
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=utc_now, 
        onupdate=utc_now, 
        nullable=False
    )
    
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, 
        default=False, 
        nullable=False
    )
    
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, 
        nullable=True
    )
    
    # JSONB field to store version history (up to 5 versions)
    versions: Mapped[Dict[str, Any]] = mapped_column(
        JSON, 
        default=dict, 
        nullable=False
    )
    
    # Field to identify user (via cookie) for the 10 notes limit
    user_id: Mapped[str] = mapped_column(
        String(255), 
        nullable=False,
        index=True
    )

    def add_version(self):
        """Add the current state as a new version in the history."""
        # Make a copy of the current versions to avoid reference issues
        # This is especially important for SQLite with JSON fields
        current_versions = dict(self.versions) if self.versions else {}
        
        # Create new version entry
        new_version = {
            "title": self.title,
            "content": self.content,
            "updated_at": self.updated_at.isoformat() if self.updated_at else datetime.now(UTC).isoformat()
        }
        
        # Get version numbers and sort them
        version_numbers = [int(k) for k in current_versions.keys() if k.isdigit()]
        version_numbers.sort()
        
        # If we have 5 versions already, remove the oldest
        if len(version_numbers) >= 5 and version_numbers:
            oldest_version = str(version_numbers[0])
            current_versions.pop(oldest_version, None)
        
        # Add new version with next version number
        next_version = "1" if not version_numbers else str(max(version_numbers) + 1)
        current_versions[next_version] = new_version
        
        # Create a new dict to ensure it's seen as a change by SQLAlchemy
        # This helps with proper detection of changes in JSON fields
        self.versions = dict(current_versions)
        
        return self
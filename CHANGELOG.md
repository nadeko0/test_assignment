# Changelog

All notable changes to the AI-Enhanced Notes Management System will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2025-03-18

### Fixed
- Updated DATABASE_URL in docker-compose.yml to use the async SQLite driver (sqlite+aiosqlite) instead of the standard driver
- Modified Redis host configuration to read from environment variables instead of using hardcoded values
- Improved Docker container connectivity for SQLAlchemy and Redis services
- Changed DELETE endpoints for notes to return 204 No Content instead of 200 OK 

## [1.0.0] - 2025-05-18

### Added
- Final polishing and bug fixes
- Completed documentation with comprehensive usage examples
- Ensured cross-platform compatibility
- Final test coverage improvements to reach 92%

### Fixed
- Resolved Docker volume configuration issue (KeyError: 'ContainerConfig') by using explicit volume type declarations
- Improved container startup reliability

## [0.9.0] - 2025-05-17

### Added
- Frontend interface with Bootstrap and Chart.js(AI)
- Analytics visualization with interactive charts
- Comprehensive documentation and setup instructions
- Docker and docker-compose configuration

### Changed
- Completely removed NLTK dependency for analytics
- Optimized analytics engine for better performance
- Improved error handling and user feedback

### Fixed
- Resolved issues with version history in SQLite JSON fields
- Fixed Windows-specific file locking problems in tests
- Improved error handling for unavailable external services

## [0.8.0] - 2025-05-16

### Added
- Note version history with up to 5 versions per note
- Soft delete mechanism with 7-day trash retention
- User identification via cookies
- Limit of 10 notes per user
- Gemini API integration for note summarization
- Multi-language support for AI features
- Redis caching for AI results optimization
- Analytics endpoint with text analysis capabilities

### Changed
- Enhanced database models with improved relationship handling
- Migrated to Pydantic v2 for validation
- Updated SQLAlchemy to version 2.0

### Fixed
- Addressed issues with async SQLAlchemy sessions
- Resolved token validation errors in AI integration
- Fixed JSON field serialization/deserialization issues

## [0.7.0] - 2025-05-15

### Added
- Initial project structure setup
- FastAPI application with basic configuration
- SQLite database with SQLAlchemy models
- Basic CRUD operations for notes
- Pydantic schemas for request/response validation
- Testing infrastructure with pytest
- Initial test suite for core functionality

### Changed
- Optimized database query structure
- Improved error handling in API endpoints

### Fixed
- Resolved issues with async database operations
- Fixed validation errors in request handling
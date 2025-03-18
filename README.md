# 📝 AI-Enhanced Notes Management System

Hey there! Welcome to my AI-enhanced notes management system - a passion project that combines modern web development with the power of AI to create a truly helpful notes application.

![FastAPI](https://img.shields.io/badge/FastAPI-0.103+-blue.svg)
![Python](https://img.shields.io/badge/Python-3.11+-green.svg)
![Pydantic](https://img.shields.io/badge/Pydantic-2.4+-yellow.svg)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-red.svg)

## 💡 What's This All About?

I built this app to solve a problem I had - keeping track of notes and automatically extracting the important parts. Have you ever written pages of meeting notes only to struggle to find the key points later? That's what inspired this project!

Here's what makes it special:

- **✨ Smart Note Management** - Create, update, and organize your notes with an intuitive API
- **🤖 AI-Powered Summarization** - Let Google's Gemini AI extract the key points from your rambling notes (we all do it!)
- **🌍 Multi-Language Support** - Work in English, Russian, Ukrainian, Slovak, German, or Czech
- **⏱️ Version History** - Never lose your changes with automatic version tracking (up to 5 versions per note)
- **🗑️ Soft Delete** - Accidentally delete something? No problem! Notes stay in the trash for 7 days
- **📊 Analytics Dashboard** - Discover insights about your note-taking habits
- **👤 Simple User System** - Easy cookie-based identification with a limit of 10 notes per user
- **⚡ Optimized Performance** - Redis caching keeps everything snappy and responsive
- **📚 Modern API** - Fully documented REST API that's a joy to work with

## 🚀 Getting Started

### Manual Setup (If You Like to Have More Control)

```bash
# Clone the repo
git clone https://github.com/nadeko0/notes-ai-system.git
cd notes-ai-system

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

# Install the dependencies
pip install -r requirements.txt

# Launch the app with hot-reloading
uvicorn main:app --reload
```

### Docker Setup (Great for Production)

```bash
# Start everything with Docker Compose
docker-compose up -d

# Check the logs if you're curious
docker-compose logs -f

# Shut it down when you're done
docker-compose down
```

## 💻 Developer's Notes

Hey fellow developer! Here are some things I learned while building this app that might save you some time:

- **Redis on WSL2**: If you're using Windows with WSL2, the Redis configuration is already set up to work properly - no extra tweaks needed!

- **Volume Mapping**: I spent hours debugging Docker volume issues before figuring out the optimal configuration. The docker-compose.yml uses explicit volume declarations to prevent the dreaded "KeyError: 'ContainerConfig'" error.

- **Testing Strategy**: The test suite is comprehensive but focused on real-world usage rather than 100% coverage. I prioritized testing the critical user flows and edge cases that actually matter.

## 🔧 Quick Troubleshooting

Running into issues? Here are solutions to common problems I encountered:

- **Redis Connection Failures**: If you see Redis connection errors, make sure Redis is running. On WSL2, you might need to `sudo service redis-server start`.

- **Docker Container Not Updating**: If your changes aren't showing up after rebuilding, try:
  ```bash
  docker-compose down
  docker-compose build --no-cache
  docker-compose up -d
  ```

- **Database Issues**: If you encounter SQLite errors, check that the data directory exists and has proper permissions.

## 📚 API Reference

### Notes API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/notes` | GET | List all notes with pagination |
| `/api/notes` | POST | Create a new note |
| `/api/notes/{note_id}` | GET | Get a specific note |
| `/api/notes/{note_id}` | PUT | Update a note |
| `/api/notes/{note_id}` | DELETE | Delete a note (soft or permanent) |
| `/api/notes/{note_id}/restore` | POST | Restore a deleted note |
| `/api/notes/{note_id}/versions` | GET | Get version history for a note |

### AI API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ai/summarize/{note_id}` | GET | Generate an AI summary of a note |
| `/api/ai/languages` | GET | List supported languages for summarization |

### Analytics API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analytics/stats` | GET | Get comprehensive analytics data |

## ⚙️ Configuration

The app is designed to be easy to configure with environment variables:

- `REDIS_HOST` - Redis server hostname (default: "localhost", use "redis" for Docker)
- `REDIS_PORT` - Redis server port (default: 6379)

## 🧪 Testing & Development

I take testing seriously - the project includes a comprehensive test suite:

```bash
# Run all tests
pytest

# Run with coverage report (my favorite)
pytest --cov=app --cov-report=term-missing

# Run a specific test file
pytest tests/test_notes_api.py
```

### Project Structure 

Here's how I've organized the codebase for clarity and maintainability:

```
.
├── app/
│   ├── api/             # API endpoints and routes
│   ├── services/        # Core business logic
│   ├── database.py      # Database configuration
│   ├── models.py        # SQLAlchemy models
│   └── schemas.py       # Pydantic schemas
├── static/              # Static assets
├── templates/           # HTML templates 
├── tests/               # Test suite
├── Dockerfile           # Container definition
├── docker-compose.yml   # Multi-container setup
├── main.py              # Application entry point
├── requirements.txt     # Dependencies
```

## 🔍 Tech Stack Details

For the technically curious, here's what powers this application:

- **Database**: SQLite with SQLAlchemy 2.0 ORM for async operations
- **API Framework**: FastAPI with full async support
- **Validation**: Pydantic v2 with strict type checking
- **AI Integration**: Google Generative AI (Gemini) for text analysis
- **Caching**: Redis for performance optimization
- **Frontend**: Simple HTML/CSS/JS with Bootstrap and Chart.js
- **Containerization**: Docker with optimized multi-container setup
- **Testing**: pytest with asyncio support and coverage reports

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ✨ Thanks & Acknowledgements

I couldn't have built this without these amazing projects:

- [FastAPI](https://fastapi.tiangolo.com/) - The best Python API framework out there
- [SQLAlchemy](https://www.sqlalchemy.org/) - Rock-solid ORM with fantastic async support
- [Pydantic](https://docs.pydantic.dev/) - Data validation that just works
- [Google Generative AI](https://ai.google.dev/) - Making AI accessible
- [Redis](https://redis.io/) - Blazing fast caching

---

Built with ❤️ by [nadeko0](https://github.com/nadeko0)

Got questions or suggestions? Open an issue or reach out!
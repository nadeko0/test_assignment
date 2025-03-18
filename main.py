import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os
import logging
from contextlib import asynccontextmanager

from app.database import init_db
from app.api.router import api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for application startup and shutdown."""
    # Initialize database and resources on startup
    await init_db()
    logger.info("Application starting up")
    logger.info("Using Gemini API for text analysis")
    
    yield  # Application runs here
    
    # Cleanup on shutdown (if needed)
    logger.info("Application shutting down")

app = FastAPI(
    title="AI-Enhanced Notes Management System",
    description="A RESTful API for managing notes with AI capabilities",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates for serving frontend
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the frontend application."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.middleware("http")
async def user_limit_middleware(request: Request, call_next):
    """Middleware to limit users to 10 notes via cookies."""
    response = await call_next(request)
    return response


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8140, reload=True)
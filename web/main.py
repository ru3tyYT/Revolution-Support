"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .config import get_web_config
from .constants import API_PREFIX

# Import routers (will be created in PLAN_03)
# from .routers import auth, ai, knowledge, analytics, guilds, tickets

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    config = get_web_config()
    config.validate()
    yield
    # Shutdown

app = FastAPI(
    title="Discord Support Bot API",
    description="Web API for Discord Support Bot",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
config = get_web_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers (will be added in PLAN_03)
# app.include_router(auth.router, prefix=AUTH_PREFIX, tags=["auth"])
# app.include_router(ai.router, prefix=API_PREFIX, tags=["ai"])
# etc.

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Discord Support Bot API",
        "version": "1.0.0",
        "docs": "/docs"
    }

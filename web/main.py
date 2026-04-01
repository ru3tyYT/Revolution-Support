"""FastAPI application entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_web_config
from .constants import API_PREFIX, AUTH_PREFIX
from .routers import (
    ai_router,
    analytics_router,
    auth_router,
    guilds_router,
    knowledge_router,
    tickets_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    config = get_web_config()
    config.validate()
    yield


app = FastAPI(
    title="Discord Support Bot API",
    description="Web API for Discord Support Bot",
    version="1.0.0",
    lifespan=lifespan,
)

config = get_web_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix=AUTH_PREFIX, tags=["Authentication"])
app.include_router(ai_router, prefix=f"{API_PREFIX}/ai", tags=["ai"])
app.include_router(knowledge_router, prefix=f"{API_PREFIX}/knowledge", tags=["knowledge"])
app.include_router(analytics_router, prefix=f"{API_PREFIX}/analytics", tags=["analytics"])
app.include_router(guilds_router, prefix=f"{API_PREFIX}/guilds", tags=["guilds"])
app.include_router(tickets_router, prefix=f"{API_PREFIX}/tickets", tags=["tickets"])


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
        "docs": "/docs",
    }

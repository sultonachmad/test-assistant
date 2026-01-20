"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.websocket_manager import ws_manager

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    # Startup
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")

    # Initialize database tables
    from app.crud.db_connection import db
    logger.info("Database initialized")

    yield

    # Shutdown
    logger.info("Shutting down...")


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and register routers
from app.api import user, tasks, reminders, notifications, auth, sync, dashboard, inbox, calendar, documents, sheets, ai, taiga, bandung_sync

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(user.router, prefix="/api/user", tags=["User"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["Tasks"])
app.include_router(reminders.router, prefix="/api/reminders", tags=["Reminders"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(sync.router, prefix="/api/sync", tags=["Sync"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(inbox.router, prefix="/api/inbox", tags=["Inbox"])
app.include_router(calendar.router, prefix="/api/calendar", tags=["Calendar"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(sheets.router, prefix="/api/sheets", tags=["Sheets"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI Assistant"])
app.include_router(taiga.router, prefix="/api/taiga", tags=["Taiga"])
app.include_router(bandung_sync.router, prefix="/api/bandung-sync", tags=["Bandung Resource Sync"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    """WebSocket endpoint for real-time updates."""
    await ws_manager.connect(websocket, user_id)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            # Echo or process incoming messages if needed
            logger.debug(f"Received from user {user_id}: {data}")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, user_id)
        logger.info(f"User {user_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        ws_manager.disconnect(websocket, user_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )

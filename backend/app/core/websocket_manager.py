"""WebSocket connection manager for real-time updates."""
import logging
from typing import Dict, List
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        """Accept and store a new WebSocket connection."""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"WebSocket connected for user {user_id}")

    def disconnect(self, websocket: WebSocket, user_id: int):
        """Remove a WebSocket connection."""
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"WebSocket disconnected for user {user_id}")

    async def send_personal_message(self, user_id: int, message: dict):
        """Send a message to a specific user."""
        if user_id in self.active_connections:
            disconnected = []
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}: {e}")
                    disconnected.append(websocket)

            # Clean up disconnected sockets
            for ws in disconnected:
                self.disconnect(ws, user_id)

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected users."""
        for user_id in list(self.active_connections.keys()):
            await self.send_personal_message(user_id, message)


# Singleton instance
ws_manager = WebSocketManager()


async def send_notification(user_id: int, notification_type: str, data: dict):
    """Helper function to send notifications via WebSocket."""
    await ws_manager.send_personal_message(user_id, {
        "type": notification_type,
        **data
    })


async def send_sync_progress(user_id: int, sync_type: str, status: str, detail: str = None):
    """Helper function to send sync progress updates."""
    await ws_manager.send_personal_message(user_id, {
        "type": "sync_progress",
        "sync_type": sync_type,
        "status": status,
        "detail": detail
    })

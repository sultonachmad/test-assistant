"""Standard response schemas."""
from typing import Any, Optional, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class StandardResponse(BaseModel, Generic[T]):
    """Standard API response wrapper."""
    status: bool = True
    message: Optional[str] = None
    data: Optional[T] = None


class ErrorResponse(BaseModel):
    """Error response schema."""
    status: bool = False
    message: str
    detail: Optional[str] = None


class SyncStatus(BaseModel):
    """Sync status response."""
    sync_type: str
    status: str
    items_synced: int = 0
    last_sync: Optional[str] = None
    error: Optional[str] = None


class DashboardData(BaseModel):
    """Dashboard aggregated data."""
    task_summary: Any
    upcoming_reminders: list
    recent_notifications: list
    calendar_today: list
    ai_suggestions: list
    sync_status: dict

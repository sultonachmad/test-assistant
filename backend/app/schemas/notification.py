"""Notification schemas."""
from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel


class NotificationType(str, Enum):
    """Notification type enum."""
    REMINDER = "reminder"
    TASK_UPDATE = "task_update"
    SYNC_COMPLETE = "sync_complete"
    AI_SUGGESTION = "ai_suggestion"
    SYSTEM = "system"


class NotificationBase(BaseModel):
    """Base notification schema."""
    type: NotificationType
    title: str
    message: Optional[str] = None
    link: Optional[str] = None


class NotificationCreate(NotificationBase):
    """Schema for creating a notification."""
    pass


class Notification(NotificationBase):
    """Notification schema with ID and timestamps."""
    id: int
    user_id: int
    is_read: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationList(BaseModel):
    """Notification list with unread count."""
    notifications: List[Notification]
    unread_count: int
    total: int

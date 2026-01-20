"""Reminder schemas."""
from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel


class ReminderStatus(str, Enum):
    """Reminder status enum."""
    PENDING = "pending"
    SENT = "sent"
    CANCELLED = "cancelled"


class ReminderVia(str, Enum):
    """Reminder delivery channel."""
    EMAIL = "email"
    CALENDAR = "calendar"
    INAPP = "inapp"


class ReminderBase(BaseModel):
    """Base reminder schema."""
    title: str
    description: Optional[str] = None
    remind_at: datetime
    remind_via: List[ReminderVia] = [ReminderVia.INAPP]
    is_recurring: bool = False
    recurrence_rule: Optional[str] = None
    task_id: Optional[int] = None


class ReminderCreate(ReminderBase):
    """Schema for creating a reminder."""
    pass


class ReminderUpdate(BaseModel):
    """Schema for updating a reminder."""
    title: Optional[str] = None
    description: Optional[str] = None
    remind_at: Optional[datetime] = None
    remind_via: Optional[List[ReminderVia]] = None
    is_recurring: Optional[bool] = None
    recurrence_rule: Optional[str] = None


class Reminder(ReminderBase):
    """Reminder schema with ID and timestamps."""
    id: int
    user_id: int
    status: ReminderStatus = ReminderStatus.PENDING
    calendar_event_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReminderSnooze(BaseModel):
    """Schema for snoozing a reminder."""
    snooze_minutes: int = 15


class ReminderList(BaseModel):
    """Paginated reminder list."""
    reminders: List[Reminder]
    total: int
    page: int
    limit: int

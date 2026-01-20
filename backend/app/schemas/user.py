"""User schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    name: Optional[str] = None
    image: Optional[str] = None
    timezone: str = "Asia/Singapore"
    notification_email: bool = True
    notification_calendar: bool = True
    notification_inapp: bool = True


class UserCreate(UserBase):
    """Schema for creating a user."""
    pass


class UserUpdate(BaseModel):
    """Schema for updating a user."""
    name: Optional[str] = None
    image: Optional[str] = None
    timezone: Optional[str] = None
    notification_email: Optional[bool] = None
    notification_calendar: Optional[bool] = None
    notification_inapp: Optional[bool] = None


class User(UserBase):
    """User schema with ID and timestamps."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserSettings(BaseModel):
    """User notification settings."""
    notification_email: bool = True
    notification_calendar: bool = True
    notification_inapp: bool = True
    timezone: str = "Asia/Singapore"

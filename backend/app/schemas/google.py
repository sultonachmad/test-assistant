"""Google API related schemas."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class GoogleToken(BaseModel):
    """Google OAuth token schema."""
    access_token: str
    refresh_token: str
    token_expiry: datetime
    scopes: List[str]


class GoogleAuthStatus(BaseModel):
    """Google authentication status."""
    is_connected: bool = False
    email: Optional[str] = None
    scopes: List[str] = []
    expires_at: Optional[datetime] = None


class EmailMessage(BaseModel):
    """Email message schema."""
    id: int
    gmail_id: str
    thread_id: Optional[str] = None
    subject: Optional[str] = None
    sender: Optional[str] = None
    snippet: Optional[str] = None
    body_preview: Optional[str] = None
    received_at: Optional[datetime] = None
    labels: List[str] = []
    is_processed: bool = False

    class Config:
        from_attributes = True


class ChatMessage(BaseModel):
    """Chat message schema."""
    id: int
    space_id: str
    space_name: Optional[str] = None
    message_id: str
    sender_name: Optional[str] = None
    sender_email: Optional[str] = None
    text: Optional[str] = None
    sent_at: Optional[datetime] = None
    is_processed: bool = False

    class Config:
        from_attributes = True


class CalendarEvent(BaseModel):
    """Calendar event schema."""
    id: int
    event_id: str
    calendar_id: str = "primary"
    summary: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    attendees: List[str] = []
    is_all_day: bool = False
    status: Optional[str] = None

    class Config:
        from_attributes = True


class CalendarEventCreate(BaseModel):
    """Schema for creating a calendar event."""
    summary: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: datetime
    end_time: datetime
    attendees: List[str] = []
    is_all_day: bool = False


class Document(BaseModel):
    """Google Doc schema."""
    id: int
    doc_id: str
    doc_name: Optional[str] = None
    doc_url: Optional[str] = None
    last_modified: Optional[datetime] = None
    is_active: bool = True

    class Config:
        from_attributes = True


class DocumentAdd(BaseModel):
    """Schema for adding a document to monitor."""
    doc_id: str
    doc_name: Optional[str] = None
    doc_url: Optional[str] = None


class InboxSummary(BaseModel):
    """Inbox summary with emails and chats."""
    emails: List[EmailMessage]
    chats: List[ChatMessage]
    email_count: int
    chat_count: int
    ai_summary: Optional[str] = None

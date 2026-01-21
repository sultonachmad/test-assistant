"""Task comment schemas."""
from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class CommentType(str, Enum):
    """Types of task comments."""
    ASK = "ask"  # Need more information
    UPDATE = "update"  # Progress update
    SOLUTION = "solution"  # Solution suggestion or root cause
    TEST_CASE = "test_case"  # Test case or completion check


class TaskCommentBase(BaseModel):
    """Base task comment fields."""
    comment_type: CommentType
    content: str
    estimated_days: Optional[int] = None
    suggested_start_date: Optional[datetime] = None
    suggested_due_date: Optional[datetime] = None


class TaskCommentCreate(TaskCommentBase):
    """Fields for creating a task comment."""
    task_id: int
    is_ai_generated: bool = False
    ai_prompt: Optional[str] = None


class TaskCommentUpdate(BaseModel):
    """Fields for updating a task comment."""
    content: Optional[str] = None
    estimated_days: Optional[int] = None
    suggested_start_date: Optional[datetime] = None
    suggested_due_date: Optional[datetime] = None


class TaskComment(TaskCommentBase):
    """Full task comment with all fields."""
    id: int
    task_id: int
    user_id: int
    is_ai_generated: bool
    ai_prompt: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AICommentRequest(BaseModel):
    """Request for AI-generated comment."""
    task_id: int
    comment_type: CommentType
    prompt: Optional[str] = None  # Optional user prompt for context
    selected_comment_ids: Optional[List[int]] = None  # Selected comments for context


class AICommentResponse(BaseModel):
    """Response with AI-generated comment content."""
    content: str
    estimated_days: Optional[int] = None  # For solution type
    suggested_start_date: Optional[datetime] = None
    suggested_due_date: Optional[datetime] = None


class TaskSuggestionFromCommentsRequest(BaseModel):
    """Request to create task suggestions from selected comments."""
    task_id: int
    selected_comment_ids: List[int]
    prompt: Optional[str] = None


class TaskSuggestionFromCommentsResponse(BaseModel):
    """Response with suggested tasks from comments."""
    suggestions: List[dict]  # List of task suggestions

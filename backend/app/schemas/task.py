"""Task schemas."""
from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel


class TaskStatus(str, Enum):
    """Task status enum."""
    DONE = "done"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    ASSIGNED = "assigned"


class TaskPriority(str, Enum):
    """Task priority enum."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class RecurrenceType(str, Enum):
    """Task recurrence type enum."""
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"


class TaskBase(BaseModel):
    """Base task schema."""
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.ASSIGNED
    priority: TaskPriority = TaskPriority.MEDIUM
    project: Optional[str] = None  # Project this task belongs to
    start_date: Optional[datetime] = None  # When task work started
    due_date: Optional[datetime] = None  # Target completion date
    completed_date: Optional[datetime] = None  # Actual completion date
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    source_url: Optional[str] = None
    assigned_to: Optional[str] = None  # Team member this task is assigned to
    tags: Optional[List[str]] = None
    # Recurrence fields
    is_recurring: bool = False
    recurrence_type: RecurrenceType = RecurrenceType.NONE
    recurrence_end_date: Optional[datetime] = None  # When to stop generating new instances
    parent_task_id: Optional[int] = None  # For generated instances, points to template task


class TaskCreate(TaskBase):
    """Schema for creating a task."""
    pass


class TaskUpdate(BaseModel):
    """Schema for updating a task."""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    project: Optional[str] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    assigned_to: Optional[str] = None
    tags: Optional[List[str]] = None
    # Recurrence fields
    is_recurring: Optional[bool] = None
    recurrence_type: Optional[RecurrenceType] = None
    recurrence_end_date: Optional[datetime] = None


class Task(TaskBase):
    """Task schema with ID and timestamps."""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskStatusUpdate(BaseModel):
    """Schema for updating task status only."""
    status: TaskStatus


class TaskSummary(BaseModel):
    """Task statistics summary."""
    total: int = 0
    done: int = 0
    in_progress: int = 0
    on_hold: int = 0
    assigned: int = 0
    overdue: int = 0


class TaskList(BaseModel):
    """Paginated task list."""
    tasks: List[Task]
    total: int
    page: int
    limit: int
    has_more: bool

"""Task API routes."""
import logging
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.core.session import get_current_user
from app.crud.task import task_db
from app.crud.notification import notification_db
from app.schemas.task import (
    Task, TaskCreate, TaskUpdate, TaskStatus, TaskPriority,
    TaskStatusUpdate, TaskSummary, TaskList
)
from app.schemas.notification import NotificationCreate, NotificationType
from app.schemas.response import StandardResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=StandardResponse[TaskList])
async def get_tasks(
    status_filter: Optional[str] = Query(None, alias="status"),
    priority: Optional[str] = None,
    project: Optional[str] = None,
    source_type: Optional[str] = None,
    due_before: Optional[datetime] = None,
    assigned_to: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=500),
    current_user: dict = Depends(get_current_user)
):
    """Get all tasks with filters."""
    tasks, total = task_db.get_all(
        user_id=current_user["id"],
        status=status_filter,
        priority=priority,
        project=project,
        source_type=source_type,
        due_before=due_before,
        assigned_to=assigned_to,
        search=search,
        page=page,
        limit=limit
    )

    task_list = TaskList(
        tasks=tasks,
        total=total,
        page=page,
        limit=limit,
        has_more=(page * limit) < total
    )
    return StandardResponse(status=True, data=task_list)


@router.post("", response_model=StandardResponse[Task])
async def create_task(
    task: TaskCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new task."""
    new_task = task_db.create(current_user["id"], task)
    if not new_task:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create task"
        )
    return StandardResponse(status=True, data=new_task, message="Task created successfully")


@router.get("/summary", response_model=StandardResponse[TaskSummary])
async def get_task_summary(current_user: dict = Depends(get_current_user)):
    """Get task statistics summary."""
    summary = task_db.get_summary(current_user["id"])
    return StandardResponse(status=True, data=summary)


@router.get("/assignees", response_model=StandardResponse[list])
async def get_assignees(current_user: dict = Depends(get_current_user)):
    """Get list of unique assignees for filtering."""
    assignees = task_db.get_assignees(current_user["id"])
    return StandardResponse(status=True, data=assignees)


@router.get("/projects", response_model=StandardResponse[list])
async def get_projects(current_user: dict = Depends(get_current_user)):
    """Get list of unique projects for filtering."""
    projects = task_db.get_projects(current_user["id"])
    return StandardResponse(status=True, data=projects)


@router.get("/{task_id}", response_model=StandardResponse[Task])
async def get_task(task_id: int, current_user: dict = Depends(get_current_user)):
    """Get a specific task."""
    task = task_db.get_by_id(task_id, current_user["id"])
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return StandardResponse(status=True, data=task)


@router.patch("/{task_id}", response_model=StandardResponse[Task])
async def update_task(
    task_id: int,
    task: TaskUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a task."""
    existing = task_db.get_by_id(task_id, current_user["id"])
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    updated_task = task_db.update(task_id, current_user["id"], task)
    if not updated_task:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update task"
        )
    return StandardResponse(status=True, data=updated_task, message="Task updated successfully")


@router.patch("/{task_id}/status", response_model=StandardResponse[Task])
async def update_task_status(
    task_id: int,
    status_update: TaskStatusUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update task status only."""
    existing = task_db.get_by_id(task_id, current_user["id"])
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    updated_task = task_db.update_status(task_id, current_user["id"], status_update.status)
    if not updated_task:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update task status"
        )

    # Create notification for status change
    notification_db.create(
        current_user["id"],
        NotificationCreate(
            type=NotificationType.TASK_UPDATE,
            title=f"Task status updated",
            message=f"'{updated_task.title}' is now {updated_task.status.value.replace('_', ' ')}",
            link=f"/tasks/{task_id}"
        )
    )

    return StandardResponse(status=True, data=updated_task, message="Task status updated")


@router.delete("/{task_id}", response_model=StandardResponse)
async def delete_task(task_id: int, current_user: dict = Depends(get_current_user)):
    """Delete a task."""
    existing = task_db.get_by_id(task_id, current_user["id"])
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if not task_db.delete(task_id, current_user["id"]):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete task"
        )
    return StandardResponse(status=True, message="Task deleted successfully")


@router.post("/bulk-status", response_model=StandardResponse)
async def bulk_update_status(
    task_ids: list[int],
    new_status: TaskStatus,
    current_user: dict = Depends(get_current_user)
):
    """Update status for multiple tasks."""
    updated_count = 0
    for task_id in task_ids:
        if task_db.update_status(task_id, current_user["id"], new_status):
            updated_count += 1

    return StandardResponse(
        status=True,
        message=f"Updated {updated_count} of {len(task_ids)} tasks"
    )


@router.get("/recurring/list", response_model=StandardResponse[list])
async def get_recurring_tasks(current_user: dict = Depends(get_current_user)):
    """Get all recurring task templates."""
    tasks = task_db.get_recurring_tasks(current_user["id"])
    return StandardResponse(status=True, data=tasks)


@router.post("/recurring/generate", response_model=StandardResponse[list])
async def generate_recurring_tasks(current_user: dict = Depends(get_current_user)):
    """Check and generate new instances of recurring tasks."""
    generated = task_db.check_and_generate_recurring_tasks(current_user["id"])
    return StandardResponse(
        status=True,
        data=generated,
        message=f"Generated {len(generated)} recurring task instances"
    )


@router.post("/{task_id}/generate-instance", response_model=StandardResponse[Task])
async def generate_task_instance(
    task_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Manually generate a new instance of a recurring task."""
    existing = task_db.get_by_id(task_id, current_user["id"])
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if not existing.is_recurring:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task is not a recurring task"
        )

    new_instance = task_db.generate_recurring_instance(current_user["id"], task_id)
    if not new_instance:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate task instance"
        )
    return StandardResponse(status=True, data=new_instance, message="Task instance generated")

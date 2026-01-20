"""AI Assistant API routes for email summarization and task extraction."""
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel

from app.core.session import get_current_user
from app.core.llm_client import llm_client
from app.crud.email_cache import email_cache_db
from app.crud.task import task_db
from app.schemas.response import StandardResponse

logger = logging.getLogger(__name__)
router = APIRouter()


class TaskSuggestion(BaseModel):
    """A task suggestion extracted from emails."""
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    due_date_hint: Optional[str] = None
    source_email_id: Optional[str] = None
    source_email_subject: Optional[str] = None
    source_email_sender: Optional[str] = None


class EmailSummaryResponse(BaseModel):
    """Response for email summary and task suggestions."""
    email_count: int
    date_range: dict
    summary: str
    task_suggestions: List[TaskSuggestion]


class AddTasksRequest(BaseModel):
    """Request to add selected task suggestions."""
    tasks: List[TaskSuggestion]
    project: Optional[str] = None


class AddTasksResponse(BaseModel):
    """Response for adding tasks."""
    added_count: int
    task_ids: List[int]


class GenerateDescriptionRequest(BaseModel):
    """Request to generate a task description."""
    title: str
    current_description: Optional[str] = None
    project: Optional[str] = None


class GenerateDescriptionResponse(BaseModel):
    """Response with generated description and title suggestion."""
    description: str
    suggested_title: Optional[str] = None


def get_current_week_range():
    """Get start and end of current week (Monday to Sunday)."""
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_week = start_of_week + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return start_of_week, end_of_week


@router.get("/email-suggestions", response_model=StandardResponse[EmailSummaryResponse])
async def get_email_suggestions(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Get email summary and task suggestions for a date range.
    Default: current week (Monday to Sunday).
    """
    # Default to current week if no dates provided
    if not start_date or not end_date:
        start_date, end_date = get_current_week_range()

    # Get emails in date range
    emails = email_cache_db.get_emails_by_date_range(
        user_id=current_user["id"],
        start_date=start_date,
        end_date=end_date,
        limit=100
    )

    if not emails:
        return StandardResponse(
            status=True,
            data=EmailSummaryResponse(
                email_count=0,
                date_range={
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                summary="No emails found in this date range.",
                task_suggestions=[]
            )
        )

    try:
        # Generate summary and extract tasks using AI
        summary = await llm_client.summarize_emails(emails)
        suggestions_raw = await llm_client.extract_task_suggestions(emails)

        # Convert to TaskSuggestion models
        task_suggestions = []
        for s in suggestions_raw:
            task_suggestions.append(TaskSuggestion(
                title=s.get("title", "Untitled Task"),
                description=s.get("description"),
                priority=s.get("priority", "medium"),
                due_date_hint=s.get("due_date_hint"),
                source_email_id=s.get("source_email_id"),
                source_email_subject=s.get("source_email_subject"),
                source_email_sender=s.get("source_email_sender")
            ))

        return StandardResponse(
            status=True,
            data=EmailSummaryResponse(
                email_count=len(emails),
                date_range={
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                summary=summary,
                task_suggestions=task_suggestions
            )
        )
    except Exception as e:
        logger.error(f"AI processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI processing failed: {str(e)}"
        )


@router.post("/add-suggested-tasks", response_model=StandardResponse[AddTasksResponse])
async def add_suggested_tasks(
    request: AddTasksRequest,
    current_user: dict = Depends(get_current_user)
):
    """Add selected task suggestions to the task list."""
    if not request.tasks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No tasks provided"
        )

    added_ids = []
    for task in request.tasks:
        # Map priority string to valid values
        priority_map = {
            "low": "low",
            "medium": "medium",
            "high": "high",
            "urgent": "urgent",
            "critical": "urgent"
        }
        priority = priority_map.get(task.priority.lower(), "medium")

        task_data = {
            "title": task.title,
            "description": task.description or f"Source: {task.source_email_subject or 'Email'}",
            "status": "assigned",
            "priority": priority,
            "project": request.project,
            "source_type": "email",
            "source_id": task.source_email_id,
        }

        # Try to parse due date hint
        if task.due_date_hint and task.due_date_hint.lower() != "none":
            # Keep it in description for now - more sophisticated parsing could be added
            task_data["description"] += f"\nDue date hint: {task.due_date_hint}"

        task_id = task_db.create_from_dict(current_user["id"], task_data)
        if task_id:
            added_ids.append(task_id)

    return StandardResponse(
        status=True,
        data=AddTasksResponse(
            added_count=len(added_ids),
            task_ids=added_ids
        ),
        message=f"Successfully added {len(added_ids)} tasks"
    )


@router.post("/generate-description", response_model=StandardResponse[GenerateDescriptionResponse])
async def generate_task_description(
    request: GenerateDescriptionRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate a good task description using AI based on task title and context."""
    if not request.title or not request.title.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task title is required"
        )

    try:
        result = await llm_client.generate_task_description(
            title=request.title.strip(),
            current_description=request.current_description,
            project=request.project,
        )

        return StandardResponse(
            status=True,
            data=GenerateDescriptionResponse(
                description=result["description"].strip(),
                suggested_title=result.get("suggested_title", "").strip() or None
            )
        )
    except Exception as e:
        logger.error(f"Description generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Description generation failed: {str(e)}"
        )


@router.get("/quick-summary", response_model=StandardResponse[dict])
async def get_quick_summary(
    days: int = Query(7, ge=1, le=30),
    current_user: dict = Depends(get_current_user)
):
    """Get a quick summary of recent emails without task extraction."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    emails = email_cache_db.get_emails_by_date_range(
        user_id=current_user["id"],
        start_date=start_date,
        end_date=end_date,
        limit=50
    )

    if not emails:
        return StandardResponse(
            status=True,
            data={
                "email_count": 0,
                "summary": "No emails found in this period."
            }
        )

    try:
        summary = await llm_client.summarize_emails(emails)
        return StandardResponse(
            status=True,
            data={
                "email_count": len(emails),
                "days": days,
                "summary": summary
            }
        )
    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Summary generation failed: {str(e)}"
        )

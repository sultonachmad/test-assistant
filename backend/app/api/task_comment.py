"""Task comment API routes."""
import logging
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.session import get_current_user
from app.core.llm_client import LLMClient
from app.crud.task_comment import task_comment_db
from app.crud.task import task_db
from app.schemas.response import StandardResponse
from app.schemas.task_comment import (
    TaskComment,
    TaskCommentCreate,
    TaskCommentUpdate,
    CommentType,
    AICommentRequest,
    AICommentResponse,
    TaskSuggestionFromCommentsRequest,
    TaskSuggestionFromCommentsResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class CommentListResponse(BaseModel):
    """Response for listing comments."""
    comments: List[TaskComment]
    counts: dict  # Count by type


class CreateCommentRequest(BaseModel):
    """Request to create a comment."""
    task_id: int
    comment_type: CommentType
    content: str
    estimated_days: Optional[int] = None
    suggested_start_date: Optional[datetime] = None
    suggested_due_date: Optional[datetime] = None


class UpdateCommentRequest(BaseModel):
    """Request to update a comment."""
    content: Optional[str] = None
    estimated_days: Optional[int] = None
    suggested_start_date: Optional[datetime] = None
    suggested_due_date: Optional[datetime] = None


class UpdateTaskFromSolutionRequest(BaseModel):
    """Request to update task dates from solution comment."""
    comment_id: int
    start_date: datetime
    due_date: datetime


@router.get("/{task_id}", response_model=StandardResponse[CommentListResponse])
async def get_task_comments(
    task_id: int,
    comment_type: Optional[CommentType] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get all comments for a task."""
    # Verify task belongs to user
    task = task_db.get_by_id(task_id, current_user["id"])
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    comments = task_comment_db.get_by_task(
        task_id,
        current_user["id"],
        comment_type.value if comment_type else None
    )
    counts = task_comment_db.get_comment_count_by_task(task_id, current_user["id"])

    return StandardResponse(
        status=True,
        data=CommentListResponse(comments=comments, counts=counts)
    )


@router.post("/", response_model=StandardResponse[TaskComment])
async def create_comment(
    request: CreateCommentRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a new comment."""
    # Verify task belongs to user
    task = task_db.get_by_id(request.task_id, current_user["id"])
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    comment = TaskCommentCreate(
        task_id=request.task_id,
        comment_type=request.comment_type,
        content=request.content,
        estimated_days=request.estimated_days,
        suggested_start_date=request.suggested_start_date,
        suggested_due_date=request.suggested_due_date,
        is_ai_generated=False
    )

    created = task_comment_db.create(current_user["id"], comment)
    if not created:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create comment"
        )

    return StandardResponse(
        status=True,
        data=created,
        message="Comment created successfully"
    )


@router.put("/{comment_id}", response_model=StandardResponse[TaskComment])
async def update_comment(
    comment_id: int,
    request: UpdateCommentRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update a comment."""
    existing = task_comment_db.get_by_id(comment_id, current_user["id"])
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )

    update = TaskCommentUpdate(
        content=request.content,
        estimated_days=request.estimated_days,
        suggested_start_date=request.suggested_start_date,
        suggested_due_date=request.suggested_due_date
    )

    updated = task_comment_db.update(comment_id, current_user["id"], update)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update comment"
        )

    return StandardResponse(
        status=True,
        data=updated,
        message="Comment updated successfully"
    )


@router.delete("/{comment_id}", response_model=StandardResponse[dict])
async def delete_comment(
    comment_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Delete a comment."""
    existing = task_comment_db.get_by_id(comment_id, current_user["id"])
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )

    if not task_comment_db.delete(comment_id, current_user["id"]):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete comment"
        )

    return StandardResponse(
        status=True,
        data={"deleted": True},
        message="Comment deleted successfully"
    )


@router.post("/ai-generate", response_model=StandardResponse[AICommentResponse])
async def generate_ai_comment(
    request: AICommentRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate an AI comment for a task."""
    # Get task
    task = task_db.get_by_id(request.task_id, current_user["id"])
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Get selected comments for context
    context_comments = []
    if request.selected_comment_ids:
        context_comments = task_comment_db.get_by_ids(
            request.selected_comment_ids,
            current_user["id"]
        )

    # Generate AI comment
    llm_client = LLMClient()
    result = await llm_client.generate_task_comment(
        task=task,
        comment_type=request.comment_type.value,
        user_prompt=request.prompt,
        context_comments=context_comments
    )

    return StandardResponse(
        status=True,
        data=AICommentResponse(
            content=result["content"],
            estimated_days=result.get("estimated_days"),
            suggested_start_date=result.get("suggested_start_date"),
            suggested_due_date=result.get("suggested_due_date")
        )
    )


@router.post("/ai-generate/save", response_model=StandardResponse[TaskComment])
async def generate_and_save_ai_comment(
    request: AICommentRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate and save an AI comment for a task."""
    # Get task
    task = task_db.get_by_id(request.task_id, current_user["id"])
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Get selected comments for context
    context_comments = []
    if request.selected_comment_ids:
        context_comments = task_comment_db.get_by_ids(
            request.selected_comment_ids,
            current_user["id"]
        )

    # Generate AI comment
    llm_client = LLMClient()
    result = await llm_client.generate_task_comment(
        task=task,
        comment_type=request.comment_type.value,
        user_prompt=request.prompt,
        context_comments=context_comments
    )

    # Save the comment
    comment = TaskCommentCreate(
        task_id=request.task_id,
        comment_type=request.comment_type,
        content=result["content"],
        is_ai_generated=True,
        ai_prompt=request.prompt,
        estimated_days=result.get("estimated_days"),
        suggested_start_date=result.get("suggested_start_date"),
        suggested_due_date=result.get("suggested_due_date")
    )

    created = task_comment_db.create(current_user["id"], comment)
    if not created:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save AI comment"
        )

    return StandardResponse(
        status=True,
        data=created,
        message="AI comment generated and saved"
    )


@router.post("/suggest-tasks", response_model=StandardResponse[TaskSuggestionFromCommentsResponse])
async def suggest_tasks_from_comments(
    request: TaskSuggestionFromCommentsRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate task suggestions from selected comments (like email suggestion)."""
    # Get task
    task = task_db.get_by_id(request.task_id, current_user["id"])
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Get selected comments
    comments = task_comment_db.get_by_ids(
        request.selected_comment_ids,
        current_user["id"]
    )

    if not comments:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid comments selected"
        )

    # Generate task suggestions
    llm_client = LLMClient()
    suggestions = await llm_client.suggest_tasks_from_comments(
        task=task,
        comments=comments,
        user_prompt=request.prompt
    )

    return StandardResponse(
        status=True,
        data=TaskSuggestionFromCommentsResponse(suggestions=suggestions)
    )


@router.post("/update-task-from-solution", response_model=StandardResponse[dict])
async def update_task_from_solution(
    request: UpdateTaskFromSolutionRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update task dates from a solution comment."""
    # Get comment
    comment = task_comment_db.get_by_id(request.comment_id, current_user["id"])
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )

    if comment.comment_type != "solution":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only solution comments can update task dates"
        )

    # Get task
    task = task_db.get_by_id(comment.task_id, current_user["id"])
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Update task with new dates
    update_data = {
        "start_date": request.start_date,
        "due_date": request.due_date
    }

    if task_db.update_from_dict(comment.task_id, current_user["id"], update_data):
        return StandardResponse(
            status=True,
            data={"updated": True},
            message="Task dates updated from solution"
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update task"
        )

"""Reminder API routes."""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.core.session import get_current_user
from app.crud.reminder import reminder_db
from app.schemas.reminder import (
    Reminder, ReminderCreate, ReminderUpdate, ReminderSnooze, ReminderList
)
from app.schemas.response import StandardResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=StandardResponse[ReminderList])
async def get_reminders(
    status_filter: Optional[str] = Query(None, alias="status"),
    upcoming_only: bool = False,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Get all reminders with filters."""
    reminders, total = reminder_db.get_all(
        user_id=current_user["id"],
        status=status_filter,
        upcoming_only=upcoming_only,
        page=page,
        limit=limit
    )

    reminder_list = ReminderList(
        reminders=reminders,
        total=total,
        page=page,
        limit=limit
    )
    return StandardResponse(status=True, data=reminder_list)


@router.post("", response_model=StandardResponse[Reminder])
async def create_reminder(
    reminder: ReminderCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new reminder."""
    new_reminder = reminder_db.create(current_user["id"], reminder)
    if not new_reminder:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create reminder"
        )
    return StandardResponse(status=True, data=new_reminder, message="Reminder created successfully")


@router.get("/{reminder_id}", response_model=StandardResponse[Reminder])
async def get_reminder(reminder_id: int, current_user: dict = Depends(get_current_user)):
    """Get a specific reminder."""
    reminder = reminder_db.get_by_id(reminder_id, current_user["id"])
    if not reminder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found")
    return StandardResponse(status=True, data=reminder)


@router.patch("/{reminder_id}", response_model=StandardResponse[Reminder])
async def update_reminder(
    reminder_id: int,
    reminder: ReminderUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a reminder."""
    existing = reminder_db.get_by_id(reminder_id, current_user["id"])
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found")

    updated_reminder = reminder_db.update(reminder_id, current_user["id"], reminder)
    if not updated_reminder:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update reminder"
        )
    return StandardResponse(status=True, data=updated_reminder, message="Reminder updated successfully")


@router.post("/{reminder_id}/snooze", response_model=StandardResponse[Reminder])
async def snooze_reminder(
    reminder_id: int,
    snooze: ReminderSnooze,
    current_user: dict = Depends(get_current_user)
):
    """Snooze a reminder."""
    existing = reminder_db.get_by_id(reminder_id, current_user["id"])
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found")

    snoozed = reminder_db.snooze(reminder_id, current_user["id"], snooze.snooze_minutes)
    if not snoozed:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to snooze reminder"
        )
    return StandardResponse(status=True, data=snoozed, message=f"Reminder snoozed for {snooze.snooze_minutes} minutes")


@router.delete("/{reminder_id}", response_model=StandardResponse)
async def delete_reminder(reminder_id: int, current_user: dict = Depends(get_current_user)):
    """Delete/cancel a reminder."""
    existing = reminder_db.get_by_id(reminder_id, current_user["id"])
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found")

    if not reminder_db.delete(reminder_id, current_user["id"]):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete reminder"
        )
    return StandardResponse(status=True, message="Reminder deleted successfully")

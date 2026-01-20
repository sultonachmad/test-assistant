"""Notification API routes."""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.core.session import get_current_user
from app.crud.notification import notification_db
from app.schemas.notification import NotificationList
from app.schemas.response import StandardResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=StandardResponse[NotificationList])
async def get_notifications(
    unread_only: bool = False,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Get all notifications."""
    notifications, total, unread_count = notification_db.get_all(
        user_id=current_user["id"],
        unread_only=unread_only,
        page=page,
        limit=limit
    )

    notification_list = NotificationList(
        notifications=notifications,
        unread_count=unread_count,
        total=total
    )
    return StandardResponse(status=True, data=notification_list)


@router.patch("/{notification_id}/read", response_model=StandardResponse)
async def mark_notification_read(
    notification_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Mark a notification as read."""
    if not notification_db.mark_read(notification_id, current_user["id"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return StandardResponse(status=True, message="Notification marked as read")


@router.post("/read-all", response_model=StandardResponse)
async def mark_all_read(current_user: dict = Depends(get_current_user)):
    """Mark all notifications as read."""
    count = notification_db.mark_all_read(current_user["id"])
    return StandardResponse(status=True, message=f"Marked {count} notifications as read")


@router.delete("/{notification_id}", response_model=StandardResponse)
async def delete_notification(
    notification_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Delete a notification."""
    if not notification_db.delete(notification_id, current_user["id"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return StandardResponse(status=True, message="Notification deleted")

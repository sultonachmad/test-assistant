"""User API routes."""
import logging
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.session import get_current_user
from app.crud.user import user_db
from app.schemas.user import User, UserUpdate, UserSettings
from app.schemas.response import StandardResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/me", response_model=StandardResponse[User])
async def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    """Get current user profile."""
    user = user_db.get_by_id(current_user["id"])
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return StandardResponse(status=True, data=user)


@router.patch("/me", response_model=StandardResponse[User])
async def update_user_profile(
    user_update: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update current user profile."""
    user = user_db.update(current_user["id"], user_update)
    if not user:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update user")
    return StandardResponse(status=True, data=user, message="Profile updated successfully")


@router.get("/settings", response_model=StandardResponse[UserSettings])
async def get_user_settings(current_user: dict = Depends(get_current_user)):
    """Get user notification settings."""
    user = user_db.get_by_id(current_user["id"])
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    settings = UserSettings(
        notification_email=user.notification_email,
        notification_calendar=user.notification_calendar,
        notification_inapp=user.notification_inapp,
        timezone=user.timezone
    )
    return StandardResponse(status=True, data=settings)


@router.patch("/settings", response_model=StandardResponse[UserSettings])
async def update_user_settings(
    settings: UserSettings,
    current_user: dict = Depends(get_current_user)
):
    """Update user notification settings."""
    user_update = UserUpdate(
        notification_email=settings.notification_email,
        notification_calendar=settings.notification_calendar,
        notification_inapp=settings.notification_inapp,
        timezone=settings.timezone
    )
    user = user_db.update(current_user["id"], user_update)
    if not user:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update settings")

    return StandardResponse(status=True, data=settings, message="Settings updated successfully")

"""Sync API routes."""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks

from app.core.session import get_current_user
from app.core.sync_worker import run_sync
from app.crud.sync_log import sync_log_db
from app.crud.google_token import google_token_db
from app.schemas.response import StandardResponse, SyncStatus

logger = logging.getLogger(__name__)
router = APIRouter()


async def run_sync_background(user_id: int, sync_type: str):
    """Background task to run sync."""
    try:
        await run_sync(user_id, sync_type)
    except Exception as e:
        logger.error(f"Background sync failed for user {user_id}: {e}")


@router.post("/all", response_model=StandardResponse[SyncStatus])
async def sync_all(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Trigger full sync of all data sources."""
    # Check if Google is connected
    if not google_token_db.is_token_valid(current_user["id"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account not connected. Please connect your Google account first."
        )

    # Run sync in background
    background_tasks.add_task(run_sync_background, current_user["id"], "all")

    return StandardResponse(
        status=True,
        data=SyncStatus(sync_type="all", status="started", items_synced=0),
        message="Sync started in background"
    )


@router.post("/gmail", response_model=StandardResponse[SyncStatus])
async def sync_gmail(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Trigger Gmail sync."""
    if not google_token_db.is_token_valid(current_user["id"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account not connected"
        )

    background_tasks.add_task(run_sync_background, current_user["id"], "gmail")

    return StandardResponse(
        status=True,
        data=SyncStatus(sync_type="gmail", status="started", items_synced=0),
        message="Gmail sync started"
    )


@router.post("/calendar", response_model=StandardResponse[SyncStatus])
async def sync_calendar(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Trigger Calendar sync."""
    if not google_token_db.is_token_valid(current_user["id"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account not connected"
        )

    background_tasks.add_task(run_sync_background, current_user["id"], "calendar")

    return StandardResponse(
        status=True,
        data=SyncStatus(sync_type="calendar", status="started", items_synced=0),
        message="Calendar sync started"
    )


@router.post("/documents", response_model=StandardResponse[SyncStatus])
async def sync_documents(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Trigger Google Docs sync."""
    if not google_token_db.is_token_valid(current_user["id"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account not connected"
        )

    background_tasks.add_task(run_sync_background, current_user["id"], "documents")

    return StandardResponse(
        status=True,
        data=SyncStatus(sync_type="documents", status="started", items_synced=0),
        message="Documents sync started"
    )


@router.get("/status", response_model=StandardResponse[dict])
async def get_sync_status(current_user: dict = Depends(get_current_user)):
    """Get current sync status for all types."""
    status_data = sync_log_db.get_sync_status(current_user["id"])
    return StandardResponse(status=True, data=status_data)


@router.get("/logs", response_model=StandardResponse[list])
async def get_sync_logs(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """Get sync history."""
    logs = sync_log_db.get_sync_history(current_user["id"], limit)
    return StandardResponse(status=True, data=logs)

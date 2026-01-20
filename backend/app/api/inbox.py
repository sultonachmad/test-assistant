"""Inbox API routes for viewing synced emails and chats."""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.core.session import get_current_user
from app.crud.email_cache import email_cache_db
from app.schemas.response import StandardResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/emails", response_model=StandardResponse[dict])
async def get_emails(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    unprocessed_only: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """Get synced emails from cache."""
    emails = email_cache_db.get_emails(
        user_id=current_user["id"],
        limit=limit,
        offset=offset,
        unprocessed_only=unprocessed_only
    )
    total = email_cache_db.get_count(current_user["id"])

    return StandardResponse(
        status=True,
        data={
            "emails": emails,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    )


@router.get("/emails/{gmail_id}", response_model=StandardResponse[dict])
async def get_email_detail(
    gmail_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific email by Gmail ID."""
    email = email_cache_db.get_email_by_gmail_id(current_user["id"], gmail_id)
    if not email:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")

    return StandardResponse(status=True, data=email)


@router.post("/emails/{gmail_id}/mark-processed", response_model=StandardResponse)
async def mark_email_processed(
    gmail_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Mark an email as processed (e.g., after extracting tasks)."""
    if not email_cache_db.mark_processed(current_user["id"], gmail_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")

    return StandardResponse(status=True, message="Email marked as processed")


@router.get("/summary", response_model=StandardResponse[dict])
async def get_inbox_summary(current_user: dict = Depends(get_current_user)):
    """Get inbox summary with counts."""
    email_count = email_cache_db.get_count(current_user["id"])
    recent_emails = email_cache_db.get_emails(current_user["id"], limit=5)

    return StandardResponse(
        status=True,
        data={
            "email_count": email_count,
            "recent_emails": recent_emails,
        }
    )

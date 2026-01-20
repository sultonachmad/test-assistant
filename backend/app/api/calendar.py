"""Calendar API routes for viewing synced calendar events."""
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel

from app.core.session import get_current_user
from app.core.google_api_client import GoogleAPIClient
from app.crud.calendar_cache import calendar_cache_db
from app.crud.google_token import google_token_db
from app.schemas.response import StandardResponse

logger = logging.getLogger(__name__)
router = APIRouter()


class CreateEventRequest(BaseModel):
    """Request body for creating calendar event."""
    summary: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: datetime
    end_time: datetime
    attendees: Optional[list[str]] = None


@router.get("/events", response_model=StandardResponse[dict])
async def get_calendar_events(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(get_current_user)
):
    """Get synced calendar events from cache."""
    events = calendar_cache_db.get_events(
        user_id=current_user["id"],
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )
    total = calendar_cache_db.get_count(current_user["id"])

    return StandardResponse(
        status=True,
        data={
            "events": events,
            "total": total,
        }
    )


@router.get("/today", response_model=StandardResponse[list])
async def get_today_events(current_user: dict = Depends(get_current_user)):
    """Get today's calendar events."""
    events = calendar_cache_db.get_today_events(current_user["id"])
    return StandardResponse(status=True, data=events)


@router.get("/week", response_model=StandardResponse[list])
async def get_week_events(current_user: dict = Depends(get_current_user)):
    """Get this week's calendar events."""
    events = calendar_cache_db.get_week_events(current_user["id"])
    return StandardResponse(status=True, data=events)


@router.get("/events/{event_id}", response_model=StandardResponse[dict])
async def get_event_detail(
    event_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific calendar event."""
    event = calendar_cache_db.get_event_by_id(current_user["id"], event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    return StandardResponse(status=True, data=event)


@router.post("/events", response_model=StandardResponse[dict])
async def create_calendar_event(
    request: CreateEventRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a new calendar event directly in Google Calendar."""
    if not google_token_db.is_token_valid(current_user["id"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account not connected"
        )

    try:
        client = GoogleAPIClient(current_user["id"])
        event = client.create_calendar_event(
            summary=request.summary,
            start_time=request.start_time,
            end_time=request.end_time,
            description=request.description,
            location=request.location,
            attendees=request.attendees
        )

        # Also cache the event locally
        calendar_cache_db.upsert_event(current_user["id"], {
            'event_id': event['id'],
            'calendar_id': 'primary',
            'summary': request.summary,
            'description': request.description,
            'location': request.location,
            'start_time': request.start_time,
            'end_time': request.end_time,
            'attendees': request.attendees or [],
            'is_all_day': False,
            'status': 'confirmed',
        })

        return StandardResponse(
            status=True,
            data=event,
            message="Event created successfully"
        )

    except Exception as e:
        logger.error(f"Failed to create calendar event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create event: {str(e)}"
        )

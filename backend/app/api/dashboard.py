"""Dashboard API routes."""
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends

from app.core.session import get_current_user
from app.crud.task import task_db
from app.crud.reminder import reminder_db
from app.crud.notification import notification_db
from app.crud.sync_log import sync_log_db
from app.schemas.response import StandardResponse, DashboardData

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=StandardResponse[DashboardData])
async def get_dashboard(current_user: dict = Depends(get_current_user)):
    """Get dashboard aggregated data."""
    user_id = current_user["id"]

    # Get task summary
    task_summary = task_db.get_summary(user_id)

    # Get upcoming reminders (next 7 days)
    upcoming_threshold = datetime.utcnow() + timedelta(days=7)
    reminders, _ = reminder_db.get_all(
        user_id=user_id,
        upcoming_only=True,
        page=1,
        limit=5
    )

    # Get recent notifications
    notifications, _, unread_count = notification_db.get_all(
        user_id=user_id,
        page=1,
        limit=5
    )

    # Get today's calendar (placeholder - will be implemented with calendar sync)
    calendar_today = []

    # Get AI suggestions (placeholder)
    ai_suggestions = []

    # Get sync status
    sync_status = sync_log_db.get_sync_status(user_id)

    dashboard = DashboardData(
        task_summary=task_summary,
        upcoming_reminders=[r.model_dump() for r in reminders],
        recent_notifications=[n.model_dump() for n in notifications],
        calendar_today=calendar_today,
        ai_suggestions=ai_suggestions,
        sync_status=sync_status
    )

    return StandardResponse(status=True, data=dashboard)


@router.get("/stats", response_model=StandardResponse[dict])
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    """Get dashboard statistics."""
    user_id = current_user["id"]

    # Task stats
    task_summary = task_db.get_summary(user_id)

    # Get tasks due this week
    this_week = datetime.utcnow() + timedelta(days=7)
    tasks_this_week, _ = task_db.get_all(
        user_id=user_id,
        due_before=this_week,
        page=1,
        limit=100
    )

    # Notification stats
    _, _, unread_notifications = notification_db.get_all(user_id=user_id, page=1, limit=1)

    # Reminder stats
    upcoming_reminders, _ = reminder_db.get_all(user_id=user_id, upcoming_only=True, page=1, limit=1)

    stats = {
        "tasks": {
            "total": task_summary.total,
            "done": task_summary.done,
            "in_progress": task_summary.in_progress,
            "on_hold": task_summary.on_hold,
            "assigned": task_summary.assigned,
            "overdue": task_summary.overdue,
            "due_this_week": len(tasks_this_week)
        },
        "notifications": {
            "unread": unread_notifications
        },
        "reminders": {
            "upcoming": len(upcoming_reminders) if upcoming_reminders else 0
        }
    }

    return StandardResponse(status=True, data=stats)

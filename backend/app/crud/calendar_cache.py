"""Calendar cache CRUD operations."""
import json
import logging
from typing import Optional, List
from datetime import datetime, timedelta

from app.crud.db_connection import db

logger = logging.getLogger(__name__)


class CalendarCacheDB:
    """Calendar cache database operations."""

    def __init__(self):
        self.db = db

    def upsert_event(self, user_id: int, event_data: dict) -> bool:
        """Insert or update a calendar event in cache."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()

                attendees_json = json.dumps(event_data.get('attendees', []))

                # Try to update first
                cursor.execute("""
                    UPDATE calendar_cache SET
                        calendar_id = %s,
                        summary = %s,
                        description = %s,
                        location = %s,
                        start_time = %s,
                        end_time = %s,
                        attendees = %s,
                        is_all_day = %s,
                        status = %s,
                        updated_at = %s
                    WHERE user_id = %s AND event_id = %s
                """, (
                    event_data.get('calendar_id', 'primary'),
                    event_data.get('summary'),
                    event_data.get('description'),
                    event_data.get('location'),
                    event_data.get('start_time'),
                    event_data.get('end_time'),
                    attendees_json,
                    event_data.get('is_all_day', False),
                    event_data.get('status', 'confirmed'),
                    datetime.utcnow(),
                    user_id,
                    event_data['event_id']
                ))

                if cursor.rowcount == 0:
                    # Insert new
                    cursor.execute("""
                        INSERT INTO calendar_cache
                        (user_id, event_id, calendar_id, summary, description, location,
                         start_time, end_time, attendees, is_all_day, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        user_id,
                        event_data['event_id'],
                        event_data.get('calendar_id', 'primary'),
                        event_data.get('summary'),
                        event_data.get('description'),
                        event_data.get('location'),
                        event_data.get('start_time'),
                        event_data.get('end_time'),
                        attendees_json,
                        event_data.get('is_all_day', False),
                        event_data.get('status', 'confirmed')
                    ))

                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error upserting calendar event: {e}")
            return False

    def bulk_upsert(self, user_id: int, events: List[dict]) -> int:
        """Bulk insert/update calendar events."""
        count = 0
        for event in events:
            if self.upsert_event(user_id, event):
                count += 1
        return count

    def get_events(
        self,
        user_id: int,
        start_date: datetime = None,
        end_date: datetime = None,
        limit: int = 100
    ) -> List[dict]:
        """Get cached calendar events for a user."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()

                where_clauses = ["user_id = %s"]
                params = [user_id]

                if start_date:
                    where_clauses.append("start_time >= %s")
                    params.append(start_date)
                if end_date:
                    where_clauses.append("start_time <= %s")
                    params.append(end_date)

                where_sql = " AND ".join(where_clauses)

                cursor.execute(f"""
                    SELECT * FROM calendar_cache
                    WHERE {where_sql}
                    ORDER BY start_time ASC
                    LIMIT %s
                """, (*params, limit))

                rows = cursor.fetchall()
                events = []
                for row in rows:
                    event = dict(row)
                    if event.get('attendees') and isinstance(event['attendees'], str):
                        event['attendees'] = json.loads(event['attendees'])
                    events.append(event)
                return events
        except Exception as e:
            logger.error(f"Error getting calendar events: {e}")
            return []

    def get_today_events(self, user_id: int) -> List[dict]:
        """Get today's events for a user."""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        return self.get_events(user_id, start_date=today, end_date=tomorrow)

    def get_week_events(self, user_id: int) -> List[dict]:
        """Get this week's events for a user."""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = today + timedelta(days=7)
        return self.get_events(user_id, start_date=today, end_date=week_end)

    def get_event_by_id(self, user_id: int, event_id: str) -> Optional[dict]:
        """Get a specific event by ID."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM calendar_cache WHERE user_id = %s AND event_id = %s",
                    (user_id, event_id)
                )
                row = cursor.fetchone()
                if row:
                    event = dict(row)
                    if event.get('attendees') and isinstance(event['attendees'], str):
                        event['attendees'] = json.loads(event['attendees'])
                    return event
                return None
        except Exception as e:
            logger.error(f"Error getting calendar event: {e}")
            return None

    def get_count(self, user_id: int) -> int:
        """Get total event count for user."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) as count FROM calendar_cache WHERE user_id = %s",
                    (user_id,)
                )
                return cursor.fetchone()['count']
        except Exception as e:
            logger.error(f"Error getting event count: {e}")
            return 0

    def delete_past_events(self, user_id: int, days_ago: int = 7) -> int:
        """Delete events older than specified days."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM calendar_cache
                    WHERE user_id = %s AND end_time < NOW() - INTERVAL '%s days'
                """, (user_id, days_ago))
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Error deleting past events: {e}")
            return 0


calendar_cache_db = CalendarCacheDB()

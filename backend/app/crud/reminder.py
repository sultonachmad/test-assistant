"""Reminder CRUD operations."""
import json
import logging
from typing import Optional, List
from datetime import datetime, timedelta

from app.crud.db_connection import db
from app.schemas.reminder import Reminder, ReminderCreate, ReminderUpdate, ReminderStatus

logger = logging.getLogger(__name__)


class ReminderDB:
    """Reminder database operations."""

    def __init__(self):
        self.db = db

    def _row_to_reminder(self, row: dict) -> Reminder:
        """Convert database row to Reminder schema."""
        data = dict(row)
        if data.get('remind_via') and isinstance(data['remind_via'], str):
            try:
                data['remind_via'] = json.loads(data['remind_via'])
            except:
                data['remind_via'] = ['inapp']
        return Reminder(**data)

    def get_by_id(self, reminder_id: int, user_id: int) -> Optional[Reminder]:
        """Get reminder by ID."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM reminders WHERE id = %s AND user_id = %s",
                    (reminder_id, user_id)
                )
                row = cursor.fetchone()
                if row:
                    return self._row_to_reminder(row)
                return None
        except Exception as e:
            logger.error(f"Error getting reminder: {e}")
            return None

    def get_all(
        self,
        user_id: int,
        status: Optional[str] = None,
        upcoming_only: bool = False,
        page: int = 1,
        limit: int = 20
    ) -> tuple[List[Reminder], int]:
        """Get all reminders with filters."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()

                where_clauses = ["user_id = %s"]
                values = [user_id]

                if status:
                    where_clauses.append("status = %s")
                    values.append(status)
                if upcoming_only:
                    where_clauses.append("remind_at >= %s")
                    values.append(datetime.utcnow())

                where_sql = " AND ".join(where_clauses)

                # Get total count
                cursor.execute(f"SELECT COUNT(*) as count FROM reminders WHERE {where_sql}", tuple(values))
                total = cursor.fetchone()['count']

                # Get paginated results
                offset = (page - 1) * limit
                values.extend([limit, offset])
                cursor.execute(f"""
                    SELECT * FROM reminders WHERE {where_sql}
                    ORDER BY remind_at ASC
                    LIMIT %s OFFSET %s
                """, tuple(values))

                reminders = [self._row_to_reminder(row) for row in cursor.fetchall()]
                return reminders, total
        except Exception as e:
            logger.error(f"Error getting reminders: {e}")
            return [], 0

    def get_due_reminders(self, threshold: datetime) -> List[Reminder]:
        """Get reminders that are due within threshold."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM reminders
                    WHERE status = 'pending' AND remind_at <= %s
                    ORDER BY remind_at ASC
                """, (threshold,))
                return [self._row_to_reminder(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting due reminders: {e}")
            return []

    def create(self, user_id: int, reminder: ReminderCreate) -> Optional[Reminder]:
        """Create a new reminder."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                remind_via_json = json.dumps([v.value for v in reminder.remind_via])
                cursor.execute("""
                    INSERT INTO reminders (user_id, task_id, title, description, remind_at,
                                          remind_via, is_recurring, recurrence_rule)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                """, (
                    user_id, reminder.task_id, reminder.title, reminder.description,
                    reminder.remind_at, remind_via_json, reminder.is_recurring, reminder.recurrence_rule
                ))
                row = cursor.fetchone()
                conn.commit()
                if row:
                    return self._row_to_reminder(row)
                return None
        except Exception as e:
            logger.error(f"Error creating reminder: {e}")
            return None

    def update(self, reminder_id: int, user_id: int, reminder: ReminderUpdate) -> Optional[Reminder]:
        """Update reminder."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                updates = []
                values = []

                if reminder.title is not None:
                    updates.append("title = %s")
                    values.append(reminder.title)
                if reminder.description is not None:
                    updates.append("description = %s")
                    values.append(reminder.description)
                if reminder.remind_at is not None:
                    updates.append("remind_at = %s")
                    values.append(reminder.remind_at)
                if reminder.remind_via is not None:
                    updates.append("remind_via = %s")
                    values.append(json.dumps([v.value for v in reminder.remind_via]))
                if reminder.is_recurring is not None:
                    updates.append("is_recurring = %s")
                    values.append(reminder.is_recurring)
                if reminder.recurrence_rule is not None:
                    updates.append("recurrence_rule = %s")
                    values.append(reminder.recurrence_rule)

                if not updates:
                    return self.get_by_id(reminder_id, user_id)

                updates.append("updated_at = %s")
                values.append(datetime.utcnow())
                values.extend([reminder_id, user_id])

                cursor.execute(f"""
                    UPDATE reminders SET {', '.join(updates)}
                    WHERE id = %s AND user_id = %s RETURNING *
                """, tuple(values))
                row = cursor.fetchone()
                conn.commit()
                if row:
                    return self._row_to_reminder(row)
                return None
        except Exception as e:
            logger.error(f"Error updating reminder: {e}")
            return None

    def mark_sent(self, reminder_id: int) -> bool:
        """Mark reminder as sent."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE reminders SET status = 'sent', updated_at = %s
                    WHERE id = %s
                """, (datetime.utcnow(), reminder_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error marking reminder as sent: {e}")
            return False

    def snooze(self, reminder_id: int, user_id: int, minutes: int = 15) -> Optional[Reminder]:
        """Snooze reminder."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                new_time = datetime.utcnow() + timedelta(minutes=minutes)
                cursor.execute("""
                    UPDATE reminders SET remind_at = %s, status = 'pending', updated_at = %s
                    WHERE id = %s AND user_id = %s RETURNING *
                """, (new_time, datetime.utcnow(), reminder_id, user_id))
                row = cursor.fetchone()
                conn.commit()
                if row:
                    return self._row_to_reminder(row)
                return None
        except Exception as e:
            logger.error(f"Error snoozing reminder: {e}")
            return None

    def cancel(self, reminder_id: int, user_id: int) -> bool:
        """Cancel reminder."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE reminders SET status = 'cancelled', updated_at = %s
                    WHERE id = %s AND user_id = %s
                """, (datetime.utcnow(), reminder_id, user_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error cancelling reminder: {e}")
            return False

    def delete(self, reminder_id: int, user_id: int) -> bool:
        """Delete reminder."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM reminders WHERE id = %s AND user_id = %s",
                    (reminder_id, user_id)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting reminder: {e}")
            return False


reminder_db = ReminderDB()

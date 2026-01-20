"""Notification CRUD operations."""
import logging
from typing import Optional, List
from datetime import datetime

from app.crud.db_connection import db
from app.schemas.notification import Notification, NotificationCreate

logger = logging.getLogger(__name__)


class NotificationDB:
    """Notification database operations."""

    def __init__(self):
        self.db = db

    def get_by_id(self, notification_id: int, user_id: int) -> Optional[Notification]:
        """Get notification by ID."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM notifications WHERE id = %s AND user_id = %s",
                    (notification_id, user_id)
                )
                row = cursor.fetchone()
                if row:
                    return Notification(**dict(row))
                return None
        except Exception as e:
            logger.error(f"Error getting notification: {e}")
            return None

    def get_all(
        self,
        user_id: int,
        unread_only: bool = False,
        page: int = 1,
        limit: int = 20
    ) -> tuple[List[Notification], int, int]:
        """Get all notifications with unread count."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()

                where_clauses = ["user_id = %s"]
                values = [user_id]

                if unread_only:
                    where_clauses.append("is_read = FALSE")

                where_sql = " AND ".join(where_clauses)

                # Get total count
                cursor.execute(f"SELECT COUNT(*) as count FROM notifications WHERE {where_sql}", tuple(values))
                total = cursor.fetchone()['count']

                # Get unread count
                cursor.execute(
                    "SELECT COUNT(*) as count FROM notifications WHERE user_id = %s AND is_read = FALSE",
                    (user_id,)
                )
                unread_count = cursor.fetchone()['count']

                # Get paginated results
                offset = (page - 1) * limit
                values.extend([limit, offset])
                cursor.execute(f"""
                    SELECT * FROM notifications WHERE {where_sql}
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """, tuple(values))

                notifications = [Notification(**dict(row)) for row in cursor.fetchall()]
                return notifications, total, unread_count
        except Exception as e:
            logger.error(f"Error getting notifications: {e}")
            return [], 0, 0

    def create(self, user_id: int, notification: NotificationCreate) -> Optional[Notification]:
        """Create a new notification."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO notifications (user_id, type, title, message, link)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING *
                """, (
                    user_id, notification.type.value, notification.title,
                    notification.message, notification.link
                ))
                row = cursor.fetchone()
                conn.commit()
                if row:
                    return Notification(**dict(row))
                return None
        except Exception as e:
            logger.error(f"Error creating notification: {e}")
            return None

    def mark_read(self, notification_id: int, user_id: int) -> bool:
        """Mark notification as read."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE notifications SET is_read = TRUE
                    WHERE id = %s AND user_id = %s
                """, (notification_id, user_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error marking notification as read: {e}")
            return False

    def mark_all_read(self, user_id: int) -> int:
        """Mark all notifications as read."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE notifications SET is_read = TRUE
                    WHERE user_id = %s AND is_read = FALSE
                """, (user_id,))
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Error marking all notifications as read: {e}")
            return 0

    def delete(self, notification_id: int, user_id: int) -> bool:
        """Delete notification."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM notifications WHERE id = %s AND user_id = %s",
                    (notification_id, user_id)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting notification: {e}")
            return False

    def delete_old(self, user_id: int, days: int = 30) -> int:
        """Delete notifications older than specified days."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM notifications
                    WHERE user_id = %s AND created_at < NOW() - INTERVAL '%s days'
                """, (user_id, days))
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Error deleting old notifications: {e}")
            return 0


notification_db = NotificationDB()

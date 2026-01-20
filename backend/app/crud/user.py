"""User CRUD operations."""
import logging
from typing import Optional, List
from datetime import datetime

from app.crud.db_connection import db
from app.schemas.user import User, UserCreate, UserUpdate

logger = logging.getLogger(__name__)


class UserDB:
    """User database operations."""

    def __init__(self):
        self.db = db

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM users WHERE id = %s",
                    (user_id,)
                )
                row = cursor.fetchone()
                if row:
                    return User(**dict(row))
                return None
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None

    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM users WHERE email = %s",
                    (email,)
                )
                row = cursor.fetchone()
                if row:
                    return User(**dict(row))
                return None
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None

    def create(self, user: UserCreate) -> Optional[User]:
        """Create a new user."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (email, name, image, timezone,
                                       notification_email, notification_calendar, notification_inapp)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                """, (
                    user.email, user.name, user.image, user.timezone,
                    user.notification_email, user.notification_calendar, user.notification_inapp
                ))
                row = cursor.fetchone()
                conn.commit()
                if row:
                    return User(**dict(row))
                return None
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None

    def update(self, user_id: int, user: UserUpdate) -> Optional[User]:
        """Update user."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                updates = []
                values = []

                if user.name is not None:
                    updates.append("name = %s")
                    values.append(user.name)
                if user.image is not None:
                    updates.append("image = %s")
                    values.append(user.image)
                if user.timezone is not None:
                    updates.append("timezone = %s")
                    values.append(user.timezone)
                if user.notification_email is not None:
                    updates.append("notification_email = %s")
                    values.append(user.notification_email)
                if user.notification_calendar is not None:
                    updates.append("notification_calendar = %s")
                    values.append(user.notification_calendar)
                if user.notification_inapp is not None:
                    updates.append("notification_inapp = %s")
                    values.append(user.notification_inapp)

                if not updates:
                    return self.get_by_id(user_id)

                updates.append("updated_at = %s")
                values.append(datetime.utcnow())
                values.append(user_id)

                cursor.execute(f"""
                    UPDATE users SET {', '.join(updates)}
                    WHERE id = %s RETURNING *
                """, tuple(values))
                row = cursor.fetchone()
                conn.commit()
                if row:
                    return User(**dict(row))
                return None
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return None

    def get_or_create(self, email: str, name: Optional[str] = None, image: Optional[str] = None) -> Optional[User]:
        """Get existing user or create new one."""
        user = self.get_by_email(email)
        if user:
            return user
        return self.create(UserCreate(email=email, name=name, image=image))

    def delete(self, user_id: int) -> bool:
        """Delete user."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return False


user_db = UserDB()

"""Taiga CRUD operations for managing Taiga sync configuration and cards."""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.crud.db_connection import db

logger = logging.getLogger(__name__)


class TaigaConfigDB:
    """Taiga configuration database operations."""

    def __init__(self):
        self.db = db

    def get_config(self, user_id: int) -> Optional[Dict]:
        """Get Taiga configuration for a user."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM taiga_config WHERE user_id = %s",
                    (user_id,)
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting Taiga config: {e}")
            return None

    def upsert_config(
        self,
        user_id: int,
        taiga_url: str,
        auth_token: str,
        project_id: int,
        is_active: bool = True,
    ) -> bool:
        """Create or update Taiga configuration."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO taiga_config (user_id, taiga_url, auth_token, project_id, is_active)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET
                        taiga_url = EXCLUDED.taiga_url,
                        auth_token = EXCLUDED.auth_token,
                        project_id = EXCLUDED.project_id,
                        is_active = EXCLUDED.is_active,
                        updated_at = CURRENT_TIMESTAMP
                """, (user_id, taiga_url, auth_token, project_id, is_active))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error upserting Taiga config: {e}")
            return False

    def update_last_sync(self, user_id: int) -> bool:
        """Update last sync timestamp."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE taiga_config SET last_sync = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                """, (user_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating last sync: {e}")
            return False


class TaigaCardsDB:
    """Taiga cards (linked tasks) database operations."""

    def __init__(self):
        self.db = db

    def get_card_by_task_id(self, user_id: int, task_id: int) -> Optional[Dict]:
        """Get Taiga card linked to a task."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM taiga_cards WHERE user_id = %s AND task_id = %s",
                    (user_id, task_id)
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting Taiga card: {e}")
            return None

    def get_card_by_taiga_id(self, user_id: int, card_id: int, card_type: str = "userstory") -> Optional[Dict]:
        """Get Taiga card by Taiga card ID."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM taiga_cards WHERE user_id = %s AND card_id = %s AND card_type = %s",
                    (user_id, card_id, card_type)
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting Taiga card by ID: {e}")
            return None

    def get_all_linked_cards(self, user_id: int) -> List[Dict]:
        """Get all Taiga cards linked to tasks for a user."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT tc.*, t.title as task_title, t.status as task_status
                    FROM taiga_cards tc
                    JOIN tasks t ON tc.task_id = t.id
                    WHERE tc.user_id = %s AND tc.task_id IS NOT NULL
                    ORDER BY tc.updated_at DESC
                """, (user_id,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting linked cards: {e}")
            return []

    def get_linked_cards_for_update(self, user_id: int) -> List[Dict]:
        """
        Get Taiga cards linked to tasks that can be updated from Taiga.
        Only returns cards linked to tasks with status 'assigned' or 'in_progress'.
        Tasks with status 'done' or 'on_hold' are excluded from Taiga updates.
        """
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT tc.*, t.title as task_title, t.status as task_status
                    FROM taiga_cards tc
                    JOIN tasks t ON tc.task_id = t.id
                    WHERE tc.user_id = %s
                      AND tc.task_id IS NOT NULL
                      AND t.status IN ('assigned', 'in_progress')
                    ORDER BY tc.updated_at DESC
                """, (user_id,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting linked cards for update: {e}")
            return []

    def create_card(
        self,
        user_id: int,
        card_id: int,
        card_type: str,
        subject: str,
        status: str,
        task_id: int,
        due_date: Optional[datetime] = None,
    ) -> Optional[int]:
        """Create a new Taiga card record."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO taiga_cards
                    (user_id, card_id, card_type, subject, status, task_id, due_date, last_checked)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    RETURNING id
                """, (user_id, card_id, card_type, subject, status, task_id, due_date))
                conn.commit()
                return cursor.fetchone()['id']
        except Exception as e:
            logger.error(f"Error creating Taiga card: {e}")
            return None

    def update_card_status(self, card_id: int, user_id: int, status: str) -> bool:
        """Update Taiga card status."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE taiga_cards SET
                        status = %s,
                        last_checked = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND user_id = %s
                """, (status, card_id, user_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating card status: {e}")
            return False

    def link_task_to_card(self, card_db_id: int, user_id: int, task_id: int) -> bool:
        """Link a task to an existing Taiga card."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE taiga_cards SET task_id = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND user_id = %s
                """, (task_id, card_db_id, user_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error linking task to card: {e}")
            return False

    def delete_card(self, card_db_id: int, user_id: int) -> bool:
        """Delete a Taiga card record."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM taiga_cards WHERE id = %s AND user_id = %s",
                    (card_db_id, user_id)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting card: {e}")
            return False


# Singleton instances
taiga_config_db = TaigaConfigDB()
taiga_cards_db = TaigaCardsDB()

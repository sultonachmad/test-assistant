"""Sync log CRUD operations."""
import logging
from typing import Optional, List
from datetime import datetime

from app.crud.db_connection import db

logger = logging.getLogger(__name__)


class SyncLogDB:
    """Sync log database operations."""

    def __init__(self):
        self.db = db

    def start_sync(self, user_id: int, sync_type: str) -> Optional[int]:
        """Start a new sync and return the log ID."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO sync_logs (user_id, sync_type, status)
                    VALUES (%s, %s, 'started')
                    RETURNING id
                """, (user_id, sync_type))
                row = cursor.fetchone()
                conn.commit()
                return row['id'] if row else None
        except Exception as e:
            logger.error(f"Error starting sync log: {e}")
            return None

    def complete_sync(self, log_id: int, items_synced: int = 0) -> bool:
        """Mark sync as completed."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE sync_logs
                    SET status = 'completed', items_synced = %s, completed_at = %s
                    WHERE id = %s
                """, (items_synced, datetime.utcnow(), log_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error completing sync log: {e}")
            return False

    def fail_sync(self, log_id: int, error_message: str) -> bool:
        """Mark sync as failed."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE sync_logs
                    SET status = 'failed', error_message = %s, completed_at = %s
                    WHERE id = %s
                """, (error_message, datetime.utcnow(), log_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error failing sync log: {e}")
            return False

    def get_latest_sync(self, user_id: int, sync_type: Optional[str] = None) -> Optional[dict]:
        """Get the latest sync log for a user."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                if sync_type:
                    cursor.execute("""
                        SELECT * FROM sync_logs
                        WHERE user_id = %s AND sync_type = %s
                        ORDER BY started_at DESC LIMIT 1
                    """, (user_id, sync_type))
                else:
                    cursor.execute("""
                        SELECT * FROM sync_logs
                        WHERE user_id = %s
                        ORDER BY started_at DESC LIMIT 1
                    """, (user_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting latest sync: {e}")
            return None

    def get_sync_history(self, user_id: int, limit: int = 10) -> List[dict]:
        """Get sync history for a user."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM sync_logs
                    WHERE user_id = %s
                    ORDER BY started_at DESC
                    LIMIT %s
                """, (user_id, limit))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting sync history: {e}")
            return []

    def get_sync_status(self, user_id: int) -> dict:
        """Get current sync status for all types."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                sync_types = ['gmail', 'calendar', 'chat', 'documents', 'all']
                status = {}

                for sync_type in sync_types:
                    cursor.execute("""
                        SELECT status, items_synced, started_at, completed_at, error_message
                        FROM sync_logs
                        WHERE user_id = %s AND sync_type = %s
                        ORDER BY started_at DESC LIMIT 1
                    """, (user_id, sync_type))
                    row = cursor.fetchone()
                    if row:
                        status[sync_type] = {
                            'status': row['status'],
                            'items_synced': row['items_synced'],
                            'last_sync': row['completed_at'].isoformat() if row['completed_at'] else None,
                            'error': row['error_message']
                        }
                    else:
                        status[sync_type] = {
                            'status': 'never',
                            'items_synced': 0,
                            'last_sync': None,
                            'error': None
                        }

                return status
        except Exception as e:
            logger.error(f"Error getting sync status: {e}")
            return {}


sync_log_db = SyncLogDB()

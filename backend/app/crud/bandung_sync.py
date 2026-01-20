"""Bandung Resource Sync CRUD operations."""
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.crud.db_connection import db

logger = logging.getLogger(__name__)


class BandungSyncDB:
    """Bandung Resource sync configuration database operations."""

    def __init__(self):
        self.db = db
        self._ensure_table()

    def _ensure_table(self):
        """Ensure the bandung_sync_configs table exists."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS bandung_sync_configs (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        spreadsheet_id VARCHAR(255) NOT NULL,
                        spreadsheet_name VARCHAR(255),
                        spreadsheet_url TEXT,
                        column_mapping JSONB NOT NULL,
                        assignee_sheet_mapping JSONB NOT NULL,
                        is_active BOOLEAN DEFAULT TRUE,
                        last_sync TIMESTAMP,
                        last_sync_count INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, spreadsheet_id)
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Error creating bandung_sync_configs table: {e}")

    def get_config(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get the Bandung sync configuration for a user."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM bandung_sync_configs WHERE user_id = %s AND is_active = TRUE",
                    (user_id,)
                )
                row = cursor.fetchone()
                if row:
                    config = dict(row)
                    if config.get('column_mapping'):
                        config['column_mapping'] = json.loads(config['column_mapping']) if isinstance(config['column_mapping'], str) else config['column_mapping']
                    if config.get('assignee_sheet_mapping'):
                        config['assignee_sheet_mapping'] = json.loads(config['assignee_sheet_mapping']) if isinstance(config['assignee_sheet_mapping'], str) else config['assignee_sheet_mapping']
                    return config
                return None
        except Exception as e:
            logger.error(f"Error getting Bandung sync config: {e}")
            return None

    def get_config_by_id(self, config_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific Bandung sync configuration."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM bandung_sync_configs WHERE id = %s AND user_id = %s",
                    (config_id, user_id)
                )
                row = cursor.fetchone()
                if row:
                    config = dict(row)
                    if config.get('column_mapping'):
                        config['column_mapping'] = json.loads(config['column_mapping']) if isinstance(config['column_mapping'], str) else config['column_mapping']
                    if config.get('assignee_sheet_mapping'):
                        config['assignee_sheet_mapping'] = json.loads(config['assignee_sheet_mapping']) if isinstance(config['assignee_sheet_mapping'], str) else config['assignee_sheet_mapping']
                    return config
                return None
        except Exception as e:
            logger.error(f"Error getting Bandung sync config by id: {e}")
            return None

    def create_config(
        self,
        user_id: int,
        spreadsheet_id: str,
        spreadsheet_name: str,
        spreadsheet_url: str,
        column_mapping: Dict[str, str],
        assignee_sheet_mapping: Dict[str, str]
    ) -> Optional[int]:
        """Create or update Bandung sync configuration."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO bandung_sync_configs
                    (user_id, spreadsheet_id, spreadsheet_name, spreadsheet_url,
                     column_mapping, assignee_sheet_mapping)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, spreadsheet_id)
                    DO UPDATE SET
                        spreadsheet_name = EXCLUDED.spreadsheet_name,
                        spreadsheet_url = EXCLUDED.spreadsheet_url,
                        column_mapping = EXCLUDED.column_mapping,
                        assignee_sheet_mapping = EXCLUDED.assignee_sheet_mapping,
                        is_active = TRUE,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING id
                """, (
                    user_id, spreadsheet_id, spreadsheet_name, spreadsheet_url,
                    json.dumps(column_mapping), json.dumps(assignee_sheet_mapping)
                ))
                result = cursor.fetchone()
                conn.commit()
                return result['id'] if result else None
        except Exception as e:
            logger.error(f"Error creating Bandung sync config: {e}")
            return None

    def update_config(
        self,
        config_id: int,
        user_id: int,
        column_mapping: Optional[Dict[str, str]] = None,
        assignee_sheet_mapping: Optional[Dict[str, str]] = None,
        is_active: Optional[bool] = None
    ) -> bool:
        """Update Bandung sync configuration."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()

                updates = []
                params = []

                if column_mapping is not None:
                    updates.append("column_mapping = %s")
                    params.append(json.dumps(column_mapping))
                if assignee_sheet_mapping is not None:
                    updates.append("assignee_sheet_mapping = %s")
                    params.append(json.dumps(assignee_sheet_mapping))
                if is_active is not None:
                    updates.append("is_active = %s")
                    params.append(is_active)

                if not updates:
                    return True

                updates.append("updated_at = CURRENT_TIMESTAMP")
                params.extend([config_id, user_id])

                cursor.execute(f"""
                    UPDATE bandung_sync_configs
                    SET {', '.join(updates)}
                    WHERE id = %s AND user_id = %s
                """, params)
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating Bandung sync config: {e}")
            return False

    def update_sync_status(self, config_id: int, synced_count: int) -> bool:
        """Update the last sync timestamp and count."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE bandung_sync_configs
                    SET last_sync = CURRENT_TIMESTAMP,
                        last_sync_count = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (synced_count, config_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating sync status: {e}")
            return False

    def delete_config(self, config_id: int, user_id: int) -> bool:
        """Delete Bandung sync configuration."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM bandung_sync_configs WHERE id = %s AND user_id = %s",
                    (config_id, user_id)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting Bandung sync config: {e}")
            return False


bandung_sync_db = BandungSyncDB()

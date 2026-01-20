"""Sheet sync CRUD operations."""
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.crud.db_connection import db

logger = logging.getLogger(__name__)


class SheetSyncDB:
    """Sheet sync configuration database operations."""

    def __init__(self):
        self.db = db

    def get_all_configs(self, user_id: int, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all sheet sync configurations for a user."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                query = "SELECT * FROM sheet_sync_configs WHERE user_id = %s"
                if active_only:
                    query += " AND is_active = TRUE"
                query += " ORDER BY created_at DESC"
                cursor.execute(query, (user_id,))
                rows = cursor.fetchall()

                configs = []
                for row in rows:
                    config = dict(row)
                    if config.get('field_mapping'):
                        config['field_mapping'] = json.loads(config['field_mapping'])
                    configs.append(config)
                return configs
        except Exception as e:
            logger.error(f"Error getting sheet sync configs: {e}")
            return []

    def get_config_by_id(self, config_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific sheet sync configuration."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM sheet_sync_configs WHERE id = %s AND user_id = %s",
                    (config_id, user_id)
                )
                row = cursor.fetchone()
                if row:
                    config = dict(row)
                    if config.get('field_mapping'):
                        config['field_mapping'] = json.loads(config['field_mapping'])
                    return config
                return None
        except Exception as e:
            logger.error(f"Error getting sheet sync config: {e}")
            return None

    def create_config(
        self,
        user_id: int,
        spreadsheet_id: str,
        spreadsheet_name: str,
        spreadsheet_url: str,
        sheet_name: str,
        field_mapping: Dict[str, str],
        auto_sync: bool = True,
        sync_interval_minutes: int = 15
    ) -> Optional[int]:
        """Create a new sheet sync configuration."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO sheet_sync_configs
                    (user_id, spreadsheet_id, spreadsheet_name, spreadsheet_url, sheet_name,
                     field_mapping, auto_sync, sync_interval_minutes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, spreadsheet_id, sheet_name)
                    DO UPDATE SET
                        spreadsheet_name = EXCLUDED.spreadsheet_name,
                        spreadsheet_url = EXCLUDED.spreadsheet_url,
                        field_mapping = EXCLUDED.field_mapping,
                        auto_sync = EXCLUDED.auto_sync,
                        sync_interval_minutes = EXCLUDED.sync_interval_minutes,
                        is_active = TRUE,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING id
                """, (
                    user_id, spreadsheet_id, spreadsheet_name, spreadsheet_url,
                    sheet_name, json.dumps(field_mapping), auto_sync, sync_interval_minutes
                ))
                result = cursor.fetchone()
                conn.commit()
                return result['id'] if result else None
        except Exception as e:
            logger.error(f"Error creating sheet sync config: {e}")
            return None

    def update_config(
        self,
        config_id: int,
        user_id: int,
        field_mapping: Optional[Dict[str, str]] = None,
        auto_sync: Optional[bool] = None,
        sync_interval_minutes: Optional[int] = None
    ) -> bool:
        """Update a sheet sync configuration."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()

                updates = []
                params = []

                if field_mapping is not None:
                    updates.append("field_mapping = %s")
                    params.append(json.dumps(field_mapping))
                if auto_sync is not None:
                    updates.append("auto_sync = %s")
                    params.append(auto_sync)
                if sync_interval_minutes is not None:
                    updates.append("sync_interval_minutes = %s")
                    params.append(sync_interval_minutes)

                if not updates:
                    return True

                updates.append("updated_at = CURRENT_TIMESTAMP")
                params.extend([config_id, user_id])

                cursor.execute(f"""
                    UPDATE sheet_sync_configs
                    SET {', '.join(updates)}
                    WHERE id = %s AND user_id = %s
                """, params)
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating sheet sync config: {e}")
            return False

    def update_sync_status(
        self,
        config_id: int,
        items_synced: int
    ) -> bool:
        """Update the last sync time and count."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE sheet_sync_configs
                    SET last_sync = CURRENT_TIMESTAMP,
                        last_sync_count = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (items_synced, config_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating sync status: {e}")
            return False

    def deactivate_config(self, config_id: int, user_id: int) -> bool:
        """Deactivate (soft delete) a sheet sync configuration."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE sheet_sync_configs
                    SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND user_id = %s
                """, (config_id, user_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deactivating sheet sync config: {e}")
            return False

    def delete_config(self, config_id: int, user_id: int) -> bool:
        """Hard delete a sheet sync configuration."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM sheet_sync_configs WHERE id = %s AND user_id = %s",
                    (config_id, user_id)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting sheet sync config: {e}")
            return False

    def get_configs_due_for_sync(self) -> List[Dict[str, Any]]:
        """Get all configurations that are due for auto-sync."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM sheet_sync_configs
                    WHERE is_active = TRUE
                    AND auto_sync = TRUE
                    AND (
                        last_sync IS NULL
                        OR last_sync < NOW() - (sync_interval_minutes || ' minutes')::INTERVAL
                    )
                """)
                rows = cursor.fetchall()

                configs = []
                for row in rows:
                    config = dict(row)
                    if config.get('field_mapping'):
                        config['field_mapping'] = json.loads(config['field_mapping'])
                    configs.append(config)
                return configs
        except Exception as e:
            logger.error(f"Error getting configs due for sync: {e}")
            return []


sheet_sync_db = SheetSyncDB()

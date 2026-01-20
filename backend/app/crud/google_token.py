"""Google token CRUD operations."""
import json
import logging
from typing import Optional
from datetime import datetime

from app.crud.db_connection import db
from app.schemas.google import GoogleToken

logger = logging.getLogger(__name__)


class GoogleTokenDB:
    """Google token database operations."""

    def __init__(self):
        self.db = db

    def get_token(self, user_id: int) -> Optional[GoogleToken]:
        """Get Google token for user."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM google_tokens WHERE user_id = %s",
                    (user_id,)
                )
                row = cursor.fetchone()
                if row:
                    data = dict(row)
                    if isinstance(data['scopes'], str):
                        data['scopes'] = json.loads(data['scopes'])
                    return GoogleToken(**data)
                return None
        except Exception as e:
            logger.error(f"Error getting Google token: {e}")
            return None

    def save_token(
        self,
        user_id: int,
        access_token: str,
        refresh_token: str,
        token_expiry: datetime,
        scopes: list
    ) -> bool:
        """Save or update Google token."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                scopes_json = json.dumps(scopes)

                # Try update first
                cursor.execute("""
                    UPDATE google_tokens
                    SET access_token = %s, refresh_token = %s, token_expiry = %s,
                        scopes = %s, updated_at = %s
                    WHERE user_id = %s
                """, (access_token, refresh_token, token_expiry, scopes_json, datetime.utcnow(), user_id))

                if cursor.rowcount == 0:
                    # Insert new
                    cursor.execute("""
                        INSERT INTO google_tokens (user_id, access_token, refresh_token, token_expiry, scopes)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (user_id, access_token, refresh_token, token_expiry, scopes_json))

                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error saving Google token: {e}")
            return False

    def update_access_token(self, user_id: int, access_token: str, token_expiry: datetime) -> bool:
        """Update only the access token (after refresh)."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE google_tokens
                    SET access_token = %s, token_expiry = %s, updated_at = %s
                    WHERE user_id = %s
                """, (access_token, token_expiry, datetime.utcnow(), user_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating access token: {e}")
            return False

    def delete_token(self, user_id: int) -> bool:
        """Delete Google token (revoke access)."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM google_tokens WHERE user_id = %s", (user_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting Google token: {e}")
            return False

    def is_token_valid(self, user_id: int) -> bool:
        """Check if user has a valid (non-expired) token."""
        token = self.get_token(user_id)
        if not token:
            return False
        return token.token_expiry > datetime.utcnow()


google_token_db = GoogleTokenDB()

"""Email cache CRUD operations."""
import json
import logging
from typing import Optional, List
from datetime import datetime

from app.crud.db_connection import db

logger = logging.getLogger(__name__)


class EmailCacheDB:
    """Email cache database operations."""

    def __init__(self):
        self.db = db

    def upsert_email(self, user_id: int, email_data: dict) -> bool:
        """Insert or update an email in cache."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()

                labels_json = json.dumps(email_data.get('labels', []))

                # Try to update first
                cursor.execute("""
                    UPDATE email_cache SET
                        thread_id = %s,
                        subject = %s,
                        sender = %s,
                        snippet = %s,
                        body_preview = %s,
                        received_at = %s,
                        labels = %s
                    WHERE user_id = %s AND gmail_id = %s
                """, (
                    email_data.get('thread_id'),
                    email_data.get('subject'),
                    email_data.get('sender'),
                    email_data.get('snippet'),
                    email_data.get('body_preview'),
                    email_data.get('received_at'),
                    labels_json,
                    user_id,
                    email_data['gmail_id']
                ))

                if cursor.rowcount == 0:
                    # Insert new
                    cursor.execute("""
                        INSERT INTO email_cache
                        (user_id, gmail_id, thread_id, subject, sender, snippet, body_preview, received_at, labels)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        user_id,
                        email_data['gmail_id'],
                        email_data.get('thread_id'),
                        email_data.get('subject'),
                        email_data.get('sender'),
                        email_data.get('snippet'),
                        email_data.get('body_preview'),
                        email_data.get('received_at'),
                        labels_json
                    ))

                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error upserting email: {e}")
            return False

    def bulk_upsert(self, user_id: int, emails: List[dict]) -> int:
        """Bulk insert/update emails."""
        count = 0
        for email in emails:
            if self.upsert_email(user_id, email):
                count += 1
        return count

    def get_emails(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        unprocessed_only: bool = False
    ) -> List[dict]:
        """Get cached emails for a user."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()

                where_clause = "user_id = %s"
                params = [user_id]

                if unprocessed_only:
                    where_clause += " AND is_processed = FALSE"

                cursor.execute(f"""
                    SELECT * FROM email_cache
                    WHERE {where_clause}
                    ORDER BY received_at DESC
                    LIMIT %s OFFSET %s
                """, (*params, limit, offset))

                rows = cursor.fetchall()
                emails = []
                for row in rows:
                    email = dict(row)
                    if email.get('labels') and isinstance(email['labels'], str):
                        email['labels'] = json.loads(email['labels'])
                    emails.append(email)
                return emails
        except Exception as e:
            logger.error(f"Error getting emails: {e}")
            return []

    def get_email_by_gmail_id(self, user_id: int, gmail_id: str) -> Optional[dict]:
        """Get a specific email by Gmail ID."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM email_cache WHERE user_id = %s AND gmail_id = %s",
                    (user_id, gmail_id)
                )
                row = cursor.fetchone()
                if row:
                    email = dict(row)
                    if email.get('labels') and isinstance(email['labels'], str):
                        email['labels'] = json.loads(email['labels'])
                    return email
                return None
        except Exception as e:
            logger.error(f"Error getting email: {e}")
            return None

    def mark_processed(self, user_id: int, gmail_id: str) -> bool:
        """Mark an email as processed (for task extraction)."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE email_cache SET is_processed = TRUE
                    WHERE user_id = %s AND gmail_id = %s
                """, (user_id, gmail_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error marking email processed: {e}")
            return False

    def get_count(self, user_id: int) -> int:
        """Get total email count for user."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) as count FROM email_cache WHERE user_id = %s",
                    (user_id,)
                )
                return cursor.fetchone()['count']
        except Exception as e:
            logger.error(f"Error getting email count: {e}")
            return 0

    def delete_old_emails(self, user_id: int, days: int = 30) -> int:
        """Delete emails older than specified days."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM email_cache
                    WHERE user_id = %s AND received_at < NOW() - INTERVAL '%s days'
                """, (user_id, days))
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Error deleting old emails: {e}")
            return 0

    def get_emails_by_date_range(
        self,
        user_id: int,
        start_date: datetime,
        end_date: datetime,
        limit: int = 100
    ) -> List[dict]:
        """Get emails within a date range."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM email_cache
                    WHERE user_id = %s
                      AND received_at >= %s
                      AND received_at <= %s
                    ORDER BY received_at DESC
                    LIMIT %s
                """, (user_id, start_date, end_date, limit))

                rows = cursor.fetchall()
                emails = []
                for row in rows:
                    email = dict(row)
                    if email.get('labels') and isinstance(email['labels'], str):
                        email['labels'] = json.loads(email['labels'])
                    emails.append(email)
                return emails
        except Exception as e:
            logger.error(f"Error getting emails by date range: {e}")
            return []


email_cache_db = EmailCacheDB()

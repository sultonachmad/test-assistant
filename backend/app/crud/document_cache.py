"""Document cache CRUD operations."""
import json
import hashlib
import logging
from typing import Optional, List
from datetime import datetime

from app.crud.db_connection import db

logger = logging.getLogger(__name__)


class SelectedDocumentDB:
    """Selected documents database operations."""

    def __init__(self):
        self.db = db

    def add_document(self, user_id: int, doc_data: dict) -> Optional[int]:
        """Add a document to monitoring list."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()

                # Check if already exists
                cursor.execute(
                    "SELECT id FROM selected_documents WHERE user_id = %s AND doc_id = %s",
                    (user_id, doc_data['doc_id'])
                )
                existing = cursor.fetchone()
                if existing:
                    # Update existing
                    cursor.execute("""
                        UPDATE selected_documents SET
                            doc_name = %s,
                            doc_url = %s,
                            is_active = TRUE,
                            updated_at = %s
                        WHERE user_id = %s AND doc_id = %s
                        RETURNING id
                    """, (
                        doc_data.get('doc_name'),
                        doc_data.get('doc_url'),
                        datetime.utcnow(),
                        user_id,
                        doc_data['doc_id']
                    ))
                else:
                    # Insert new
                    cursor.execute("""
                        INSERT INTO selected_documents
                        (user_id, doc_id, doc_name, doc_url)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id
                    """, (
                        user_id,
                        doc_data['doc_id'],
                        doc_data.get('doc_name'),
                        doc_data.get('doc_url')
                    ))

                row = cursor.fetchone()
                conn.commit()
                return row['id'] if row else None
        except Exception as e:
            logger.error(f"Error adding document: {e}")
            return None

    def get_documents(self, user_id: int, active_only: bool = True) -> List[dict]:
        """Get selected documents for a user."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()

                where_clause = "user_id = %s"
                if active_only:
                    where_clause += " AND is_active = TRUE"

                cursor.execute(f"""
                    SELECT * FROM selected_documents
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                """, (user_id,))

                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting documents: {e}")
            return []

    def get_document_by_id(self, user_id: int, doc_id: str) -> Optional[dict]:
        """Get a specific document."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM selected_documents WHERE user_id = %s AND doc_id = %s",
                    (user_id, doc_id)
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting document: {e}")
            return None

    def update_document_sync(
        self,
        document_id: int,
        last_modified: datetime,
        content_hash: str
    ) -> bool:
        """Update document after sync."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE selected_documents SET
                        last_modified = %s,
                        content_hash = %s,
                        updated_at = %s
                    WHERE id = %s
                """, (last_modified, content_hash, datetime.utcnow(), document_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating document sync: {e}")
            return False

    def deactivate_document(self, user_id: int, doc_id: str) -> bool:
        """Deactivate (soft delete) a document."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE selected_documents SET is_active = FALSE, updated_at = %s
                    WHERE user_id = %s AND doc_id = %s
                """, (datetime.utcnow(), user_id, doc_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deactivating document: {e}")
            return False

    def delete_document(self, user_id: int, doc_id: str) -> bool:
        """Delete a document permanently."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM selected_documents WHERE user_id = %s AND doc_id = %s",
                    (user_id, doc_id)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            return False


class DocumentCacheDB:
    """Document content cache database operations."""

    def __init__(self):
        self.db = db

    def save_content(
        self,
        document_id: int,
        content: str,
        extracted_tasks: List[dict] = None,
        summary: str = None
    ) -> bool:
        """Save or update document content."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()

                tasks_json = json.dumps(extracted_tasks) if extracted_tasks else None

                # Delete old cache and insert new
                cursor.execute(
                    "DELETE FROM document_cache WHERE document_id = %s",
                    (document_id,)
                )
                cursor.execute("""
                    INSERT INTO document_cache
                    (document_id, content, extracted_tasks, summary)
                    VALUES (%s, %s, %s, %s)
                """, (document_id, content, tasks_json, summary))

                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error saving document content: {e}")
            return False

    def get_content(self, document_id: int) -> Optional[dict]:
        """Get cached content for a document."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM document_cache WHERE document_id = %s ORDER BY created_at DESC LIMIT 1",
                    (document_id,)
                )
                row = cursor.fetchone()
                if row:
                    data = dict(row)
                    if data.get('extracted_tasks') and isinstance(data['extracted_tasks'], str):
                        data['extracted_tasks'] = json.loads(data['extracted_tasks'])
                    return data
                return None
        except Exception as e:
            logger.error(f"Error getting document content: {e}")
            return None

    def delete_content(self, document_id: int) -> bool:
        """Delete cached content."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM document_cache WHERE document_id = %s",
                    (document_id,)
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error deleting document content: {e}")
            return False


def compute_content_hash(content: str) -> str:
    """Compute SHA256 hash of content."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


selected_document_db = SelectedDocumentDB()
document_cache_db = DocumentCacheDB()

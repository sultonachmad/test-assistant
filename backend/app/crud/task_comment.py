"""Task comment CRUD operations."""
import logging
from typing import Optional, List
from datetime import datetime

from app.crud.db_connection import db
from app.schemas.task_comment import TaskComment, TaskCommentCreate, TaskCommentUpdate

logger = logging.getLogger(__name__)


class TaskCommentDB:
    """Task comment database operations."""

    def __init__(self):
        self.db = db

    def _row_to_comment(self, row: dict) -> TaskComment:
        """Convert database row to TaskComment schema."""
        return TaskComment(**dict(row))

    def get_by_id(self, comment_id: int, user_id: int) -> Optional[TaskComment]:
        """Get comment by ID."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM task_comments WHERE id = %s AND user_id = %s",
                    (comment_id, user_id)
                )
                row = cursor.fetchone()
                if row:
                    return self._row_to_comment(row)
                return None
        except Exception as e:
            logger.error(f"Error getting comment: {e}")
            return None

    def get_by_task(
        self,
        task_id: int,
        user_id: int,
        comment_type: Optional[str] = None
    ) -> List[TaskComment]:
        """Get all comments for a task."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()

                if comment_type:
                    cursor.execute("""
                        SELECT * FROM task_comments
                        WHERE task_id = %s AND user_id = %s AND comment_type = %s
                        ORDER BY created_at ASC
                    """, (task_id, user_id, comment_type))
                else:
                    cursor.execute("""
                        SELECT * FROM task_comments
                        WHERE task_id = %s AND user_id = %s
                        ORDER BY created_at ASC
                    """, (task_id, user_id))

                return [self._row_to_comment(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting comments: {e}")
            return []

    def get_by_ids(self, comment_ids: List[int], user_id: int) -> List[TaskComment]:
        """Get comments by list of IDs."""
        if not comment_ids:
            return []
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                placeholders = ','.join(['%s'] * len(comment_ids))
                cursor.execute(f"""
                    SELECT * FROM task_comments
                    WHERE id IN ({placeholders}) AND user_id = %s
                    ORDER BY created_at ASC
                """, (*comment_ids, user_id))
                return [self._row_to_comment(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting comments by ids: {e}")
            return []

    def create(self, user_id: int, comment: TaskCommentCreate) -> Optional[TaskComment]:
        """Create a new comment."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO task_comments (
                        task_id, user_id, comment_type, content,
                        is_ai_generated, ai_prompt,
                        estimated_days, suggested_start_date, suggested_due_date
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                """, (
                    comment.task_id,
                    user_id,
                    comment.comment_type.value,
                    comment.content,
                    comment.is_ai_generated,
                    comment.ai_prompt,
                    comment.estimated_days,
                    comment.suggested_start_date,
                    comment.suggested_due_date
                ))
                row = cursor.fetchone()
                conn.commit()
                if row:
                    return self._row_to_comment(row)
                return None
        except Exception as e:
            logger.error(f"Error creating comment: {e}")
            return None

    def update(
        self,
        comment_id: int,
        user_id: int,
        update: TaskCommentUpdate
    ) -> Optional[TaskComment]:
        """Update a comment."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                updates = []
                values = []

                if update.content is not None:
                    updates.append("content = %s")
                    values.append(update.content)
                if update.estimated_days is not None:
                    updates.append("estimated_days = %s")
                    values.append(update.estimated_days)
                if update.suggested_start_date is not None:
                    updates.append("suggested_start_date = %s")
                    values.append(update.suggested_start_date)
                if update.suggested_due_date is not None:
                    updates.append("suggested_due_date = %s")
                    values.append(update.suggested_due_date)

                if not updates:
                    return self.get_by_id(comment_id, user_id)

                updates.append("updated_at = %s")
                values.append(datetime.utcnow())
                values.extend([comment_id, user_id])

                cursor.execute(f"""
                    UPDATE task_comments SET {', '.join(updates)}
                    WHERE id = %s AND user_id = %s
                    RETURNING *
                """, tuple(values))
                row = cursor.fetchone()
                conn.commit()
                if row:
                    return self._row_to_comment(row)
                return None
        except Exception as e:
            logger.error(f"Error updating comment: {e}")
            return None

    def delete(self, comment_id: int, user_id: int) -> bool:
        """Delete a comment."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM task_comments WHERE id = %s AND user_id = %s",
                    (comment_id, user_id)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting comment: {e}")
            return False

    def get_comment_count_by_task(self, task_id: int, user_id: int) -> dict:
        """Get comment count grouped by type for a task."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT comment_type, COUNT(*) as count
                    FROM task_comments
                    WHERE task_id = %s AND user_id = %s
                    GROUP BY comment_type
                """, (task_id, user_id))
                result = {row['comment_type']: row['count'] for row in cursor.fetchall()}
                return result
        except Exception as e:
            logger.error(f"Error getting comment count: {e}")
            return {}


task_comment_db = TaskCommentDB()

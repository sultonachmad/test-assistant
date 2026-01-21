"""Task CRUD operations."""
import json
import logging
from typing import Optional, List
from datetime import datetime, timedelta

from app.crud.db_connection import db
from app.schemas.task import Task, TaskCreate, TaskUpdate, TaskStatus, TaskSummary, RecurrenceType

logger = logging.getLogger(__name__)


class TaskDB:
    """Task database operations."""

    def __init__(self):
        self.db = db

    def _row_to_task(self, row: dict) -> Task:
        """Convert database row to Task schema."""
        data = dict(row)
        if data.get('tags') and isinstance(data['tags'], str):
            try:
                data['tags'] = json.loads(data['tags'])
            except:
                data['tags'] = []
        return Task(**data)

    def get_by_id(self, task_id: int, user_id: int) -> Optional[Task]:
        """Get task by ID."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM tasks WHERE id = %s AND user_id = %s",
                    (task_id, user_id)
                )
                row = cursor.fetchone()
                if row:
                    return self._row_to_task(row)
                return None
        except Exception as e:
            logger.error(f"Error getting task: {e}")
            return None

    def get_all(
        self,
        user_id: int,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        project: Optional[str] = None,
        source_type: Optional[str] = None,
        due_before: Optional[datetime] = None,
        assigned_to: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> tuple[List[Task], int]:
        """Get all tasks with filters."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()

                where_clauses = ["user_id = %s"]
                values = [user_id]

                if status:
                    # Support comma-separated status values for multi-select
                    status_list = [s.strip() for s in status.split(",")]
                    if len(status_list) == 1:
                        where_clauses.append("status = %s")
                        values.append(status_list[0])
                    else:
                        placeholders = ", ".join(["%s"] * len(status_list))
                        where_clauses.append(f"status IN ({placeholders})")
                        values.extend(status_list)
                if priority:
                    where_clauses.append("priority = %s")
                    values.append(priority)
                if project:
                    where_clauses.append("project ILIKE %s")
                    values.append(f"%{project}%")
                if source_type:
                    where_clauses.append("source_type = %s")
                    values.append(source_type)
                if due_before:
                    where_clauses.append("due_date <= %s")
                    values.append(due_before)
                if assigned_to:
                    where_clauses.append("assigned_to ILIKE %s")
                    values.append(f"%{assigned_to}%")
                if search:
                    where_clauses.append("(title ILIKE %s OR description ILIKE %s)")
                    values.extend([f"%{search}%", f"%{search}%"])

                where_sql = " AND ".join(where_clauses)

                # Get total count
                cursor.execute(f"SELECT COUNT(*) as count FROM tasks WHERE {where_sql}", tuple(values))
                total = cursor.fetchone()['count']

                # Get paginated results
                offset = (page - 1) * limit
                values.extend([limit, offset])
                cursor.execute(f"""
                    SELECT * FROM tasks WHERE {where_sql}
                    ORDER BY
                        CASE WHEN due_date IS NULL THEN 1 ELSE 0 END,
                        due_date ASC,
                        CASE priority
                            WHEN 'urgent' THEN 1
                            WHEN 'high' THEN 2
                            WHEN 'medium' THEN 3
                            WHEN 'low' THEN 4
                        END,
                        created_at DESC
                    LIMIT %s OFFSET %s
                """, tuple(values))

                tasks = [self._row_to_task(row) for row in cursor.fetchall()]
                return tasks, total
        except Exception as e:
            logger.error(f"Error getting tasks: {e}")
            return [], 0

    def create(self, user_id: int, task: TaskCreate) -> Optional[Task]:
        """Create a new task."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                tags_json = json.dumps(task.tags) if task.tags else None
                recurrence_type_val = task.recurrence_type.value if task.recurrence_type else 'none'
                cursor.execute("""
                    INSERT INTO tasks (user_id, title, description, status, priority, project,
                                       start_date, due_date, completed_date,
                                       source_type, source_id, source_url, assigned_to, tags,
                                       is_recurring, recurrence_type, recurrence_end_date, parent_task_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                """, (
                    user_id, task.title, task.description, task.status.value,
                    task.priority.value, task.project, task.start_date, task.due_date, task.completed_date,
                    task.source_type, task.source_id, task.source_url, task.assigned_to, tags_json,
                    task.is_recurring, recurrence_type_val, task.recurrence_end_date, task.parent_task_id
                ))
                row = cursor.fetchone()
                conn.commit()
                if row:
                    return self._row_to_task(row)
                return None
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            return None

    def update(self, task_id: int, user_id: int, task: TaskUpdate) -> Optional[Task]:
        """Update task."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                updates = []
                values = []

                if task.title is not None:
                    updates.append("title = %s")
                    values.append(task.title)
                if task.description is not None:
                    updates.append("description = %s")
                    values.append(task.description)
                if task.status is not None:
                    updates.append("status = %s")
                    values.append(task.status.value)
                if task.priority is not None:
                    updates.append("priority = %s")
                    values.append(task.priority.value)
                if task.project is not None:
                    updates.append("project = %s")
                    values.append(task.project)
                if task.start_date is not None:
                    updates.append("start_date = %s")
                    values.append(task.start_date)
                if task.due_date is not None:
                    updates.append("due_date = %s")
                    values.append(task.due_date)
                if task.completed_date is not None:
                    updates.append("completed_date = %s")
                    values.append(task.completed_date)
                if task.assigned_to is not None:
                    updates.append("assigned_to = %s")
                    values.append(task.assigned_to)
                if task.tags is not None:
                    updates.append("tags = %s")
                    values.append(json.dumps(task.tags))
                if task.is_recurring is not None:
                    updates.append("is_recurring = %s")
                    values.append(task.is_recurring)
                if task.recurrence_type is not None:
                    updates.append("recurrence_type = %s")
                    values.append(task.recurrence_type.value)
                if task.recurrence_end_date is not None:
                    updates.append("recurrence_end_date = %s")
                    values.append(task.recurrence_end_date)

                if not updates:
                    return self.get_by_id(task_id, user_id)

                updates.append("updated_at = %s")
                values.append(datetime.utcnow())
                values.extend([task_id, user_id])

                cursor.execute(f"""
                    UPDATE tasks SET {', '.join(updates)}
                    WHERE id = %s AND user_id = %s RETURNING *
                """, tuple(values))
                row = cursor.fetchone()
                conn.commit()
                if row:
                    return self._row_to_task(row)
                return None
        except Exception as e:
            logger.error(f"Error updating task: {e}")
            return None

    def update_status(self, task_id: int, user_id: int, status: TaskStatus) -> Optional[Task]:
        """Update task status only. Auto-sets dates based on status transitions."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                now = datetime.utcnow()

                if status == TaskStatus.DONE:
                    # Auto-set completed_date when marking as done
                    cursor.execute("""
                        UPDATE tasks SET status = %s, completed_date = %s, updated_at = %s
                        WHERE id = %s AND user_id = %s RETURNING *
                    """, (status.value, now, now, task_id, user_id))
                elif status == TaskStatus.IN_PROGRESS:
                    # Auto-set start_date when starting work (if not already set)
                    cursor.execute("""
                        UPDATE tasks SET status = %s,
                            start_date = COALESCE(start_date, %s),
                            completed_date = NULL,
                            updated_at = %s
                        WHERE id = %s AND user_id = %s RETURNING *
                    """, (status.value, now, now, task_id, user_id))
                else:
                    # Clear completed_date if moving away from done
                    cursor.execute("""
                        UPDATE tasks SET status = %s, completed_date = NULL, updated_at = %s
                        WHERE id = %s AND user_id = %s RETURNING *
                    """, (status.value, now, task_id, user_id))

                row = cursor.fetchone()
                conn.commit()
                if row:
                    return self._row_to_task(row)
                return None
        except Exception as e:
            logger.error(f"Error updating task status: {e}")
            return None

    def delete(self, task_id: int, user_id: int) -> bool:
        """Delete task."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM tasks WHERE id = %s AND user_id = %s",
                    (task_id, user_id)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting task: {e}")
            return False

    def get_summary(self, user_id: int) -> TaskSummary:
        """Get task statistics summary."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE status = 'done') as done,
                        COUNT(*) FILTER (WHERE status = 'in_progress') as in_progress,
                        COUNT(*) FILTER (WHERE status = 'on_hold') as on_hold,
                        COUNT(*) FILTER (WHERE status = 'assigned') as assigned,
                        COUNT(*) FILTER (WHERE due_date < NOW() AND status != 'done') as overdue
                    FROM tasks WHERE user_id = %s
                """, (user_id,))
                row = cursor.fetchone()
                return TaskSummary(**dict(row))
        except Exception as e:
            logger.error(f"Error getting task summary: {e}")
            return TaskSummary()

    def find_by_source(
        self,
        user_id: int,
        source_type: str,
        source_id: str,
        title: str
    ) -> Optional[dict]:
        """Find a task by source and title (for deduplication)."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM tasks
                    WHERE user_id = %s AND source_type = %s AND source_id = %s AND title = %s
                    LIMIT 1
                """, (user_id, source_type, source_id, title))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error finding task by source: {e}")
            return None

    def create_from_dict(self, user_id: int, task_data: dict) -> Optional[int]:
        """Create a task from a dictionary (for external sync)."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                tags_json = json.dumps(task_data.get('tags')) if task_data.get('tags') else None
                cursor.execute("""
                    INSERT INTO tasks (user_id, title, description, status, priority, project,
                                       start_date, due_date, completed_date,
                                       source_type, source_id, source_url, assigned_to, tags)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    user_id,
                    task_data.get('title'),
                    task_data.get('description'),
                    task_data.get('status', 'assigned'),
                    task_data.get('priority', 'medium'),
                    task_data.get('project'),
                    task_data.get('start_date'),
                    task_data.get('due_date'),
                    task_data.get('completed_date'),
                    task_data.get('source_type'),
                    task_data.get('source_id'),
                    task_data.get('source_url'),
                    task_data.get('assigned_to'),
                    tags_json
                ))
                result = cursor.fetchone()
                conn.commit()
                return result['id'] if result else None
        except Exception as e:
            logger.error(f"Error creating task from dict: {e}")
            return None

    def update_from_dict(self, task_id: int, user_id: int, task_data: dict) -> bool:
        """Update a task from a dictionary (for external sync).

        Note: For date fields (start_date, due_date, completed_date), explicitly passing None
        will clear the value. For other fields, None values are skipped.
        """
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                updates = []
                values = []

                # Fields that can be cleared (set to NULL) when explicitly passed as None
                nullable_date_fields = ['start_date', 'due_date', 'completed_date']

                # Fields that skip None values
                regular_fields = ['title', 'description', 'status', 'priority', 'project', 'assigned_to', 'source_type', 'source_id', 'source_url']

                for field in regular_fields:
                    if field in task_data and task_data[field] is not None:
                        updates.append(f"{field} = %s")
                        values.append(task_data[field])

                # Handle date fields - allow explicit NULL setting
                for field in nullable_date_fields:
                    if field in task_data:
                        updates.append(f"{field} = %s")
                        values.append(task_data[field])  # Can be None to clear the field

                if 'tags' in task_data:
                    updates.append("tags = %s")
                    values.append(json.dumps(task_data['tags']) if task_data['tags'] else None)

                if not updates:
                    return True

                updates.append("updated_at = %s")
                values.append(datetime.utcnow())
                values.extend([task_id, user_id])

                cursor.execute(f"""
                    UPDATE tasks SET {', '.join(updates)}
                    WHERE id = %s AND user_id = %s
                """, tuple(values))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating task from dict: {e}")
            return False

    def get_assignees(self, user_id: int) -> List[str]:
        """Get list of unique assigned_to values for filtering."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT assigned_to FROM tasks
                    WHERE user_id = %s AND assigned_to IS NOT NULL AND assigned_to != ''
                    ORDER BY assigned_to
                """, (user_id,))
                return [row['assigned_to'] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting assignees: {e}")
            return []

    def get_projects(self, user_id: int) -> List[str]:
        """Get list of unique project names for filtering."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT project FROM tasks
                    WHERE user_id = %s AND project IS NOT NULL AND project != ''
                    ORDER BY project
                """, (user_id,))
                return [row['project'] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting projects: {e}")
            return []

    def get_recurring_tasks(self, user_id: int) -> List[Task]:
        """Get all recurring task templates for a user."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM tasks
                    WHERE user_id = %s AND is_recurring = TRUE AND parent_task_id IS NULL
                    ORDER BY title
                """, (user_id,))
                return [self._row_to_task(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting recurring tasks: {e}")
            return []

    def get_next_recurrence_date(self, recurrence_type: str, from_date: datetime) -> datetime:
        """Calculate the next occurrence date based on recurrence type."""
        if recurrence_type == 'daily':
            return from_date + timedelta(days=1)
        elif recurrence_type == 'weekly':
            return from_date + timedelta(weeks=1)
        elif recurrence_type == 'biweekly':
            return from_date + timedelta(weeks=2)
        elif recurrence_type == 'monthly':
            # Add approximately one month
            next_month = from_date.month + 1
            next_year = from_date.year
            if next_month > 12:
                next_month = 1
                next_year += 1
            try:
                return from_date.replace(year=next_year, month=next_month)
            except ValueError:
                # Handle edge case like Jan 31 -> Feb 28
                return from_date.replace(year=next_year, month=next_month, day=28)
        return from_date

    def generate_recurring_instance(self, user_id: int, parent_task_id: int) -> Optional[Task]:
        """Generate a new instance of a recurring task."""
        try:
            parent = self.get_by_id(parent_task_id, user_id)
            if not parent or not parent.is_recurring:
                return None

            # Check if recurrence has ended
            if parent.recurrence_end_date and datetime.utcnow() > parent.recurrence_end_date:
                return None

            # Calculate new due date based on parent's due date or today
            base_date = parent.due_date if parent.due_date else datetime.utcnow()
            new_due_date = self.get_next_recurrence_date(parent.recurrence_type.value, base_date)

            with self.db.connect() as conn:
                cursor = conn.cursor()
                tags_json = json.dumps(parent.tags) if parent.tags else None
                cursor.execute("""
                    INSERT INTO tasks (user_id, title, description, status, priority, project,
                                       due_date, source_type, source_id, source_url, assigned_to, tags,
                                       is_recurring, recurrence_type, recurrence_end_date, parent_task_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                """, (
                    user_id, parent.title, parent.description, 'assigned',
                    parent.priority.value, parent.project, new_due_date,
                    parent.source_type, parent.source_id, parent.source_url, parent.assigned_to, tags_json,
                    False, 'none', None, parent_task_id
                ))
                row = cursor.fetchone()
                conn.commit()
                if row:
                    return self._row_to_task(row)
                return None
        except Exception as e:
            logger.error(f"Error generating recurring instance: {e}")
            return None

    def check_and_generate_recurring_tasks(self, user_id: int) -> List[Task]:
        """Check all recurring tasks and generate instances if needed."""
        generated = []
        try:
            recurring_tasks = self.get_recurring_tasks(user_id)
            now = datetime.utcnow()

            for task in recurring_tasks:
                # Skip if recurrence has ended
                if task.recurrence_end_date and now > task.recurrence_end_date:
                    continue

                # Check if we need to generate a new instance
                # Look for the most recent instance of this recurring task
                with self.db.connect() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT due_date FROM tasks
                        WHERE parent_task_id = %s
                        ORDER BY due_date DESC
                        LIMIT 1
                    """, (task.id,))
                    last_instance = cursor.fetchone()

                    # Determine if we need a new instance
                    should_generate = False
                    if not last_instance:
                        # No instances yet, generate one
                        should_generate = True
                    else:
                        last_due = last_instance['due_date']
                        if last_due:
                            next_due = self.get_next_recurrence_date(task.recurrence_type.value, last_due)
                            # Generate if next due date is within the next week
                            if next_due <= now + timedelta(days=7):
                                should_generate = True

                    if should_generate:
                        new_task = self.generate_recurring_instance(user_id, task.id)
                        if new_task:
                            generated.append(new_task)

        except Exception as e:
            logger.error(f"Error checking recurring tasks: {e}")

        return generated


task_db = TaskDB()

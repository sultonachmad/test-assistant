"""PostgreSQL database connection manager."""
import logging
from contextlib import contextmanager
from typing import Optional, Generator
import psycopg2
from psycopg2.extras import RealDictCursor

from app.core.config import settings

logger = logging.getLogger(__name__)


class ConnectionManager:
    """PostgreSQL connection manager with automatic table creation."""

    def __init__(self, dsn: Optional[str] = None):
        self.dsn = dsn or settings.POSTGRES_DSN
        self._init_db()

    @contextmanager
    def connect(self) -> Generator:
        """Get a database connection with automatic cleanup."""
        conn = None
        try:
            conn = psycopg2.connect(self.dsn, cursor_factory=RealDictCursor)
            yield conn
        except psycopg2.Error as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def _init_db(self):
        """Initialize database tables."""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()

                # Users table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        email VARCHAR(255) NOT NULL UNIQUE,
                        name VARCHAR(255),
                        image VARCHAR(500),
                        timezone VARCHAR(50) DEFAULT 'Asia/Singapore',
                        notification_email BOOLEAN DEFAULT TRUE,
                        notification_calendar BOOLEAN DEFAULT TRUE,
                        notification_inapp BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Google OAuth tokens
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS google_tokens (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        access_token TEXT NOT NULL,
                        refresh_token TEXT NOT NULL,
                        token_expiry TIMESTAMP NOT NULL,
                        scopes TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id)
                    )
                """)

                # Tasks table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        title VARCHAR(500) NOT NULL,
                        description TEXT,
                        status VARCHAR(20) DEFAULT 'assigned',
                        priority VARCHAR(20) DEFAULT 'medium',
                        project VARCHAR(255),
                        start_date TIMESTAMP,
                        due_date TIMESTAMP,
                        completed_date TIMESTAMP,
                        source_type VARCHAR(50),
                        source_id VARCHAR(255),
                        source_url TEXT,
                        assigned_to VARCHAR(255),
                        tags TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Migration: rename assigned_by to assigned_to if exists
                cursor.execute("""
                    DO $$
                    BEGIN
                        IF EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_name = 'tasks' AND column_name = 'assigned_by'
                        ) THEN
                            ALTER TABLE tasks RENAME COLUMN assigned_by TO assigned_to;
                        END IF;
                    END $$;
                """)

                # Migration: add start_date and completed_date columns if not exists
                cursor.execute("""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_name = 'tasks' AND column_name = 'start_date'
                        ) THEN
                            ALTER TABLE tasks ADD COLUMN start_date TIMESTAMP;
                        END IF;
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_name = 'tasks' AND column_name = 'completed_date'
                        ) THEN
                            ALTER TABLE tasks ADD COLUMN completed_date TIMESTAMP;
                        END IF;
                    END $$;
                """)

                # Migration: add project column if not exists
                cursor.execute("""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_name = 'tasks' AND column_name = 'project'
                        ) THEN
                            ALTER TABLE tasks ADD COLUMN project VARCHAR(255);
                        END IF;
                    END $$;
                """)

                # Migration: add recurrence columns if not exists
                cursor.execute("""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_name = 'tasks' AND column_name = 'is_recurring'
                        ) THEN
                            ALTER TABLE tasks ADD COLUMN is_recurring BOOLEAN DEFAULT FALSE;
                        END IF;
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_name = 'tasks' AND column_name = 'recurrence_type'
                        ) THEN
                            ALTER TABLE tasks ADD COLUMN recurrence_type VARCHAR(20) DEFAULT 'none';
                        END IF;
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_name = 'tasks' AND column_name = 'recurrence_end_date'
                        ) THEN
                            ALTER TABLE tasks ADD COLUMN recurrence_end_date TIMESTAMP;
                        END IF;
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_name = 'tasks' AND column_name = 'parent_task_id'
                        ) THEN
                            ALTER TABLE tasks ADD COLUMN parent_task_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL;
                        END IF;
                    END $$;
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_tasks_user_status ON tasks(user_id, status)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date)
                """)

                # Reminders table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS reminders (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
                        title VARCHAR(500) NOT NULL,
                        description TEXT,
                        remind_at TIMESTAMP NOT NULL,
                        remind_via TEXT NOT NULL,
                        is_recurring BOOLEAN DEFAULT FALSE,
                        recurrence_rule TEXT,
                        status VARCHAR(20) DEFAULT 'pending',
                        calendar_event_id VARCHAR(255),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_reminders_user ON reminders(user_id, status)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_reminders_remind_at ON reminders(remind_at)
                """)

                # Notifications table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS notifications (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        type VARCHAR(50) NOT NULL,
                        title VARCHAR(255) NOT NULL,
                        message TEXT,
                        link TEXT,
                        is_read BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read)
                """)

                # Email cache
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS email_cache (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        gmail_id VARCHAR(255) NOT NULL,
                        thread_id VARCHAR(255),
                        subject VARCHAR(500),
                        sender VARCHAR(255),
                        snippet TEXT,
                        body_preview TEXT,
                        received_at TIMESTAMP,
                        labels TEXT,
                        is_processed BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, gmail_id)
                    )
                """)

                # Chat cache
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS chat_cache (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        space_id VARCHAR(255) NOT NULL,
                        space_name VARCHAR(255),
                        message_id VARCHAR(255) NOT NULL,
                        sender_name VARCHAR(255),
                        sender_email VARCHAR(255),
                        text TEXT,
                        sent_at TIMESTAMP,
                        is_processed BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, message_id)
                    )
                """)

                # Calendar cache
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS calendar_cache (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        event_id VARCHAR(255) NOT NULL,
                        calendar_id VARCHAR(255) DEFAULT 'primary',
                        summary VARCHAR(500),
                        description TEXT,
                        location VARCHAR(500),
                        start_time TIMESTAMP,
                        end_time TIMESTAMP,
                        attendees TEXT,
                        is_all_day BOOLEAN DEFAULT FALSE,
                        status VARCHAR(50),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, event_id)
                    )
                """)

                # Selected documents
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS selected_documents (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        doc_id VARCHAR(255) NOT NULL,
                        doc_name VARCHAR(500),
                        doc_url TEXT,
                        last_modified TIMESTAMP,
                        content_hash VARCHAR(64),
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, doc_id)
                    )
                """)

                # Document cache
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS document_cache (
                        id SERIAL PRIMARY KEY,
                        document_id INTEGER NOT NULL REFERENCES selected_documents(id) ON DELETE CASCADE,
                        content TEXT,
                        extracted_tasks TEXT,
                        summary TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Sync logs
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sync_logs (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        sync_type VARCHAR(50) NOT NULL,
                        status VARCHAR(20) NOT NULL,
                        items_synced INTEGER DEFAULT 0,
                        error_message TEXT,
                        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP
                    )
                """)

                # AI suggestions
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS ai_suggestions (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        suggestion_type VARCHAR(50) NOT NULL,
                        content TEXT NOT NULL,
                        context TEXT,
                        is_accepted BOOLEAN,
                        is_dismissed BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Sheet sync configurations
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sheet_sync_configs (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        spreadsheet_id VARCHAR(255) NOT NULL,
                        spreadsheet_name VARCHAR(500),
                        spreadsheet_url TEXT,
                        sheet_name VARCHAR(255) NOT NULL,
                        field_mapping TEXT NOT NULL,
                        auto_sync BOOLEAN DEFAULT TRUE,
                        sync_interval_minutes INTEGER DEFAULT 15,
                        last_sync TIMESTAMP,
                        last_sync_count INTEGER DEFAULT 0,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, spreadsheet_id, sheet_name)
                    )
                """)

                # Taiga config (future)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS taiga_config (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        taiga_url VARCHAR(500),
                        auth_token TEXT,
                        project_id INTEGER,
                        last_sync TIMESTAMP,
                        is_active BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id)
                    )
                """)

                # Taiga cards
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS taiga_cards (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        card_id INTEGER NOT NULL,
                        card_type VARCHAR(50),
                        subject VARCHAR(500),
                        status VARCHAR(100),
                        due_date TIMESTAMP,
                        last_checked TIMESTAMP,
                        needs_update BOOLEAN DEFAULT FALSE,
                        task_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, card_id, card_type)
                    )
                """)

                conn.commit()
                logger.info("Database tables initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise


# Singleton instance
db = ConnectionManager()

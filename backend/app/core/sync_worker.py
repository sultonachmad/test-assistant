"""Sync worker for Google API data synchronization."""
import logging
from typing import Optional
from datetime import datetime

from app.core.config import settings
from app.core.google_api_client import GoogleAPIClient
from app.core.websocket_manager import send_sync_progress
from app.crud.sync_log import sync_log_db
from app.crud.email_cache import email_cache_db
from app.crud.calendar_cache import calendar_cache_db
from app.crud.document_cache import selected_document_db, document_cache_db, compute_content_hash
from app.crud.notification import notification_db
from app.schemas.notification import NotificationCreate, NotificationType

logger = logging.getLogger(__name__)


class SyncWorker:
    """Worker for synchronizing data from Google APIs."""

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.google_client = GoogleAPIClient(user_id)

    async def sync_all(self) -> dict:
        """Run full sync of all data sources."""
        log_id = sync_log_db.start_sync(self.user_id, "all")
        results = {
            "gmail": {"status": "pending", "items": 0},
            "calendar": {"status": "pending", "items": 0},
            "documents": {"status": "pending", "items": 0},
        }

        try:
            await send_sync_progress(self.user_id, "all", "in_progress", "Starting full sync...")

            # Sync Gmail
            await send_sync_progress(self.user_id, "gmail", "in_progress", "Syncing emails...")
            gmail_result = await self.sync_gmail()
            results["gmail"] = gmail_result

            # Sync Calendar
            await send_sync_progress(self.user_id, "calendar", "in_progress", "Syncing calendar...")
            calendar_result = await self.sync_calendar()
            results["calendar"] = calendar_result

            # Sync Documents
            await send_sync_progress(self.user_id, "documents", "in_progress", "Syncing documents...")
            docs_result = await self.sync_documents()
            results["documents"] = docs_result

            # Calculate total
            total_items = sum(r.get("items", 0) for r in results.values())
            sync_log_db.complete_sync(log_id, total_items)

            await send_sync_progress(self.user_id, "all", "completed", f"Synced {total_items} items")

            # Create notification
            notification_db.create(
                self.user_id,
                NotificationCreate(
                    type=NotificationType.SYNC_COMPLETE,
                    title="Sync completed",
                    message=f"Successfully synced {total_items} items from Google"
                )
            )

            return {"status": "completed", "results": results, "total_items": total_items}

        except Exception as e:
            logger.error(f"Full sync failed for user {self.user_id}: {e}")
            sync_log_db.fail_sync(log_id, str(e))
            await send_sync_progress(self.user_id, "all", "error", str(e))
            return {"status": "failed", "error": str(e), "results": results}

    async def sync_gmail(self) -> dict:
        """Sync Gmail messages."""
        log_id = sync_log_db.start_sync(self.user_id, "gmail")

        try:
            await send_sync_progress(self.user_id, "gmail", "in_progress", "Fetching emails...")

            # Fetch recent emails
            emails = self.google_client.get_recent_emails(
                max_results=settings.SYNC_EMAIL_MAX_RESULTS
            )

            # Store in cache
            count = email_cache_db.bulk_upsert(self.user_id, emails)

            sync_log_db.complete_sync(log_id, count)
            await send_sync_progress(self.user_id, "gmail", "completed", f"Synced {count} emails")

            logger.info(f"Gmail sync completed for user {self.user_id}: {count} emails")
            return {"status": "completed", "items": count}

        except Exception as e:
            logger.error(f"Gmail sync failed for user {self.user_id}: {e}")
            sync_log_db.fail_sync(log_id, str(e))
            await send_sync_progress(self.user_id, "gmail", "error", str(e))
            return {"status": "failed", "error": str(e), "items": 0}

    async def sync_calendar(self) -> dict:
        """Sync Google Calendar events."""
        log_id = sync_log_db.start_sync(self.user_id, "calendar")

        try:
            await send_sync_progress(self.user_id, "calendar", "in_progress", "Fetching calendar events...")

            # Fetch upcoming events
            events = self.google_client.get_upcoming_events(
                days_ahead=settings.SYNC_CALENDAR_DAYS_AHEAD
            )

            # Store in cache
            count = calendar_cache_db.bulk_upsert(self.user_id, events)

            sync_log_db.complete_sync(log_id, count)
            await send_sync_progress(self.user_id, "calendar", "completed", f"Synced {count} events")

            logger.info(f"Calendar sync completed for user {self.user_id}: {count} events")
            return {"status": "completed", "items": count}

        except Exception as e:
            logger.error(f"Calendar sync failed for user {self.user_id}: {e}")
            sync_log_db.fail_sync(log_id, str(e))
            await send_sync_progress(self.user_id, "calendar", "error", str(e))
            return {"status": "failed", "error": str(e), "items": 0}

    async def sync_documents(self) -> dict:
        """Sync selected Google Docs."""
        log_id = sync_log_db.start_sync(self.user_id, "documents")

        try:
            await send_sync_progress(self.user_id, "documents", "in_progress", "Fetching documents...")

            # Get selected documents
            selected_docs = selected_document_db.get_documents(self.user_id)
            count = 0

            for doc in selected_docs:
                try:
                    # Fetch document content
                    doc_content = self.google_client.get_document_content(doc['doc_id'])

                    # Compute content hash to check for changes
                    new_hash = compute_content_hash(doc_content.get('content', ''))

                    # Check if content changed
                    if doc.get('content_hash') != new_hash:
                        # Update document metadata
                        selected_document_db.update_document_sync(
                            doc['id'],
                            doc_content.get('last_modified'),
                            new_hash
                        )

                        # Save content to cache
                        document_cache_db.save_content(
                            doc['id'],
                            doc_content.get('content', ''),
                        )

                        logger.info(f"Document {doc['doc_id']} updated for user {self.user_id}")

                    count += 1

                except Exception as e:
                    logger.warning(f"Failed to sync document {doc['doc_id']}: {e}")
                    continue

            sync_log_db.complete_sync(log_id, count)
            await send_sync_progress(self.user_id, "documents", "completed", f"Synced {count} documents")

            logger.info(f"Documents sync completed for user {self.user_id}: {count} documents")
            return {"status": "completed", "items": count}

        except Exception as e:
            logger.error(f"Documents sync failed for user {self.user_id}: {e}")
            sync_log_db.fail_sync(log_id, str(e))
            await send_sync_progress(self.user_id, "documents", "error", str(e))
            return {"status": "failed", "error": str(e), "items": 0}


async def run_sync(user_id: int, sync_type: str) -> dict:
    """
    Run sync for a specific type or all.

    Args:
        user_id: User ID
        sync_type: Type of sync ('all', 'gmail', 'calendar', 'documents')

    Returns:
        Sync result dictionary
    """
    worker = SyncWorker(user_id)

    if sync_type == "all":
        return await worker.sync_all()
    elif sync_type == "gmail":
        return await worker.sync_gmail()
    elif sync_type == "calendar":
        return await worker.sync_calendar()
    elif sync_type == "documents":
        return await worker.sync_documents()
    else:
        raise ValueError(f"Unknown sync type: {sync_type}")

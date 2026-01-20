"""Taiga integration API routes for syncing tasks."""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.session import get_current_user
from app.core.config import settings
from app.core.taiga_client import TaigaClient
from app.crud.taiga import taiga_config_db, taiga_cards_db
from app.crud.task import task_db
from app.schemas.response import StandardResponse
from app.schemas.task import TaskStatus

logger = logging.getLogger(__name__)
router = APIRouter()


class TaigaConfigRequest(BaseModel):
    """Request to configure Taiga integration."""
    taiga_url: str
    # Auth: either token OR username/password
    auth_token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    # Project: either ID or slug
    project_id: Optional[int] = None  # Numeric project ID (optional if slug provided)
    project_slug: Optional[str] = None  # Project slug like "tecq-ai-bd" (from URL)


class SyncTasksRequest(BaseModel):
    """Request to sync tasks to Taiga."""
    task_ids: List[int]


class SyncResult(BaseModel):
    """Result of a sync operation."""
    task_id: int
    task_title: str
    action: str  # "created", "updated", "error"
    taiga_id: Optional[int] = None
    message: Optional[str] = None


class SyncResponse(BaseModel):
    """Response for sync operations."""
    synced_count: int
    error_count: int
    results: List[SyncResult]


class UpdateFromTaigaResponse(BaseModel):
    """Response for updating tasks from Taiga."""
    updated_count: int
    results: List[SyncResult]


def get_taiga_client(user_id: int) -> TaigaClient:
    """Get Taiga client with user or global configuration."""
    # Check for user-specific config first
    user_config = taiga_config_db.get_config(user_id)

    if user_config and user_config.get("is_active"):
        return TaigaClient(
            base_url=user_config["taiga_url"],
            auth_token=user_config["auth_token"],
            project_id=user_config["project_id"],
        )

    # Fall back to global settings (auth token OR username/password)
    if settings.TAIGA_URL and (
        settings.TAIGA_AUTH_TOKEN or
        (settings.TAIGA_USERNAME and settings.TAIGA_PASSWORD)
    ):
        return TaigaClient()

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Taiga integration not configured. Please configure Taiga in settings."
    )


@router.get("/config", response_model=StandardResponse[dict])
async def get_taiga_config(current_user: dict = Depends(get_current_user)):
    """Get current Taiga configuration."""
    user_config = taiga_config_db.get_config(current_user["id"])

    # Check global config (auth token OR username/password)
    has_global = bool(
        settings.TAIGA_URL and (
            settings.TAIGA_AUTH_TOKEN or
            (settings.TAIGA_USERNAME and settings.TAIGA_PASSWORD)
        )
    )

    return StandardResponse(
        status=True,
        data={
            "user_config": user_config,
            "has_global_config": has_global,
            "is_configured": bool(user_config and user_config.get("is_active")) or has_global,
        }
    )


@router.post("/config", response_model=StandardResponse[dict])
async def save_taiga_config(
    request: TaigaConfigRequest,
    current_user: dict = Depends(get_current_user)
):
    """Save Taiga configuration for the user."""
    # Validate auth credentials
    if not request.auth_token and not (request.username and request.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either auth_token or username/password must be provided"
        )

    if not request.project_id and not request.project_slug:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either project_id or project_slug must be provided"
        )

    # Validate connection by trying to get project
    try:
        client = TaigaClient(
            base_url=request.taiga_url,
            auth_token=request.auth_token,
            username=request.username,
            password=request.password,
            project_id=request.project_slug or request.project_id,
        )
        project = await client.get_project()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not connect to Taiga or project not found"
            )

        # Get the resolved numeric project ID and the auth token (may have been generated from login)
        resolved_project_id = project.get("id")
        resolved_auth_token = client._auth_token  # Token from login if username/password was used
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to connect to Taiga: {str(e)}"
        )

    # Save configuration with resolved project ID and auth token
    success = taiga_config_db.upsert_config(
        user_id=current_user["id"],
        taiga_url=request.taiga_url,
        auth_token=resolved_auth_token,  # Save the resolved token
        project_id=resolved_project_id,
        is_active=True,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save configuration"
        )

    return StandardResponse(
        status=True,
        data={
            "project_name": project.get("name"),
            "project_id": resolved_project_id,
            "project_slug": project.get("slug"),
        },
        message=f"Connected to Taiga project: {project.get('name')}"
    )


@router.post("/sync-tasks", response_model=StandardResponse[SyncResponse])
async def sync_tasks_to_taiga(
    request: SyncTasksRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Sync selected tasks to Taiga.
    - Creates new user story in Taiga if task is not linked
    - Updates status from Taiga if already linked
    """
    if not request.task_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No tasks provided"
        )

    client = get_taiga_client(current_user["id"])
    statuses = await client.get_project_statuses()

    results = []
    synced_count = 0
    error_count = 0

    for task_id in request.task_ids:
        # Get task
        task = task_db.get_by_id(task_id, current_user["id"])
        if not task:
            results.append(SyncResult(
                task_id=task_id,
                task_title="Unknown",
                action="error",
                message="Task not found"
            ))
            error_count += 1
            continue

        # Check if already linked to Taiga
        existing_card = taiga_cards_db.get_card_by_task_id(current_user["id"], task_id)

        try:
            if existing_card:
                # Task is already linked - update status and dates from Taiga
                taiga_story = await client.get_user_story(existing_card["card_id"])
                if taiga_story:
                    taiga_status_name = taiga_story.get("status_extra_info", {}).get("name", "")
                    new_task_status_str = client.map_taiga_status_to_task(taiga_status_name)
                    new_task_status = TaskStatus(new_task_status_str)

                    # Extract dates from Taiga story
                    dates = client.extract_dates_from_story(taiga_story)

                    # Build update dict with status and dates
                    update_data = {
                        "status": new_task_status_str,
                    }
                    update_messages = [f"Status: {new_task_status_str}"]

                    if dates.get("start_date"):
                        update_data["start_date"] = dates["start_date"]
                        update_messages.append(f"Start: {dates['start_date'].strftime('%Y-%m-%d')}")

                    if dates.get("due_date"):
                        update_data["due_date"] = dates["due_date"]
                        update_messages.append(f"Due: {dates['due_date'].strftime('%Y-%m-%d')}")

                    if dates.get("completed_date"):
                        update_data["completed_date"] = dates["completed_date"]
                        update_messages.append(f"Completed: {dates['completed_date'].strftime('%Y-%m-%d')}")
                    elif new_task_status_str != "done":
                        update_data["completed_date"] = None

                    # Update task with all fields
                    task_db.update_from_dict(task_id, current_user["id"], update_data)

                    # Update card record
                    taiga_cards_db.update_card_status(
                        existing_card["id"],
                        current_user["id"],
                        taiga_status_name
                    )

                    results.append(SyncResult(
                        task_id=task_id,
                        task_title=task.title,
                        action="updated",
                        taiga_id=existing_card["card_id"],
                        message=" | ".join(update_messages)
                    ))
                    synced_count += 1
                else:
                    results.append(SyncResult(
                        task_id=task_id,
                        task_title=task.title,
                        action="error",
                        message="Taiga story not found"
                    ))
                    error_count += 1
            else:
                # Task not linked - create in Taiga
                # First check if story with same subject exists
                existing_story = await client.search_user_story_by_subject(task.title)

                if existing_story:
                    # Link to existing story
                    taiga_cards_db.create_card(
                        user_id=current_user["id"],
                        card_id=existing_story["id"],
                        card_type="userstory",
                        subject=existing_story["subject"],
                        status=existing_story.get("status_extra_info", {}).get("name", ""),
                        task_id=task_id,
                    )

                    results.append(SyncResult(
                        task_id=task_id,
                        task_title=task.title,
                        action="updated",
                        taiga_id=existing_story["id"],
                        message="Linked to existing Taiga story"
                    ))
                    synced_count += 1
                else:
                    # Create new story
                    target_status_id = client.map_task_status_to_taiga(task.status.value, statuses)

                    description = task.description or ""
                    if task.project:
                        description = f"**Project:** {task.project}\n\n{description}"

                    # Combine project, priority and task tags
                    all_tags = []
                    if task.project:
                        all_tags.append(task.project)
                    # Add priority as a tag (after project name)
                    if task.priority:
                        priority_tag = f"priority:{task.priority.value}"
                        all_tags.append(priority_tag)
                    if task.tags:
                        all_tags.extend(task.tags)

                    # Format due date for Taiga (YYYY-MM-DD)
                    due_date_str = None
                    if task.due_date:
                        try:
                            from datetime import datetime
                            if isinstance(task.due_date, str):
                                # Parse ISO format string
                                dt = datetime.fromisoformat(task.due_date.replace("Z", "+00:00"))
                            else:
                                dt = task.due_date
                            due_date_str = dt.strftime("%Y-%m-%d")
                        except Exception as e:
                            logger.warning(f"Could not parse due_date for task {task_id}: {e}")

                    new_story = await client.create_user_story(
                        subject=task.title,
                        description=description,
                        status_id=target_status_id,
                        tags=all_tags if all_tags else None,
                        due_date=due_date_str,
                    )

                    if new_story:
                        # Build Taiga URL for the user story
                        project_slug = new_story.get("project_extra_info", {}).get("slug", "")
                        story_ref = new_story.get("ref", new_story["id"])
                        taiga_url = f"{client.base_url}/project/{project_slug}/us/{story_ref}"

                        # Create card link
                        taiga_cards_db.create_card(
                            user_id=current_user["id"],
                            card_id=new_story["id"],
                            card_type="userstory",
                            subject=new_story["subject"],
                            status=new_story.get("status_extra_info", {}).get("name", ""),
                            task_id=task_id,
                        )

                        # Update task with source info including URL
                        task_db.update_from_dict(task_id, current_user["id"], {
                            "source_type": "taiga",
                            "source_id": str(new_story["id"]),
                            "source_url": taiga_url,
                        })

                        results.append(SyncResult(
                            task_id=task_id,
                            task_title=task.title,
                            action="created",
                            taiga_id=new_story["id"],
                            message="Created in Taiga"
                        ))
                        synced_count += 1
                    else:
                        results.append(SyncResult(
                            task_id=task_id,
                            task_title=task.title,
                            action="error",
                            message="Failed to create in Taiga"
                        ))
                        error_count += 1

        except Exception as e:
            logger.error(f"Error syncing task {task_id}: {e}")
            results.append(SyncResult(
                task_id=task_id,
                task_title=task.title if task else "Unknown",
                action="error",
                message=str(e)
            ))
            error_count += 1

    # Update last sync timestamp
    taiga_config_db.update_last_sync(current_user["id"])

    return StandardResponse(
        status=True,
        data=SyncResponse(
            synced_count=synced_count,
            error_count=error_count,
            results=results
        ),
        message=f"Synced {synced_count} tasks, {error_count} errors"
    )


@router.post("/update-from-taiga", response_model=StandardResponse[UpdateFromTaigaResponse])
async def update_all_from_taiga(current_user: dict = Depends(get_current_user)):
    """
    Update all linked tasks from Taiga.
    Syncs: status, start_date (from created_date), due_date, completed_date (from finish_date).
    Only updates tasks that are already connected to Taiga.
    """
    client = get_taiga_client(current_user["id"])

    # Get all linked cards
    linked_cards = taiga_cards_db.get_all_linked_cards(current_user["id"])

    if not linked_cards:
        return StandardResponse(
            status=True,
            data=UpdateFromTaigaResponse(updated_count=0, results=[]),
            message="No tasks linked to Taiga"
        )

    results = []
    updated_count = 0

    for card in linked_cards:
        try:
            taiga_story = await client.get_user_story(card["card_id"])
            if taiga_story:
                # Extract status
                taiga_status_name = taiga_story.get("status_extra_info", {}).get("name", "")
                new_task_status_str = client.map_taiga_status_to_task(taiga_status_name)
                new_task_status = TaskStatus(new_task_status_str)

                # Extract dates from Taiga story
                dates = client.extract_dates_from_story(taiga_story)

                # Build update dict with status and dates
                update_data = {
                    "status": new_task_status_str,
                }

                # Add dates if they exist in Taiga
                update_messages = [f"Status: {taiga_status_name} -> {new_task_status_str}"]

                if dates.get("start_date"):
                    update_data["start_date"] = dates["start_date"]
                    update_messages.append(f"Start: {dates['start_date'].strftime('%Y-%m-%d')}")

                if dates.get("due_date"):
                    update_data["due_date"] = dates["due_date"]
                    update_messages.append(f"Due: {dates['due_date'].strftime('%Y-%m-%d')}")

                if dates.get("completed_date"):
                    update_data["completed_date"] = dates["completed_date"]
                    update_messages.append(f"Completed: {dates['completed_date'].strftime('%Y-%m-%d')}")
                elif new_task_status_str != "done":
                    # Clear completed_date if status is not done
                    update_data["completed_date"] = None

                # Update task with all fields
                task_db.update_from_dict(card["task_id"], current_user["id"], update_data)

                # Update card record
                taiga_cards_db.update_card_status(card["id"], current_user["id"], taiga_status_name)

                results.append(SyncResult(
                    task_id=card["task_id"],
                    task_title=card.get("task_title", "Unknown"),
                    action="updated",
                    taiga_id=card["card_id"],
                    message=" | ".join(update_messages)
                ))
                updated_count += 1
            else:
                results.append(SyncResult(
                    task_id=card["task_id"],
                    task_title=card.get("task_title", "Unknown"),
                    action="error",
                    taiga_id=card["card_id"],
                    message="Taiga story not found"
                ))
        except Exception as e:
            logger.error(f"Error updating from Taiga for card {card['id']}: {e}")
            results.append(SyncResult(
                task_id=card["task_id"],
                task_title=card.get("task_title", "Unknown"),
                action="error",
                taiga_id=card["card_id"],
                message=str(e)
            ))

    # Update last sync timestamp
    taiga_config_db.update_last_sync(current_user["id"])

    return StandardResponse(
        status=True,
        data=UpdateFromTaigaResponse(updated_count=updated_count, results=results),
        message=f"Updated {updated_count} tasks from Taiga"
    )


@router.get("/linked-tasks", response_model=StandardResponse[list])
async def get_linked_tasks(current_user: dict = Depends(get_current_user)):
    """Get all tasks that are linked to Taiga."""
    linked_cards = taiga_cards_db.get_all_linked_cards(current_user["id"])
    return StandardResponse(status=True, data=linked_cards)

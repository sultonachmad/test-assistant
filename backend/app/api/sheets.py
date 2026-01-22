"""Google Sheets API routes for managing sheet sync configurations."""
import logging
from typing import Optional, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from pydantic import BaseModel

from app.core.session import get_current_user
from app.core.google_api_client import GoogleAPIClient
from app.crud.sheet_sync import sheet_sync_db
from app.crud.task import task_db
from app.crud.google_token import google_token_db
from app.schemas.response import StandardResponse

logger = logging.getLogger(__name__)
router = APIRouter()


class FieldMapping(BaseModel):
    """Field mapping from sheet column to task field."""
    title: str  # Required: column name for task title
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    project: Optional[str] = None
    start_date: Optional[str] = None
    due_date: Optional[str] = None
    completed_date: Optional[str] = None
    assigned_to: Optional[str] = None
    tags: Optional[str] = None


class CreateSheetSyncRequest(BaseModel):
    """Request to create a new sheet sync configuration."""
    spreadsheet_id: str
    sheet_name: str
    field_mapping: FieldMapping
    auto_sync: bool = True
    sync_interval_minutes: int = 15


class UpdateSheetSyncRequest(BaseModel):
    """Request to update a sheet sync configuration."""
    field_mapping: Optional[FieldMapping] = None
    auto_sync: Optional[bool] = None
    sync_interval_minutes: Optional[int] = None


# Task field info for frontend
TASK_FIELDS = [
    {"name": "title", "label": "Title", "required": True, "description": "Task title (required)"},
    {"name": "description", "label": "Description", "required": False, "description": "Task description"},
    {"name": "status", "label": "Status", "required": False, "description": "Task status (done, in_progress, on_hold, assigned)"},
    {"name": "priority", "label": "Priority", "required": False, "description": "Priority level (low, medium, high, urgent)"},
    {"name": "project", "label": "Project", "required": False, "description": "Project name this task belongs to"},
    {"name": "start_date", "label": "Start Date", "required": False, "description": "When task work started (YYYY-MM-DD format)"},
    {"name": "due_date", "label": "Due Date", "required": False, "description": "Target completion date (YYYY-MM-DD format)"},
    {"name": "completed_date", "label": "Completed Date", "required": False, "description": "Actual completion date (YYYY-MM-DD format)"},
    {"name": "assigned_to", "label": "Assigned To", "required": False, "description": "Team member this task is assigned to"},
    {"name": "tags", "label": "Tags", "required": False, "description": "Comma-separated tags"},
]


@router.get("/task-fields", response_model=StandardResponse[list])
async def get_task_fields(current_user: dict = Depends(get_current_user)):
    """Get available task fields for mapping."""
    return StandardResponse(status=True, data=TASK_FIELDS)


@router.get("/spreadsheets", response_model=StandardResponse[list])
async def list_spreadsheets(
    limit: int = Query(20, ge=1, le=50),
    current_user: dict = Depends(get_current_user)
):
    """List recent Google Sheets the user has access to."""
    if not google_token_db.is_token_valid(current_user["id"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account not connected"
        )

    try:
        client = GoogleAPIClient(current_user["id"])
        spreadsheets = client.list_spreadsheets(max_results=limit)
        return StandardResponse(status=True, data=spreadsheets)
    except Exception as e:
        logger.error(f"Failed to list spreadsheets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list spreadsheets: {str(e)}"
        )


@router.get("/spreadsheets/{spreadsheet_id}", response_model=StandardResponse[dict])
async def get_spreadsheet_info(
    spreadsheet_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get spreadsheet info including list of sheets."""
    if not google_token_db.is_token_valid(current_user["id"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account not connected"
        )

    try:
        client = GoogleAPIClient(current_user["id"])
        info = client.get_spreadsheet_info(spreadsheet_id)
        return StandardResponse(status=True, data=info)
    except Exception as e:
        logger.error(f"Failed to get spreadsheet info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get spreadsheet info: {str(e)}"
        )


@router.get("/spreadsheets/{spreadsheet_id}/sheets/{sheet_name}/headers", response_model=StandardResponse[list])
async def get_sheet_headers(
    spreadsheet_id: str,
    sheet_name: str,
    current_user: dict = Depends(get_current_user)
):
    """Get column headers from a specific sheet."""
    if not google_token_db.is_token_valid(current_user["id"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account not connected"
        )

    try:
        client = GoogleAPIClient(current_user["id"])
        headers = client.get_sheet_headers(spreadsheet_id, sheet_name)
        return StandardResponse(status=True, data=headers)
    except Exception as e:
        logger.error(f"Failed to get sheet headers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sheet headers: {str(e)}"
        )


@router.get("/spreadsheets/{spreadsheet_id}/sheets/{sheet_name}/preview", response_model=StandardResponse[dict])
async def preview_sheet_data(
    spreadsheet_id: str,
    sheet_name: str,
    limit: int = Query(5, ge=1, le=20),
    current_user: dict = Depends(get_current_user)
):
    """Preview sheet data (first few rows)."""
    if not google_token_db.is_token_valid(current_user["id"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account not connected"
        )

    try:
        client = GoogleAPIClient(current_user["id"])
        data = client.get_sheet_data(spreadsheet_id, sheet_name)
        # Return only first N rows for preview
        preview_rows = data['rows'][:limit] if data['rows'] else []
        return StandardResponse(status=True, data={
            'headers': data['headers'],
            'rows': preview_rows,
            'total_rows': len(data['rows'])
        })
    except Exception as e:
        logger.error(f"Failed to preview sheet data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to preview sheet data: {str(e)}"
        )


@router.get("/configs", response_model=StandardResponse[list])
async def get_sheet_sync_configs(
    active_only: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """Get all sheet sync configurations."""
    configs = sheet_sync_db.get_all_configs(current_user["id"], active_only)
    return StandardResponse(status=True, data=configs)


@router.get("/configs/{config_id}", response_model=StandardResponse[dict])
async def get_sheet_sync_config(
    config_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific sheet sync configuration."""
    config = sheet_sync_db.get_config_by_id(config_id, current_user["id"])
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuration not found")
    return StandardResponse(status=True, data=config)


@router.post("/configs", response_model=StandardResponse[dict])
async def create_sheet_sync_config(
    request: CreateSheetSyncRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a new sheet sync configuration."""
    if not google_token_db.is_token_valid(current_user["id"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account not connected"
        )

    # Get spreadsheet info for name and URL
    try:
        client = GoogleAPIClient(current_user["id"])
        info = client.get_spreadsheet_info(request.spreadsheet_id)
        spreadsheet_name = info.get('title', 'Unknown')
        spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{request.spreadsheet_id}"
    except Exception as e:
        logger.warning(f"Could not get spreadsheet info: {e}")
        spreadsheet_name = "Unknown"
        spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{request.spreadsheet_id}"

    config_id = sheet_sync_db.create_config(
        user_id=current_user["id"],
        spreadsheet_id=request.spreadsheet_id,
        spreadsheet_name=spreadsheet_name,
        spreadsheet_url=spreadsheet_url,
        sheet_name=request.sheet_name,
        field_mapping=request.field_mapping.model_dump(exclude_none=True),
        auto_sync=request.auto_sync,
        sync_interval_minutes=request.sync_interval_minutes
    )

    if not config_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create configuration"
        )

    config = sheet_sync_db.get_config_by_id(config_id, current_user["id"])
    return StandardResponse(
        status=True,
        data=config,
        message="Sheet sync configuration created successfully"
    )


@router.patch("/configs/{config_id}", response_model=StandardResponse[dict])
async def update_sheet_sync_config(
    config_id: int,
    request: UpdateSheetSyncRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update a sheet sync configuration."""
    config = sheet_sync_db.get_config_by_id(config_id, current_user["id"])
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuration not found")

    success = sheet_sync_db.update_config(
        config_id=config_id,
        user_id=current_user["id"],
        field_mapping=request.field_mapping.model_dump(exclude_none=True) if request.field_mapping else None,
        auto_sync=request.auto_sync,
        sync_interval_minutes=request.sync_interval_minutes
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update configuration"
        )

    updated_config = sheet_sync_db.get_config_by_id(config_id, current_user["id"])
    return StandardResponse(
        status=True,
        data=updated_config,
        message="Configuration updated successfully"
    )


@router.delete("/configs/{config_id}", response_model=StandardResponse)
async def delete_sheet_sync_config(
    config_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Delete a sheet sync configuration."""
    if not sheet_sync_db.delete_config(config_id, current_user["id"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuration not found")

    return StandardResponse(status=True, message="Configuration deleted successfully")


@router.post("/configs/{config_id}/sync", response_model=StandardResponse[dict])
async def sync_sheet_tasks(
    config_id: int,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Manually trigger sync for a sheet configuration."""
    config = sheet_sync_db.get_config_by_id(config_id, current_user["id"])
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuration not found")

    if not google_token_db.is_token_valid(current_user["id"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account not connected"
        )

    # Run sync in background
    background_tasks.add_task(
        run_sheet_sync,
        current_user["id"],
        config_id
    )

    return StandardResponse(
        status=True,
        data={"config_id": config_id, "status": "started"},
        message="Sync started in background"
    )


def get_field_value(field_mapping: dict, field_name: str, row: dict) -> str | None:
    """
    Get value for a field from either a column or custom value.
    Custom values are prefixed with 'custom:'.
    Returns None if field is not mapped.
    """
    mapping = field_mapping.get(field_name)
    if not mapping:
        return None

    if mapping.startswith('custom:'):
        # Custom/hardcoded value
        return mapping[7:]  # Remove 'custom:' prefix
    else:
        # Column mapping - get value from row
        return row.get(mapping)


async def run_sheet_sync(user_id: int, config_id: int):
    """Background task to sync tasks from a Google Sheet."""
    try:
        config = sheet_sync_db.get_config_by_id(config_id, user_id)
        if not config:
            logger.error(f"Sheet sync config {config_id} not found")
            return

        client = GoogleAPIClient(user_id)
        rows = client.get_sheet_rows_as_dicts(
            config['spreadsheet_id'],
            config['sheet_name']
        )

        field_mapping = config['field_mapping']
        synced_count = 0

        for row in rows:
            # Skip empty rows (no title)
            title_value = get_field_value(field_mapping, 'title', row)
            if not title_value:
                continue

            # Map fields
            task_data = {
                'title': title_value.strip(),
                'source_type': 'google_sheet',
                'source_id': f"{config['spreadsheet_id']}:{config['sheet_name']}",
                'source_url': config['spreadsheet_url'],
            }

            # Map optional fields using helper that supports custom values
            description = get_field_value(field_mapping, 'description', row)
            if description:
                task_data['description'] = description

            status_value = get_field_value(field_mapping, 'status', row)
            if status_value:
                status_value = status_value.lower().strip()
                # Map common status values
                status_map = {
                    'done': 'done',
                    'completed': 'done',
                    'finish': 'done',
                    'finished': 'done',
                    'in progress': 'in_progress',
                    'in-progress': 'in_progress',
                    'ongoing': 'in_progress',
                    'wip': 'in_progress',
                    'on hold': 'on_hold',
                    'on-hold': 'on_hold',
                    'hold': 'on_hold',
                    'pending': 'on_hold',
                    'assigned': 'assigned',
                    'new': 'assigned',
                    'todo': 'assigned',
                    'to do': 'assigned',
                }
                task_data['status'] = status_map.get(status_value, 'assigned')

            priority_value = get_field_value(field_mapping, 'priority', row)
            if priority_value:
                priority_value = priority_value.lower().strip()
                priority_map = {
                    'low': 'low',
                    'medium': 'medium',
                    'normal': 'medium',
                    'high': 'high',
                    'urgent': 'urgent',
                    'critical': 'urgent',
                }
                task_data['priority'] = priority_map.get(priority_value, 'medium')

            project = get_field_value(field_mapping, 'project', row)
            if project:
                task_data['project'] = project.strip()

            start_date = get_field_value(field_mapping, 'start_date', row)
            if start_date:
                task_data['start_date'] = start_date

            due_date = get_field_value(field_mapping, 'due_date', row)
            if due_date:
                task_data['due_date'] = due_date

            completed_date = get_field_value(field_mapping, 'completed_date', row)
            if completed_date:
                task_data['completed_date'] = completed_date

            assigned_to = get_field_value(field_mapping, 'assigned_to', row)
            if assigned_to:
                task_data['assigned_to'] = assigned_to

            tags = get_field_value(field_mapping, 'tags', row)
            if tags:
                task_data['tags'] = [t.strip() for t in tags.split(',')]

            # Create or update task
            # Check if task with same title and source exists
            existing_task = task_db.find_by_source(
                user_id,
                task_data['source_type'],
                task_data['source_id'],
                task_data['title']
            )

            if existing_task:
                # Update existing task
                task_db.update_from_dict(existing_task['id'], user_id, task_data)
            else:
                # Create new task
                task_db.create_from_dict(user_id, task_data)

            synced_count += 1

        # Update sync status
        sheet_sync_db.update_sync_status(config_id, synced_count)
        logger.info(f"Sheet sync completed for config {config_id}: {synced_count} tasks")

    except Exception as e:
        logger.error(f"Sheet sync failed for config {config_id}: {e}")

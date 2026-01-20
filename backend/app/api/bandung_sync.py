"""Bandung Resource Sync API routes."""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query

from app.core.session import get_current_user
from app.core.google_api_client import GoogleAPIClient
from app.crud.bandung_sync import bandung_sync_db
from app.crud.task import task_db
from app.crud.google_token import google_token_db
from app.schemas.bandung_sync import (
    CreateBandungSyncRequest,
    UpdateBandungSyncRequest,
    BandungSyncResult,
    BandungSyncTaskPreview
)
from app.schemas.response import StandardResponse

logger = logging.getLogger(__name__)
router = APIRouter()


def format_date_for_sheet(date_str: Optional[str]) -> str:
    """Format date for Google Sheets (DD/MM/YYYY)."""
    if not date_str:
        return ""
    try:
        # Parse ISO format
        if "T" in date_str:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        else:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return str(date_str)


def format_status_for_sheet(status: str) -> str:
    """Format task status for Google Sheets."""
    status_map = {
        "done": "Done",
        "in_progress": "In Progress",
        "on_hold": "On Hold",
        "assigned": "Assigned"
    }
    return status_map.get(status, status)


@router.get("/config", response_model=StandardResponse)
async def get_bandung_sync_config(current_user: dict = Depends(get_current_user)):
    """Get Bandung Resource sync configuration."""
    config = bandung_sync_db.get_config(current_user["id"])
    return StandardResponse(status=True, data=config)


@router.post("/config", response_model=StandardResponse)
async def create_bandung_sync_config(
    request: CreateBandungSyncRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create Bandung Resource sync configuration."""
    if not google_token_db.is_token_valid(current_user["id"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account not connected"
        )

    # Get spreadsheet info
    try:
        client = GoogleAPIClient(current_user["id"])
        info = client.get_spreadsheet_info(request.spreadsheet_id)
        spreadsheet_name = info.get('title', 'Unknown')
        spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{request.spreadsheet_id}"
    except Exception as e:
        logger.warning(f"Could not get spreadsheet info: {e}")
        spreadsheet_name = "Unknown"
        spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{request.spreadsheet_id}"

    config_id = bandung_sync_db.create_config(
        user_id=current_user["id"],
        spreadsheet_id=request.spreadsheet_id,
        spreadsheet_name=spreadsheet_name,
        spreadsheet_url=spreadsheet_url,
        column_mapping=request.column_mapping.model_dump(),
        assignee_sheet_mapping=request.assignee_sheet_mapping
    )

    if not config_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create configuration"
        )

    config = bandung_sync_db.get_config_by_id(config_id, current_user["id"])
    return StandardResponse(
        status=True,
        data=config,
        message="Bandung Resource sync configuration created successfully"
    )


@router.patch("/config/{config_id}", response_model=StandardResponse)
async def update_bandung_sync_config(
    config_id: int,
    request: UpdateBandungSyncRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update Bandung Resource sync configuration."""
    config = bandung_sync_db.get_config_by_id(config_id, current_user["id"])
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuration not found")

    success = bandung_sync_db.update_config(
        config_id=config_id,
        user_id=current_user["id"],
        column_mapping=request.column_mapping.model_dump() if request.column_mapping else None,
        assignee_sheet_mapping=request.assignee_sheet_mapping,
        is_active=request.is_active
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update configuration"
        )

    updated_config = bandung_sync_db.get_config_by_id(config_id, current_user["id"])
    return StandardResponse(
        status=True,
        data=updated_config,
        message="Configuration updated successfully"
    )


@router.delete("/config/{config_id}", response_model=StandardResponse)
async def delete_bandung_sync_config(
    config_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Delete Bandung Resource sync configuration."""
    if not bandung_sync_db.delete_config(config_id, current_user["id"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuration not found")

    return StandardResponse(status=True, message="Configuration deleted successfully")


@router.get("/assignees", response_model=StandardResponse[list])
async def get_task_assignees(current_user: dict = Depends(get_current_user)):
    """Get unique assignees from tasks for mapping."""
    assignees = task_db.get_assignees(current_user["id"])
    return StandardResponse(status=True, data=assignees)


@router.get("/preview", response_model=StandardResponse[list])
async def preview_sync_tasks(
    assigned_to: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Preview tasks that would be synced."""
    # Get tasks with start_date
    tasks, _ = task_db.get_all(
        user_id=current_user["id"],
        assigned_to=assigned_to,
        page=1,
        limit=100  # Limit preview
    )

    # Filter to tasks with start_date
    preview_tasks = []
    config = bandung_sync_db.get_config(current_user["id"])
    assignee_mapping = config.get('assignee_sheet_mapping', {}) if config else {}

    for task in tasks:
        if task.start_date:
            preview_tasks.append(BandungSyncTaskPreview(
                task_id=task.id,
                title=task.title,
                assigned_to=task.assigned_to,
                start_date=format_date_for_sheet(str(task.start_date) if task.start_date else None),
                status=format_status_for_sheet(task.status.value),
                source_url=task.source_url,
                target_sheet=assignee_mapping.get(task.assigned_to) if task.assigned_to else None
            ))

    return StandardResponse(status=True, data=preview_tasks)


@router.post("/sync", response_model=StandardResponse[BandungSyncResult])
async def sync_tasks_to_sheet(
    background_tasks: BackgroundTasks,
    sync_all: bool = Query(False, description="Sync all tasks or only new ones"),
    current_user: dict = Depends(get_current_user)
):
    """Sync tasks to Google Sheet."""
    config = bandung_sync_db.get_config(current_user["id"])
    if not config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bandung Resource sync not configured. Please configure the sync first."
        )

    if not google_token_db.is_token_valid(current_user["id"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account not connected"
        )

    # Run sync synchronously for now (can be moved to background if needed)
    result = await run_bandung_sync(current_user["id"], config, sync_all)

    return StandardResponse(
        status=True,
        data=result,
        message=f"Synced {result.synced_tasks} tasks to Google Sheet"
    )


async def run_bandung_sync(
    user_id: int,
    config: Dict[str, Any],
    sync_all: bool = False
) -> BandungSyncResult:
    """Execute Bandung Resource sync."""
    result = BandungSyncResult(
        total_tasks=0,
        synced_tasks=0,
        updated_tasks=0,
        new_tasks=0,
        skipped_tasks=0,
        errors=[],
        by_sheet={}
    )

    try:
        client = GoogleAPIClient(user_id)
        column_mapping = config['column_mapping']
        assignee_mapping = config['assignee_sheet_mapping']
        spreadsheet_id = config['spreadsheet_id']

        # Get tasks with start_date
        tasks, total = task_db.get_all(
            user_id=user_id,
            page=1,
            limit=1000  # Get all tasks
        )
        result.total_tasks = total

        # Group tasks by assigned_to -> sheet
        tasks_by_sheet: Dict[str, List[Any]] = {}

        for task in tasks:
            if not task.start_date:
                result.skipped_tasks += 1
                continue

            if not task.assigned_to or task.assigned_to not in assignee_mapping:
                result.skipped_tasks += 1
                continue

            sheet_name = assignee_mapping[task.assigned_to]
            if sheet_name not in tasks_by_sheet:
                tasks_by_sheet[sheet_name] = []
            tasks_by_sheet[sheet_name].append(task)

        # Process each sheet
        for sheet_name, sheet_tasks in tasks_by_sheet.items():
            try:
                # Get existing data from sheet to check for updates
                existing_data = {}
                try:
                    sheet_data = client.get_sheet_data(spreadsheet_id, sheet_name)
                    headers = sheet_data.get('headers', [])

                    # Find the task details column index
                    task_details_col = column_mapping.get('task_details', 'Task Details')
                    task_col_idx = headers.index(task_details_col) if task_details_col in headers else -1

                    if task_col_idx >= 0:
                        for row_num, row in enumerate(sheet_data.get('rows', []), start=2):
                            if row_num > 1 and len(row) > task_col_idx:
                                existing_data[row[task_col_idx].strip()] = row_num
                except Exception as e:
                    logger.warning(f"Could not read existing sheet data: {e}")

                sheet_count = 0
                for task in sheet_tasks:
                    try:
                        # Prepare row data based on column mapping
                        row_data = {
                            column_mapping['start_date']: format_date_for_sheet(
                                str(task.start_date) if task.start_date else None
                            ),
                            column_mapping['hours']: "8",
                            column_mapping['task_details']: task.title,
                            column_mapping['status']: format_status_for_sheet(task.status.value),
                            column_mapping['links']: task.source_url or ""
                        }

                        # Check if task already exists in sheet
                        existing_row = existing_data.get(task.title.strip())

                        if existing_row:
                            # Update existing row
                            # Get headers to build row in correct order
                            try:
                                headers = client.get_sheet_headers(spreadsheet_id, sheet_name)
                                row_values = []
                                for header in headers:
                                    if header in row_data:
                                        row_values.append(row_data[header])
                                    else:
                                        row_values.append("")  # Keep existing value placeholder

                                # Only update the mapped columns
                                updates = []
                                for col_name, value in row_data.items():
                                    if col_name in headers:
                                        col_idx = headers.index(col_name)
                                        col_letter = chr(ord('A') + col_idx)
                                        updates.append({
                                            'range': f"{col_letter}{existing_row}",
                                            'values': [[value]]
                                        })

                                if updates:
                                    client.batch_update_sheet(spreadsheet_id, sheet_name, updates)
                                    result.updated_tasks += 1
                            except Exception as e:
                                logger.error(f"Error updating row: {e}")
                                result.errors.append(f"Failed to update task '{task.title}': {str(e)}")
                        else:
                            # Append new row
                            try:
                                headers = client.get_sheet_headers(spreadsheet_id, sheet_name)
                                row_values = []
                                for header in headers:
                                    if header in row_data:
                                        row_values.append(row_data[header])
                                    else:
                                        row_values.append("")

                                client.append_sheet_rows(spreadsheet_id, sheet_name, [row_values])
                                result.new_tasks += 1
                            except Exception as e:
                                logger.error(f"Error appending row: {e}")
                                result.errors.append(f"Failed to add task '{task.title}': {str(e)}")

                        result.synced_tasks += 1
                        sheet_count += 1

                    except Exception as e:
                        logger.error(f"Error syncing task {task.id}: {e}")
                        result.errors.append(f"Failed to sync task '{task.title}': {str(e)}")

                result.by_sheet[sheet_name] = sheet_count

            except Exception as e:
                logger.error(f"Error processing sheet {sheet_name}: {e}")
                result.errors.append(f"Failed to process sheet '{sheet_name}': {str(e)}")

        # Update sync status
        bandung_sync_db.update_sync_status(config['id'], result.synced_tasks)

    except Exception as e:
        logger.error(f"Bandung sync failed: {e}")
        result.errors.append(f"Sync failed: {str(e)}")

    return result

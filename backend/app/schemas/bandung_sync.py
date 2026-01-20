"""Bandung Resource Sync schemas."""
from typing import Optional, Dict, List, Any
from datetime import datetime
from pydantic import BaseModel
from enum import Enum


class BandungSyncColumnMapping(BaseModel):
    """Column mapping for Bandung Resource sync."""
    start_date: str  # Column name for start date
    hours: str  # Column name for hours (will be set to 8)
    task_details: str  # Column name for task title
    status: str  # Column name for status
    links: str  # Column name for Taiga links


class BandungSyncConfig(BaseModel):
    """Configuration for Bandung Resource sync."""
    id: Optional[int] = None
    user_id: Optional[int] = None
    spreadsheet_id: str
    spreadsheet_name: Optional[str] = None
    spreadsheet_url: Optional[str] = None
    column_mapping: BandungSyncColumnMapping
    assignee_sheet_mapping: Dict[str, str]  # assigned_to -> sheet_name mapping
    is_active: bool = True
    last_sync: Optional[datetime] = None
    last_sync_count: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CreateBandungSyncRequest(BaseModel):
    """Request to create Bandung Resource sync configuration."""
    spreadsheet_id: str
    column_mapping: BandungSyncColumnMapping
    assignee_sheet_mapping: Dict[str, str]  # assigned_to -> sheet_name


class UpdateBandungSyncRequest(BaseModel):
    """Request to update Bandung Resource sync configuration."""
    column_mapping: Optional[BandungSyncColumnMapping] = None
    assignee_sheet_mapping: Optional[Dict[str, str]] = None
    is_active: Optional[bool] = None


class BandungSyncResult(BaseModel):
    """Result of a Bandung Resource sync operation."""
    total_tasks: int
    synced_tasks: int
    updated_tasks: int
    new_tasks: int
    skipped_tasks: int
    errors: List[str] = []
    by_sheet: Dict[str, int] = {}  # sheet_name -> count


class BandungSyncTaskPreview(BaseModel):
    """Preview of a task for Bandung sync."""
    task_id: int
    title: str
    assigned_to: Optional[str]
    start_date: Optional[str]
    status: str
    source_url: Optional[str]
    target_sheet: Optional[str]

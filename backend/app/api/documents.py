"""Documents API routes for managing monitored Google Docs."""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel

from app.core.session import get_current_user
from app.core.google_api_client import GoogleAPIClient
from app.crud.document_cache import selected_document_db, document_cache_db
from app.crud.google_token import google_token_db
from app.schemas.response import StandardResponse

logger = logging.getLogger(__name__)
router = APIRouter()


class AddDocumentRequest(BaseModel):
    """Request body for adding a document."""
    doc_id: str
    doc_name: Optional[str] = None
    doc_url: Optional[str] = None


@router.get("", response_model=StandardResponse[list])
async def get_documents(
    active_only: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """Get list of monitored documents."""
    documents = selected_document_db.get_documents(
        user_id=current_user["id"],
        active_only=active_only
    )
    return StandardResponse(status=True, data=documents)


@router.post("", response_model=StandardResponse[dict])
async def add_document(
    request: AddDocumentRequest,
    current_user: dict = Depends(get_current_user)
):
    """Add a document to monitoring list."""
    if not google_token_db.is_token_valid(current_user["id"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account not connected"
        )

    # Try to fetch document info from Google
    try:
        client = GoogleAPIClient(current_user["id"])
        doc_info = client.get_document_content(request.doc_id)

        doc_data = {
            'doc_id': request.doc_id,
            'doc_name': request.doc_name or doc_info.get('doc_name'),
            'doc_url': request.doc_url or doc_info.get('doc_url'),
        }
    except Exception as e:
        logger.warning(f"Could not fetch document info: {e}")
        doc_data = {
            'doc_id': request.doc_id,
            'doc_name': request.doc_name,
            'doc_url': request.doc_url or f"https://docs.google.com/document/d/{request.doc_id}",
        }

    doc_id = selected_document_db.add_document(current_user["id"], doc_data)
    if not doc_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add document"
        )

    return StandardResponse(
        status=True,
        data={"id": doc_id, **doc_data},
        message="Document added successfully"
    )


@router.get("/browse", response_model=StandardResponse[list])
async def browse_documents(
    limit: int = Query(20, ge=1, le=50),
    current_user: dict = Depends(get_current_user)
):
    """Browse recent Google Docs the user has access to."""
    if not google_token_db.is_token_valid(current_user["id"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account not connected"
        )

    try:
        client = GoogleAPIClient(current_user["id"])
        documents = client.list_recent_documents(max_results=limit)
        return StandardResponse(status=True, data=documents)
    except Exception as e:
        logger.error(f"Failed to browse documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to browse documents: {str(e)}"
        )


@router.get("/{doc_id}", response_model=StandardResponse[dict])
async def get_document(
    doc_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific monitored document."""
    document = selected_document_db.get_document_by_id(current_user["id"], doc_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    return StandardResponse(status=True, data=document)


@router.get("/{doc_id}/content", response_model=StandardResponse[dict])
async def get_document_content(
    doc_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get cached content for a document."""
    document = selected_document_db.get_document_by_id(current_user["id"], doc_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    content = document_cache_db.get_content(document['id'])
    if not content:
        # Try to fetch fresh content
        if google_token_db.is_token_valid(current_user["id"]):
            try:
                client = GoogleAPIClient(current_user["id"])
                doc_content = client.get_document_content(doc_id)
                return StandardResponse(
                    status=True,
                    data={
                        "document": document,
                        "content": doc_content.get('content', ''),
                        "cached": False
                    }
                )
            except Exception as e:
                logger.error(f"Failed to fetch document content: {e}")

        return StandardResponse(
            status=True,
            data={
                "document": document,
                "content": None,
                "cached": False,
                "message": "No cached content available. Run sync to fetch content."
            }
        )

    return StandardResponse(
        status=True,
        data={
            "document": document,
            "content": content.get('content'),
            "summary": content.get('summary'),
            "extracted_tasks": content.get('extracted_tasks'),
            "cached": True,
            "cached_at": content.get('created_at')
        }
    )


@router.delete("/{doc_id}", response_model=StandardResponse)
async def remove_document(
    doc_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove a document from monitoring list."""
    if not selected_document_db.deactivate_document(current_user["id"], doc_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    return StandardResponse(status=True, message="Document removed from monitoring")

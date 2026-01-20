"""Authentication API routes."""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.config import settings
from app.core.session import get_current_user
from app.crud.google_token import google_token_db
from app.schemas.google import GoogleAuthStatus
from app.schemas.response import StandardResponse

logger = logging.getLogger(__name__)
router = APIRouter()


class GoogleTokenInput(BaseModel):
    """Input for saving Google token from frontend."""
    access_token: str
    refresh_token: str
    expires_at: int  # Unix timestamp
    scopes: list[str]


@router.get("/google/status", response_model=StandardResponse[GoogleAuthStatus])
async def get_google_auth_status(current_user: dict = Depends(get_current_user)):
    """Check Google authentication status."""
    token = google_token_db.get_token(current_user["id"])

    if not token:
        return StandardResponse(
            status=True,
            data=GoogleAuthStatus(is_connected=False)
        )

    is_valid = token.token_expiry > datetime.utcnow()

    return StandardResponse(
        status=True,
        data=GoogleAuthStatus(
            is_connected=is_valid,
            email=current_user["email"],
            scopes=token.scopes,
            expires_at=token.token_expiry
        )
    )


@router.post("/google/token", response_model=StandardResponse)
async def save_google_token(
    token_input: GoogleTokenInput,
    current_user: dict = Depends(get_current_user)
):
    """Save Google OAuth token from frontend NextAuth."""
    expires_at = datetime.fromtimestamp(token_input.expires_at)

    success = google_token_db.save_token(
        user_id=current_user["id"],
        access_token=token_input.access_token,
        refresh_token=token_input.refresh_token,
        token_expiry=expires_at,
        scopes=token_input.scopes
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save Google token"
        )

    return StandardResponse(status=True, message="Google account connected successfully")


@router.delete("/google/revoke", response_model=StandardResponse)
async def revoke_google_access(current_user: dict = Depends(get_current_user)):
    """Revoke Google access and delete stored token."""
    google_token_db.delete_token(current_user["id"])
    return StandardResponse(status=True, message="Google access revoked")

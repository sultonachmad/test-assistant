"""JWT session validation and user extraction."""
import logging
from typing import Optional
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from app.core.config import settings
from app.crud.user import user_db

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


def decode_jwt(token: str) -> Optional[dict]:
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.NEXTAUTH_SECRET,
            algorithms=["HS256"],
            options={"verify_exp": True},
            leeway=3600  # 1 hour grace period
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> dict:
    """Extract and validate current user from JWT token."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme",
            headers={"WWW-Authenticate": "Bearer"}
        )

    payload = decode_jwt(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Extract user info from JWT
    email = payload.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing email claim"
        )

    # Get or create user in database
    user = user_db.get_or_create(
        email=email,
        name=payload.get("name"),
        image=payload.get("picture")
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve or create user"
        )

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "image": user.image,
        "timezone": user.timezone
    }


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> Optional[dict]:
    """Get current user if authenticated, None otherwise."""
    if credentials is None:
        return None

    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None

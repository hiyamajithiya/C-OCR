"""
Authentication dependencies for API endpoints.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token, verify_api_key
from app.models.user import User, UserRole
from app.models.api_key import APIKey
from app.models.tenant import Tenant

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer credentials
        db: Database session

    Returns:
        Current user

    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Convert string user_id back to integer
    try:
        user_id: int = int(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current active user.

    Args:
        current_user: Current user from token

    Returns:
        Current active user

    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Get current admin user.

    Args:
        current_user: Current active user

    Returns:
        Current admin user

    Raises:
        HTTPException: If user is not admin
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    return current_user


async def get_current_reviewer_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Get current reviewer user (or admin).

    Args:
        current_user: Current active user

    Returns:
        Current reviewer user

    Raises:
        HTTPException: If user is not reviewer or admin
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.REVIEWER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    return current_user


async def verify_api_key_header(
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> tuple[APIKey, Tenant]:
    """
    Verify API key from header with rate limiting and quota enforcement.

    Args:
        x_api_key: API key from header
        db: Database session

    Returns:
        Tuple of (APIKey, Tenant)

    Raises:
        HTTPException: If API key is invalid, expired, or rate limited
    """
    from datetime import datetime
    from app.services.api_key_service import rate_limiter

    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )

    # Find API key by checking all keys (this is simplified, in production
    # you might want to optimize this with a cache)
    api_keys = db.query(APIKey).filter(APIKey.is_active == True).all()

    matched_key = None
    for key in api_keys:
        if verify_api_key(x_api_key, key.key_hash):
            matched_key = key
            break

    if not matched_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    # Check if key has expired
    if matched_key.expires_at and matched_key.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired",
        )

    # Check rate limit
    is_allowed, current_count = rate_limiter.check_rate_limit(
        matched_key.id, matched_key.rate_limit
    )
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Limit: {matched_key.rate_limit}/min, Current: {current_count}",
            headers={"Retry-After": "60"}
        )

    # Check daily quota
    quota_allowed, daily_count = rate_limiter.check_daily_quota(
        matched_key.id, matched_key.daily_quota
    )
    if not quota_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily quota exceeded. Limit: {matched_key.daily_quota}/day, Used: {daily_count}",
            headers={"Retry-After": "86400"}
        )

    # Update last used timestamp
    matched_key.last_used_at = datetime.utcnow()
    db.commit()

    # Get tenant
    tenant = db.query(Tenant).filter(Tenant.id == matched_key.tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    if tenant.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant is not active",
        )

    return matched_key, tenant


async def verify_api_key_with_template(
    template_id: int,
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> tuple[APIKey, Tenant]:
    """
    Verify API key and check template access permissions.

    Args:
        template_id: Template ID to access
        x_api_key: API key from header
        db: Database session

    Returns:
        Tuple of (APIKey, Tenant)

    Raises:
        HTTPException: If API key is invalid or doesn't have template access
    """
    from app.services.api_key_service import APIKeyService

    api_key, tenant = await verify_api_key_header(x_api_key, db)

    # Check template access
    service = APIKeyService(db)
    if not service.check_template_access(api_key, template_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key does not have access to this template",
        )

    return api_key, tenant

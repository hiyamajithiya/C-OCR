"""
API Key endpoints for key management (Admin only).
"""

from typing import Any, List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.api.dependencies.auth import get_current_admin_user
from app.models.user import User
from app.models.api_key import APIKey
from app.models.template import Template
from app.models.audit_log import AuditLog
from app.core.security import generate_api_key, hash_api_key, get_api_key_prefix
from app.services.api_key_service import APIKeyService

router = APIRouter()


class APIKeyCreate(BaseModel):
    """API Key creation model."""
    name: str
    scopes: List[str] = []
    rate_limit: int = 60
    daily_quota: int = 1000
    restrict_to_templates: bool = False
    template_ids: List[int] = []  # Template IDs to restrict to
    expires_at: Optional[datetime] = None


class APIKeyResponse(BaseModel):
    """API Key response model."""
    id: int
    name: str
    key_prefix: str
    scopes: List[str]
    rate_limit: int
    daily_quota: int
    is_active: bool
    restrict_to_templates: bool = False
    allowed_template_ids: List[int] = []
    created_at: datetime
    last_used_at: datetime = None
    expires_at: datetime = None
    raw_key: str = None  # Only returned on creation


class APIKeyUsageStats(BaseModel):
    """API Key usage statistics."""
    api_key_id: int
    api_key_name: str
    period_days: int
    total_requests: int
    successful_requests: int
    client_errors: int
    server_errors: int
    success_rate: float
    today: Dict[str, Any]
    rate_limit: Dict[str, Any]
    daily_breakdown: List[Dict[str, Any]]
    top_endpoints: List[Dict[str, Any]]


class APIKeySummary(BaseModel):
    """Summary of all API keys with usage."""
    id: int
    name: str
    key_prefix: str
    is_active: bool
    rate_limit: int
    daily_quota: int
    restrict_to_templates: bool
    allowed_template_count: Optional[int]
    created_at: str
    last_used_at: Optional[str]
    usage: Dict[str, Any]


@router.post("/", response_model=APIKeyResponse)
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Create a new API key (Admin only).

    Args:
        key_data: API key creation data
        current_user: Current admin user
        db: Database session

    Returns:
        Created API key with raw key (shown only once)

    Raises:
        HTTPException: If creation fails
    """
    # Validate template IDs if restricting
    allowed_templates = []
    if key_data.restrict_to_templates and key_data.template_ids:
        for template_id in key_data.template_ids:
            template = db.query(Template).filter(
                Template.id == template_id,
                Template.tenant_id == current_user.tenant_id
            ).first()
            if not template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Template {template_id} not found"
                )
            allowed_templates.append(template)

    # Generate API key
    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)
    key_prefix = get_api_key_prefix(raw_key)

    # Create API key
    api_key = APIKey(
        tenant_id=current_user.tenant_id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=key_data.name,
        scopes=key_data.scopes,
        rate_limit=key_data.rate_limit,
        daily_quota=key_data.daily_quota,
        restrict_to_templates=key_data.restrict_to_templates,
        expires_at=key_data.expires_at,
    )

    # Add allowed templates if restricted
    if allowed_templates:
        api_key.allowed_templates = allowed_templates

    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    # Log the creation
    audit_log = AuditLog(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.id,
        action="api_key_create",
        entity_type="api_key",
        entity_id=api_key.id,
        metadata_json={
            "name": api_key.name,
            "key_prefix": key_prefix,
            "restrict_to_templates": key_data.restrict_to_templates,
            "template_count": len(allowed_templates)
        }
    )
    db.add(audit_log)
    db.commit()

    return APIKeyResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        scopes=api_key.scopes,
        rate_limit=api_key.rate_limit,
        daily_quota=api_key.daily_quota,
        is_active=api_key.is_active,
        restrict_to_templates=api_key.restrict_to_templates,
        allowed_template_ids=[t.id for t in api_key.allowed_templates],
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        expires_at=api_key.expires_at,
        raw_key=raw_key  # Only shown on creation
    )


@router.get("/", response_model=List[APIKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    List all API keys for the current tenant (Admin only).

    Args:
        current_user: Current admin user
        db: Database session

    Returns:
        List of API keys (without raw keys)
    """
    api_keys = db.query(APIKey).filter(
        APIKey.tenant_id == current_user.tenant_id
    ).order_by(APIKey.created_at.desc()).all()

    return [
        APIKeyResponse(
            id=key.id,
            name=key.name,
            key_prefix=key.key_prefix,
            scopes=key.scopes,
            rate_limit=key.rate_limit,
            daily_quota=key.daily_quota,
            is_active=key.is_active,
            restrict_to_templates=key.restrict_to_templates,
            allowed_template_ids=[t.id for t in key.allowed_templates],
            created_at=key.created_at,
            last_used_at=key.last_used_at,
            expires_at=key.expires_at
        )
        for key in api_keys
    ]


@router.get("/with-stats", response_model=List[APIKeySummary])
async def list_api_keys_with_stats(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    List all API keys with usage statistics (Admin only).

    Args:
        current_user: Current admin user
        db: Database session

    Returns:
        List of API keys with usage stats
    """
    service = APIKeyService(db)
    return service.get_all_keys_stats(current_user.tenant_id)


@router.get("/{key_id}/stats", response_model=APIKeyUsageStats)
async def get_api_key_stats(
    key_id: int,
    days: int = 30,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get detailed usage statistics for an API key (Admin only).

    Args:
        key_id: API key ID
        days: Number of days to include in stats (default 30)
        current_user: Current admin user
        db: Database session

    Returns:
        Detailed usage statistics
    """
    # Verify key belongs to tenant
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.tenant_id == current_user.tenant_id
    ).first()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    service = APIKeyService(db)
    stats = service.get_usage_stats(key_id, days)

    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    return stats


@router.post("/{key_id}/update-stats")
async def update_api_key_stats(
    key_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Manually trigger daily stats update for an API key (Admin only).

    Args:
        key_id: API key ID
        current_user: Current admin user
        db: Database session

    Returns:
        Success message
    """
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.tenant_id == current_user.tenant_id
    ).first()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    service = APIKeyService(db)
    service.update_daily_stats(api_key)

    return {"message": "Stats updated successfully"}


@router.put("/{key_id}/templates")
async def update_api_key_templates(
    key_id: int,
    template_ids: List[int],
    restrict: bool = True,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Update template restrictions for an API key (Admin only).

    Args:
        key_id: API key ID
        template_ids: List of template IDs to allow
        restrict: Whether to restrict to these templates
        current_user: Current admin user
        db: Database session

    Returns:
        Updated API key
    """
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.tenant_id == current_user.tenant_id
    ).first()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    # Validate and get templates
    templates = []
    for template_id in template_ids:
        template = db.query(Template).filter(
            Template.id == template_id,
            Template.tenant_id == current_user.tenant_id
        ).first()
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template {template_id} not found"
            )
        templates.append(template)

    # Update API key
    api_key.restrict_to_templates = restrict
    api_key.allowed_templates = templates
    db.commit()
    db.refresh(api_key)

    # Log the update
    audit_log = AuditLog(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.id,
        action="api_key_update",
        entity_type="api_key",
        entity_id=api_key.id,
        metadata_json={
            "name": api_key.name,
            "restrict_to_templates": restrict,
            "template_ids": template_ids
        }
    )
    db.add(audit_log)
    db.commit()

    return APIKeyResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        scopes=api_key.scopes,
        rate_limit=api_key.rate_limit,
        daily_quota=api_key.daily_quota,
        is_active=api_key.is_active,
        restrict_to_templates=api_key.restrict_to_templates,
        allowed_template_ids=[t.id for t in api_key.allowed_templates],
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        expires_at=api_key.expires_at
    )


@router.delete("/{key_id}")
async def revoke_api_key(
    key_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Revoke (deactivate) an API key (Admin only).

    Args:
        key_id: API key ID
        current_user: Current admin user
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If key not found
    """
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.tenant_id == current_user.tenant_id
    ).first()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    # Deactivate the key
    api_key.is_active = False
    db.commit()

    # Log the revocation
    audit_log = AuditLog(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.id,
        action="api_key_revoke",
        entity_type="api_key",
        entity_id=api_key.id,
        metadata_json={"name": api_key.name, "key_prefix": api_key.key_prefix}
    )
    db.add(audit_log)
    db.commit()

    return {"message": "API key revoked successfully"}

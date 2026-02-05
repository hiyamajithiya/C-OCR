"""
Audit log endpoints for viewing system activity (Admin only).
"""

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.api.dependencies.auth import get_current_admin_user
from app.models.user import User
from app.models.audit_log import AuditLog

router = APIRouter()


class AuditLogResponse(BaseModel):
    """Audit log response model."""
    id: int
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    actor_user_id: Optional[int] = None
    actor_api_key_id: Optional[int] = None
    ip: Optional[str] = None
    user_agent: Optional[str] = None
    metadata_json: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/", response_model=List[AuditLogResponse])
async def list_audit_logs(
    action: Optional[str] = Query(None, description="Filter by action type"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    limit: int = Query(100, ge=1, le=1000, description="Number of logs to return"),
    offset: int = Query(0, ge=0, description="Number of logs to skip"),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    List audit logs for the current tenant (Admin only).

    Args:
        action: Optional filter by action type
        entity_type: Optional filter by entity type
        limit: Maximum number of logs to return
        offset: Number of logs to skip
        current_user: Current admin user
        db: Database session

    Returns:
        List of audit logs
    """
    query = db.query(AuditLog).filter(
        AuditLog.tenant_id == current_user.tenant_id
    )

    # Apply filters
    if action:
        query = query.filter(AuditLog.action == action)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)

    # Order by most recent first
    query = query.order_by(AuditLog.created_at.desc())

    # Apply pagination
    logs = query.offset(offset).limit(limit).all()

    return [
        AuditLogResponse(
            id=log.id,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            actor_user_id=log.actor_user_id,
            actor_api_key_id=log.actor_api_key_id,
            ip=log.ip,
            user_agent=log.user_agent,
            metadata_json=log.metadata_json,
            created_at=log.created_at
        )
        for log in logs
    ]


@router.get("/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get a specific audit log entry (Admin only).

    Args:
        log_id: Audit log ID
        current_user: Current admin user
        db: Database session

    Returns:
        Audit log details

    Raises:
        HTTPException: If log not found
    """
    log = db.query(AuditLog).filter(
        AuditLog.id == log_id,
        AuditLog.tenant_id == current_user.tenant_id
    ).first()

    if not log:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log not found"
        )

    return AuditLogResponse(
        id=log.id,
        action=log.action,
        entity_type=log.entity_type,
        entity_id=log.entity_id,
        actor_user_id=log.actor_user_id,
        actor_api_key_id=log.actor_api_key_id,
        ip=log.ip,
        user_agent=log.user_agent,
        metadata_json=log.metadata_json,
        created_at=log.created_at
    )

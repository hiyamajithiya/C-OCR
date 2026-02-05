"""
User endpoints for user management (Admin only).
"""

from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import datetime

from app.core.database import get_db
from app.api.dependencies.auth import get_current_admin_user, get_current_active_user
from app.models.user import User, UserRole
from app.models.audit_log import AuditLog
from app.core.security import get_password_hash

router = APIRouter()


class UserCreate(BaseModel):
    """User creation model."""
    name: str
    email: EmailStr
    password: str
    role: UserRole


class UserUpdate(BaseModel):
    """User update model."""
    name: str = None
    email: EmailStr = None
    role: UserRole = None
    is_active: bool = None


class UserResponse(BaseModel):
    """User response model."""
    id: int
    name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: datetime = None


@router.post("/", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Create a new user (Admin only).

    Args:
        user_data: User creation data
        current_user: Current admin user
        db: Database session

    Returns:
        Created user

    Raises:
        HTTPException: If email already exists or creation fails
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create user
    user = User(
        tenant_id=current_user.tenant_id,
        name=user_data.name,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        role=user_data.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Log the creation
    audit_log = AuditLog(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.id,
        action="user_create",
        entity_type="user",
        entity_id=user.id,
        metadata_json={"email": user.email, "role": user.role.value}
    )
    db.add(audit_log)
    db.commit()

    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role.value,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login_at=user.last_login_at
    )


@router.get("/", response_model=List[UserResponse])
async def list_users(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    List all users for the current tenant (Admin only).

    Args:
        current_user: Current admin user
        db: Database session

    Returns:
        List of users
    """
    users = db.query(User).filter(
        User.tenant_id == current_user.tenant_id
    ).order_by(User.created_at.desc()).all()

    return [
        UserResponse(
            id=u.id,
            name=u.name,
            email=u.email,
            role=u.role.value,
            is_active=u.is_active,
            created_at=u.created_at,
            last_login_at=u.last_login_at
        )
        for u in users
    ]


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get current user information.

    Args:
        current_user: Current authenticated user

    Returns:
        Current user information
    """
    return UserResponse(
        id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        role=current_user.role.value,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        last_login_at=current_user.last_login_at
    )


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Update a user (Admin only).

    Args:
        user_id: User ID
        user_data: User update data
        current_user: Current admin user
        db: Database session

    Returns:
        Updated user

    Raises:
        HTTPException: If user not found
    """
    user = db.query(User).filter(
        User.id == user_id,
        User.tenant_id == current_user.tenant_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Update fields
    if user_data.name is not None:
        user.name = user_data.name
    if user_data.email is not None:
        user.email = user_data.email
    if user_data.role is not None:
        user.role = user_data.role
    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    db.commit()
    db.refresh(user)

    # Log the update
    audit_log = AuditLog(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.id,
        action="user_update",
        entity_type="user",
        entity_id=user.id,
        metadata_json={"email": user.email}
    )
    db.add(audit_log)
    db.commit()

    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role.value,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login_at=user.last_login_at
    )

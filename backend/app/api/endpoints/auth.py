"""
Authentication endpoints for user login and token management.
"""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.models.user import User
from app.models.audit_log import AuditLog

router = APIRouter()


class Token(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str


class LoginResponse(BaseModel):
    """Login response model."""
    access_token: str
    token_type: str
    user: dict


@router.post("/login", response_model=LoginResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Any:
    """
    Login endpoint to obtain JWT access token.

    Args:
        form_data: Login form data (username/email and password)
        db: Database session

    Returns:
        Access token and user information

    Raises:
        HTTPException: If credentials are invalid
    """
    # Find user by email
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    # Update last login timestamp
    user.last_login_at = datetime.utcnow()
    db.commit()

    # Create access token
    access_token = create_access_token(data={"sub": user.id})

    # Log the login
    audit_log = AuditLog(
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        action="user_login",
        entity_type="user",
        entity_id=user.id,
    )
    db.add(audit_log)
    db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role.value,
        }
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    current_user: User = Depends(get_db)
) -> Any:
    """
    Refresh access token.

    Args:
        current_user: Current authenticated user

    Returns:
        New access token
    """
    access_token = create_access_token(data={"sub": current_user.id})

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

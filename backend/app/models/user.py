"""
User model for authentication and authorization.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class UserRole(str, enum.Enum):
    """User role enumeration."""
    ADMIN = "admin"  # Manage users, templates, API keys, settings
    OPERATOR = "operator"  # Upload docs, view results, request training
    REVIEWER = "reviewer"  # Approve templates, approve extraction outputs


class User(Base):
    """
    User model with role-based access control.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.OPERATOR)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    created_templates = relationship(
        "TemplateVersion",
        foreign_keys="TemplateVersion.created_by",
        back_populates="creator"
    )
    created_documents = relationship(
        "Document",
        foreign_keys="Document.created_by",
        back_populates="creator"
    )
    audit_logs = relationship(
        "AuditLog",
        foreign_keys="AuditLog.actor_user_id",
        back_populates="actor_user"
    )
    corrections = relationship(
        "ExtractionCorrection",
        foreign_keys="ExtractionCorrection.corrected_by",
        back_populates="user"
    )

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"

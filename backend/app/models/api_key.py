"""
API Key model for external API access.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON, Table
from sqlalchemy.orm import relationship

from app.core.database import Base


# Association table for API key to template restrictions
api_key_templates = Table(
    'api_key_templates',
    Base.metadata,
    Column('api_key_id', Integer, ForeignKey('api_keys.id', ondelete='CASCADE'), primary_key=True),
    Column('template_id', Integer, ForeignKey('templates.id', ondelete='CASCADE'), primary_key=True)
)


class APIKey(Base):
    """
    API Key model for authenticating external API requests.
    Keys are stored hashed, and only the raw key is shown once at creation.
    """

    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    key_hash = Column(String(255), nullable=False, unique=True, index=True)
    key_prefix = Column(String(20), nullable=False)  # First 8 chars for display
    name = Column(String(255), nullable=False)  # Friendly name for the key
    scopes = Column(JSON, nullable=False, default=list)  # List of allowed scopes
    rate_limit = Column(Integer, nullable=False, default=60)  # Requests per minute
    daily_quota = Column(Integer, nullable=False, default=1000)  # Daily request quota
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)

    # Template scoping - if empty, allows access to all templates
    restrict_to_templates = Column(Boolean, nullable=False, default=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="api_keys")
    audit_logs = relationship(
        "AuditLog",
        foreign_keys="AuditLog.actor_api_key_id",
        back_populates="actor_api_key"
    )

    # Template restrictions (many-to-many)
    allowed_templates = relationship(
        "Template",
        secondary=api_key_templates,
        back_populates="api_keys"
    )

    # Usage tracking
    usage_records = relationship("APIKeyUsage", back_populates="api_key", cascade="all, delete-orphan")
    daily_stats = relationship("APIKeyDailyStats", back_populates="api_key", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<APIKey(id={self.id}, name='{self.name}', prefix='{self.key_prefix}')>"

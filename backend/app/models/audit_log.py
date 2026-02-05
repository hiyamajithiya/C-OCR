"""
Audit log model for tracking all system activities.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class AuditLog(Base):
    """
    Audit log model for tracking all important system events.
    Logs include: uploads, downloads, template changes, API calls, user logins, etc.
    """

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    # Actor information (either user or API key)
    actor_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_api_key_id = Column(Integer, ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True, index=True)

    # Action details
    action = Column(String(100), nullable=False, index=True)  # login, upload, download, template_create, etc.
    entity_type = Column(String(100), nullable=True)  # document, template, user, etc.
    entity_id = Column(Integer, nullable=True)

    # Request details
    ip = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)  # Additional context

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="audit_logs")
    actor_user = relationship("User", foreign_keys=[actor_user_id], back_populates="audit_logs")
    actor_api_key = relationship("APIKey", foreign_keys=[actor_api_key_id], back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action='{self.action}', entity_type='{self.entity_type}')>"

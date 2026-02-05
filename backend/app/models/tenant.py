"""
Tenant model for multi-tenancy support.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base


class Tenant(Base):
    """
    Tenant model for multi-tenant isolation.
    Each tenant has isolated templates, documents, API keys, and users.
    """

    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    status = Column(String(50), nullable=False, default="active")  # active, inactive, suspended
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="tenant", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="tenant", cascade="all, delete-orphan")
    templates = relationship("Template", back_populates="tenant", cascade="all, delete-orphan")
    extraction_jobs = relationship("ExtractionJob", back_populates="tenant", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="tenant", cascade="all, delete-orphan")
    extraction_corrections = relationship("ExtractionCorrection", back_populates="tenant", cascade="all, delete-orphan")
    field_abbreviations = relationship("FieldAbbreviation", back_populates="tenant", cascade="all, delete-orphan")
    template_accuracy = relationship("TemplateAccuracy", back_populates="tenant", cascade="all, delete-orphan")
    api_key_usage = relationship("APIKeyUsage", back_populates="tenant", cascade="all, delete-orphan")
    api_key_daily_stats = relationship("APIKeyDailyStats", back_populates="tenant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Tenant(id={self.id}, name='{self.name}', status='{self.status}')>"

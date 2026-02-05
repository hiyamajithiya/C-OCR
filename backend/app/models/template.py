"""
Template models for document format recognition and field extraction.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class Template(Base):
    """
    Template model representing a document format.
    Templates store signature patterns and field extraction rules.
    """

    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    doc_category = Column(String(100), nullable=True, index=True)  # invoice, bank_statement, gst_return, etc.
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="templates")
    versions = relationship("TemplateVersion", back_populates="template", cascade="all, delete-orphan")
    extraction_results = relationship("ExtractionResult", back_populates="template")
    extraction_corrections = relationship("ExtractionCorrection", back_populates="template")
    accuracy_records = relationship("TemplateAccuracy", back_populates="template", cascade="all, delete-orphan")

    # API key restrictions (many-to-many)
    api_keys = relationship(
        "APIKey",
        secondary="api_key_templates",
        back_populates="allowed_templates"
    )
    api_key_usage = relationship("APIKeyUsage", back_populates="template")

    def __repr__(self):
        return f"<Template(id={self.id}, name='{self.name}', category='{self.doc_category}')>"


class TemplateVersion(Base):
    """
    Template version model storing specific extraction configuration.
    Each change to a template creates a new version.
    """

    __tablename__ = "template_versions"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("templates.id", ondelete="CASCADE"), nullable=False, index=True)
    version_no = Column(Integer, nullable=False)

    # Template configuration stored as JSON
    signature_json = Column(JSON, nullable=False)  # Document signature/fingerprint
    fields_json = Column(JSON, nullable=False)  # Field definitions
    rules_json = Column(JSON, nullable=False)  # Validation rules

    is_active = Column(Boolean, nullable=False, default=True)
    is_approved = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    template = relationship("Template", back_populates="versions")
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_templates")
    extraction_results = relationship("ExtractionResult", back_populates="template_version")
    extraction_corrections = relationship("ExtractionCorrection", back_populates="template_version")
    accuracy_records = relationship("TemplateAccuracy", back_populates="template_version")

    def __repr__(self):
        return f"<TemplateVersion(id={self.id}, template_id={self.template_id}, version={self.version_no})>"

"""
Extraction models for document processing jobs and results.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class JobStatus(str, enum.Enum):
    """Extraction job status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExtractionJob(Base):
    """
    Extraction job model tracking document processing tasks.
    """

    __tablename__ = "extraction_jobs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(Enum(JobStatus), nullable=False, default=JobStatus.PENDING, index=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    error_json = Column(JSON, nullable=True)  # Error details if job failed
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="extraction_jobs")
    document = relationship("Document", back_populates="extraction_jobs")

    def __repr__(self):
        return f"<ExtractionJob(id={self.id}, document_id={self.document_id}, status='{self.status}')>"


class ExtractionResult(Base):
    """
    Extraction result model storing extracted data from a document.
    """

    __tablename__ = "extraction_results"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    template_id = Column(Integer, ForeignKey("templates.id", ondelete="SET NULL"), nullable=True, index=True)
    template_version_id = Column(Integer, ForeignKey("template_versions.id", ondelete="SET NULL"), nullable=True)

    # Extraction results stored as JSON
    result_json = Column(JSON, nullable=False)  # Extracted fields and values
    confidence_json = Column(JSON, nullable=False)  # Confidence scores per field

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="extraction_results")
    template = relationship("Template", back_populates="extraction_results")
    template_version = relationship("TemplateVersion", back_populates="extraction_results")
    corrections = relationship("ExtractionCorrection", back_populates="extraction_result")

    def __repr__(self):
        return f"<ExtractionResult(id={self.id}, document_id={self.document_id}, template_id={self.template_id})>"

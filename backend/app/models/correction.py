"""
Correction models for storing user feedback on extraction results.
Used for training and improving extraction accuracy over time.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Float, Text, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base


class ExtractionCorrection(Base):
    """
    Stores user corrections to extracted field values.
    These corrections are used to improve extraction accuracy.
    """

    __tablename__ = "extraction_corrections"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    template_id = Column(Integer, ForeignKey("templates.id", ondelete="SET NULL"), nullable=True, index=True)
    template_version_id = Column(Integer, ForeignKey("template_versions.id", ondelete="SET NULL"), nullable=True)
    extraction_result_id = Column(Integer, ForeignKey("extraction_results.id", ondelete="SET NULL"), nullable=True)

    # Field information
    field_name = Column(String(255), nullable=False, index=True)
    field_label = Column(String(255), nullable=True)
    field_type = Column(String(50), nullable=True)  # text, number, date, etc.

    # Original extraction details
    original_value = Column(Text, nullable=True)
    original_confidence = Column(Float, nullable=True)
    extraction_method = Column(String(50), nullable=True)  # bbox, label_search, term_search, etc.

    # User correction
    corrected_value = Column(Text, nullable=False)
    correction_note = Column(Text, nullable=True)  # Optional note explaining the correction

    # Learning metadata
    is_processed = Column(Boolean, nullable=False, default=False)  # Has this correction been used for learning?
    learned_pattern = Column(JSON, nullable=True)  # Pattern learned from this correction

    # Audit fields
    corrected_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="extraction_corrections")
    document = relationship("Document", back_populates="extraction_corrections")
    template = relationship("Template", back_populates="extraction_corrections")
    template_version = relationship("TemplateVersion", back_populates="extraction_corrections")
    extraction_result = relationship("ExtractionResult", back_populates="corrections")
    user = relationship("User", foreign_keys=[corrected_by], back_populates="corrections")

    def __repr__(self):
        return f"<ExtractionCorrection(id={self.id}, field='{self.field_name}', original='{self.original_value}', corrected='{self.corrected_value}')>"


class FieldAbbreviation(Base):
    """
    Stores learned abbreviation mappings for field names.
    Populated from user corrections and manual additions.
    """

    __tablename__ = "field_abbreviations"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)  # NULL = global

    abbreviation = Column(String(50), nullable=False, index=True)
    expanded_form = Column(String(255), nullable=False)

    # Context - when to apply this abbreviation
    field_type = Column(String(50), nullable=True)  # Limit to specific field types
    doc_category = Column(String(100), nullable=True)  # Limit to specific document categories

    # Learning metadata
    source = Column(String(50), nullable=False, default="manual")  # manual, learned
    usage_count = Column(Integer, nullable=False, default=0)  # How many times this mapping was used
    success_count = Column(Integer, nullable=False, default=0)  # How many times it led to correct extraction

    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="field_abbreviations")

    def __repr__(self):
        return f"<FieldAbbreviation(id={self.id}, abbr='{self.abbreviation}', expanded='{self.expanded_form}')>"


class TemplateAccuracy(Base):
    """
    Tracks extraction accuracy metrics per template and field.
    Used for monitoring and improving template performance.
    """

    __tablename__ = "template_accuracy"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    template_id = Column(Integer, ForeignKey("templates.id", ondelete="CASCADE"), nullable=False, index=True)
    template_version_id = Column(Integer, ForeignKey("template_versions.id", ondelete="SET NULL"), nullable=True)

    # Tracking period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # Overall metrics
    total_extractions = Column(Integer, nullable=False, default=0)
    total_corrections = Column(Integer, nullable=False, default=0)
    accuracy_rate = Column(Float, nullable=True)  # (total - corrections) / total * 100
    avg_confidence = Column(Float, nullable=True)

    # Per-field metrics stored as JSON
    # Format: {"field_name": {"extractions": N, "corrections": N, "accuracy": N}}
    field_metrics_json = Column(JSON, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="template_accuracy")
    template = relationship("Template", back_populates="accuracy_records")
    template_version = relationship("TemplateVersion", back_populates="accuracy_records")

    def __repr__(self):
        return f"<TemplateAccuracy(id={self.id}, template_id={self.template_id}, accuracy={self.accuracy_rate}%)>"

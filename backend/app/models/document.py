"""
Document models for file management and OCR results.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class DocumentStatus(str, enum.Enum):
    """Document processing status."""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    EXTRACTED = "extracted"
    NEEDS_TRAINING = "needs_training"
    ERROR = "error"


class DocumentSource(str, enum.Enum):
    """Document upload source."""
    WEB_UI = "web_ui"
    API = "api"
    BATCH = "batch"


class FileKind(str, enum.Enum):
    """Type of document file."""
    ORIGINAL = "original"
    PAGE_IMAGE = "page_image"
    SEARCHABLE_PDF = "searchable_pdf"
    HTML = "html"
    DOCX = "docx"
    JSON = "json"


class Document(Base):
    """
    Document model representing an uploaded file for processing.
    """

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    page_count = Column(Integer, nullable=True)
    status = Column(Enum(DocumentStatus), nullable=False, default=DocumentStatus.UPLOADED, index=True)
    source = Column(Enum(DocumentSource), nullable=False, default=DocumentSource.WEB_UI)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="documents")
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_documents")
    files = relationship("DocumentFile", back_populates="document", cascade="all, delete-orphan")
    ocr_pages = relationship("OCRPage", back_populates="document", cascade="all, delete-orphan")
    extraction_jobs = relationship("ExtractionJob", back_populates="document", cascade="all, delete-orphan")
    extraction_results = relationship("ExtractionResult", back_populates="document", cascade="all, delete-orphan")
    extraction_corrections = relationship("ExtractionCorrection", back_populates="document", cascade="all, delete-orphan")
    api_key_usage = relationship("APIKeyUsage", back_populates="document")

    def __repr__(self):
        return f"<Document(id={self.id}, filename='{self.filename}', status='{self.status}')>"


class DocumentFile(Base):
    """
    File associated with a document (original, processed images, exports).
    """

    __tablename__ = "document_files"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    kind = Column(Enum(FileKind), nullable=False, index=True)
    path = Column(String(500), nullable=False)
    checksum = Column(String(64), nullable=True)  # SHA-256 checksum
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="files")

    def __repr__(self):
        return f"<DocumentFile(id={self.id}, kind='{self.kind}', path='{self.path}')>"


class OCRPage(Base):
    """
    OCR results for a single page of a document.
    """

    __tablename__ = "ocr_pages"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    page_no = Column(Integer, nullable=False)
    engine = Column(String(50), nullable=False)  # paddle, tesseract
    lang = Column(String(10), nullable=False, default="en")
    dpi = Column(Integer, nullable=False, default=300)
    json_path = Column(String(500), nullable=False)  # Path to OCR JSON file
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="ocr_pages")

    def __repr__(self):
        return f"<OCRPage(id={self.id}, document_id={self.document_id}, page_no={self.page_no})>"

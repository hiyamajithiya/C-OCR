"""
External API endpoints authenticated via API keys.
These endpoints are designed for external integrations and programmatic access.
"""

from typing import Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Query, Form, Header, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
import structlog
import time

logger = structlog.get_logger()

from app.core.database import get_db
from app.api.dependencies.auth import verify_api_key_header, verify_api_key_with_template
from app.models.api_key import APIKey
from app.models.tenant import Tenant
from app.models.document import Document, DocumentStatus, DocumentSource, DocumentFile, OCRPage, FileKind
from app.models.template import Template
from app.models.extraction import ExtractionResult
from app.models.audit_log import AuditLog
from app.services.storage import storage_service
from app.services.ocr import ocr_service
from app.services.api_key_service import APIKeyService
import json

router = APIRouter()


class ExternalDocumentResponse(BaseModel):
    """External API document response."""
    document_id: int
    status: str
    filename: str
    page_count: Optional[int]
    created_at: datetime


class ExternalExtractionResponse(BaseModel):
    """External API extraction response."""
    document_id: int
    template_id: Optional[int]
    status: str
    fields: dict
    confidence: float


class ExternalTemplateResponse(BaseModel):
    """External API template response."""
    id: int
    name: str
    description: Optional[str]
    category: Optional[str]
    is_active: bool


def record_api_usage(
    db: Session,
    api_key: APIKey,
    request: Request,
    endpoint: str,
    method: str,
    status_code: int = 200,
    template_id: Optional[int] = None,
    document_id: Optional[int] = None,
    response_time_ms: Optional[int] = None
):
    """Record API key usage for tracking and statistics."""
    service = APIKeyService(db)
    service.record_usage(
        api_key=api_key,
        endpoint=endpoint,
        method=method,
        status_code=status_code,
        template_id=template_id,
        document_id=document_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        response_time_ms=response_time_ms
    )


@router.get("/templates", response_model=List[ExternalTemplateResponse])
async def list_templates_external(
    request: Request,
    api_key_data: tuple = Depends(verify_api_key_header),
    db: Session = Depends(get_db)
) -> Any:
    """
    List available templates for this API key.

    If the API key is restricted to specific templates, only those will be returned.
    """
    start_time = time.time()
    api_key, tenant = api_key_data

    service = APIKeyService(db)
    templates = service.get_allowed_templates(api_key)

    # Record usage
    response_time = int((time.time() - start_time) * 1000)
    record_api_usage(db, api_key, request, "/external/templates", "GET", 200, response_time_ms=response_time)

    return [
        ExternalTemplateResponse(
            id=t.id,
            name=t.name,
            description=t.description,
            category=t.doc_category,
            is_active=t.is_active
        )
        for t in templates
    ]


@router.post("/documents/upload", response_model=ExternalDocumentResponse)
async def upload_document_external(
    request: Request,
    file: UploadFile = File(...),
    template_id: Optional[int] = Form(default=None),
    language: str = Form(default="eng"),
    api_key_data: tuple = Depends(verify_api_key_header),
    db: Session = Depends(get_db)
) -> Any:
    """
    Upload a document via external API.

    Args:
        file: Document file to upload (PDF, JPEG, PNG, TIFF)
        template_id: Optional template ID to apply for extraction
        language: OCR language code (default: eng)

    Returns:
        Document metadata with ID and status
    """
    start_time = time.time()
    api_key, tenant = api_key_data

    # Check template access if template_id is provided
    if template_id:
        service = APIKeyService(db)
        if not service.check_template_access(api_key, template_id):
            record_api_usage(db, api_key, request, "/external/documents/upload", "POST", 403, template_id=template_id)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="API key does not have access to this template"
            )

    # Validate file type
    allowed_types = [
        "application/pdf",
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/tiff"
    ]

    if file.content_type not in allowed_types:
        record_api_usage(db, api_key, request, "/external/documents/upload", "POST", 400)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not supported: {file.content_type}"
        )

    # Create document record
    document = Document(
        tenant_id=tenant.id,
        filename=file.filename,
        mime_type=file.content_type,
        status=DocumentStatus.UPLOADED,
        source=DocumentSource.API,
        created_by=None  # No user for API uploads
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        # Save file to storage
        file_path, checksum = storage_service.save_upload(
            file_data=file.file,
            tenant_id=tenant.id,
            document_id=document.id,
            filename=file.filename or f"document_{document.id}"
        )

        # Create document_file record
        doc_file = DocumentFile(
            document_id=document.id,
            path=file_path,
            checksum=checksum,
            kind=FileKind.ORIGINAL
        )
        db.add(doc_file)
        db.commit()

        # Log the upload with API key
        audit_log = AuditLog(
            tenant_id=tenant.id,
            actor_api_key_id=api_key.id,
            action="document_upload",
            entity_type="document",
            entity_id=document.id,
            metadata_json={
                "filename": file.filename,
                "mime_type": file.content_type,
                "source": "api",
                "template_id": template_id
            }
        )
        db.add(audit_log)
        db.commit()

        # Trigger OCR processing
        try:
            document.status = DocumentStatus.PROCESSING
            db.commit()

            full_path = storage_service.get_full_path(file_path)
            ocr_results = ocr_service.process_document(full_path, language=language)

            # Store OCR results
            for page_data in ocr_results.get("pages", []):
                page_num = page_data.get("page_number", 1)
                json_filename = f"ocr_page_{page_num}.json"
                json_data = json.dumps(page_data, indent=2).encode('utf-8')

                from io import BytesIO
                json_buffer = BytesIO(json_data)

                ocr_json_path, _ = storage_service.save_processed(
                    file_data=json_buffer,
                    tenant_id=tenant.id,
                    document_id=document.id,
                    filename=json_filename,
                    kind="ocr_json"
                )

                ocr_page = OCRPage(
                    document_id=document.id,
                    page_no=page_num,
                    engine="tesseract",
                    lang=language,
                    dpi=300,
                    json_path=ocr_json_path
                )
                db.add(ocr_page)

            document.status = DocumentStatus.EXTRACTED
            document.page_count = ocr_results.get("page_count", 1)
            db.commit()

        except Exception as ocr_error:
            logger.error("external_api_ocr_error", document_id=document.id, error=str(ocr_error))
            document.status = DocumentStatus.ERROR
            db.commit()

        # Record usage
        response_time = int((time.time() - start_time) * 1000)
        record_api_usage(
            db, api_key, request, "/external/documents/upload", "POST", 200,
            template_id=template_id, document_id=document.id, response_time_ms=response_time
        )

        return ExternalDocumentResponse(
            document_id=document.id,
            status=document.status.value,
            filename=document.filename,
            page_count=document.page_count,
            created_at=document.created_at
        )

    except Exception as e:
        document.status = DocumentStatus.ERROR
        db.commit()
        record_api_usage(db, api_key, request, "/external/documents/upload", "POST", 500)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(e)}"
        )


@router.get("/documents/{document_id}", response_model=ExternalDocumentResponse)
async def get_document_external(
    request: Request,
    document_id: int,
    api_key_data: tuple = Depends(verify_api_key_header),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get document metadata via external API.
    """
    start_time = time.time()
    api_key, tenant = api_key_data

    document = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == tenant.id
    ).first()

    if not document:
        record_api_usage(db, api_key, request, f"/external/documents/{document_id}", "GET", 404)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    response_time = int((time.time() - start_time) * 1000)
    record_api_usage(
        db, api_key, request, f"/external/documents/{document_id}", "GET", 200,
        document_id=document_id, response_time_ms=response_time
    )

    return ExternalDocumentResponse(
        document_id=document.id,
        status=document.status.value,
        filename=document.filename,
        page_count=document.page_count,
        created_at=document.created_at
    )


@router.get("/documents/{document_id}/extraction")
async def get_document_extraction_external(
    request: Request,
    document_id: int,
    api_key_data: tuple = Depends(verify_api_key_header),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get document extraction results via external API.

    Returns OCR text and any template-based field extractions.
    """
    start_time = time.time()
    api_key, tenant = api_key_data

    document = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == tenant.id
    ).first()

    if not document:
        record_api_usage(db, api_key, request, f"/external/documents/{document_id}/extraction", "GET", 404)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    if document.status != DocumentStatus.EXTRACTED:
        record_api_usage(db, api_key, request, f"/external/documents/{document_id}/extraction", "GET", 400)
        return {
            "document_id": document_id,
            "status": document.status.value,
            "message": "Document not yet processed",
            "ocr_text": None,
            "extractions": []
        }

    # Get OCR text
    ocr_pages = db.query(OCRPage).filter(
        OCRPage.document_id == document_id
    ).order_by(OCRPage.page_no).all()

    full_text_parts = []
    for ocr_page in ocr_pages:
        try:
            full_json_path = storage_service.get_full_path(ocr_page.json_path)
            with open(full_json_path, 'r', encoding='utf-8') as f:
                page_data = json.load(f)
                if page_data.get('text'):
                    full_text_parts.append(page_data['text'])
        except Exception as e:
            logger.error("external_api_ocr_read_error", page_id=ocr_page.id, error=str(e))

    # Get extraction results
    extractions = db.query(ExtractionResult).filter(
        ExtractionResult.document_id == document_id
    ).all()

    # Filter by template access if restricted
    service = APIKeyService(db)
    accessible_extractions = []
    for ext in extractions:
        if ext.template_id and not service.check_template_access(api_key, ext.template_id):
            continue
        accessible_extractions.append({
            "template_id": ext.template_id,
            "template_name": ext.template.name if ext.template else None,
            "fields": ext.extracted_json,
            "confidence": ext.confidence,
            "created_at": ext.created_at.isoformat()
        })

    response_time = int((time.time() - start_time) * 1000)
    record_api_usage(
        db, api_key, request, f"/external/documents/{document_id}/extraction", "GET", 200,
        document_id=document_id, response_time_ms=response_time
    )

    return {
        "document_id": document_id,
        "status": document.status.value,
        "page_count": document.page_count,
        "ocr_text": "\n\n".join(full_text_parts),
        "extractions": accessible_extractions
    }


@router.post("/documents/{document_id}/extract")
async def extract_with_template_external(
    request: Request,
    document_id: int,
    template_id: int = Query(..., description="Template ID to use for extraction"),
    api_key_data: tuple = Depends(verify_api_key_header),
    db: Session = Depends(get_db)
) -> Any:
    """
    Apply a template to extract fields from a document.

    Requires access to the specified template.
    """
    start_time = time.time()
    api_key, tenant = api_key_data

    # Check template access
    service = APIKeyService(db)
    if not service.check_template_access(api_key, template_id):
        record_api_usage(
            db, api_key, request, f"/external/documents/{document_id}/extract", "POST", 403,
            template_id=template_id
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key does not have access to this template"
        )

    document = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == tenant.id
    ).first()

    if not document:
        record_api_usage(db, api_key, request, f"/external/documents/{document_id}/extract", "POST", 404)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    template = db.query(Template).filter(
        Template.id == template_id,
        Template.tenant_id == tenant.id
    ).first()

    if not template:
        record_api_usage(db, api_key, request, f"/external/documents/{document_id}/extract", "POST", 404)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    # Log the extraction attempt
    audit_log = AuditLog(
        tenant_id=tenant.id,
        actor_api_key_id=api_key.id,
        action="template_apply",
        entity_type="document",
        entity_id=document_id,
        metadata_json={"template_id": template_id, "template_name": template.name}
    )
    db.add(audit_log)
    db.commit()

    response_time = int((time.time() - start_time) * 1000)
    record_api_usage(
        db, api_key, request, f"/external/documents/{document_id}/extract", "POST", 200,
        template_id=template_id, document_id=document_id, response_time_ms=response_time
    )

    # TODO: Implement actual template extraction logic
    return {
        "document_id": document_id,
        "template_id": template_id,
        "template_name": template.name,
        "status": "extraction_queued",
        "message": "Template extraction has been queued"
    }


@router.get("/usage/stats")
async def get_my_usage_stats(
    request: Request,
    days: int = Query(default=30, ge=1, le=90),
    api_key_data: tuple = Depends(verify_api_key_header),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get usage statistics for the current API key.

    Allows API consumers to monitor their own usage.
    """
    start_time = time.time()
    api_key, tenant = api_key_data

    service = APIKeyService(db)
    stats = service.get_usage_stats(api_key.id, days)

    response_time = int((time.time() - start_time) * 1000)
    record_api_usage(
        db, api_key, request, "/external/usage/stats", "GET", 200,
        response_time_ms=response_time
    )

    return stats

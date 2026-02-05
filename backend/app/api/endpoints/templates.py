"""
Template endpoints for template management and training.
"""

from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.api.dependencies.auth import get_current_active_user, get_current_reviewer_user
from app.models.user import User
from app.models.template import Template, TemplateVersion
from app.models.audit_log import AuditLog
from app.models.extraction import ExtractionJob, ExtractionResult

router = APIRouter()


class TemplateCreate(BaseModel):
    """Template creation model."""
    name: str
    description: str = None
    doc_category: str = None


class TemplateResponse(BaseModel):
    """Template response model."""
    id: int
    name: str
    description: str = None
    doc_category: str = None
    is_active: bool
    created_at: datetime


@router.post("/", response_model=TemplateResponse)
async def create_template(
    template_data: TemplateCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Create a new template.

    Args:
        template_data: Template creation data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Created template

    Raises:
        HTTPException: If creation fails
    """
    # Create template
    template = Template(
        tenant_id=current_user.tenant_id,
        name=template_data.name,
        description=template_data.description,
        doc_category=template_data.doc_category,
    )
    db.add(template)
    db.commit()
    db.refresh(template)

    # Log the creation
    audit_log = AuditLog(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.id,
        action="template_create",
        entity_type="template",
        entity_id=template.id,
        metadata_json={"name": template.name}
    )
    db.add(audit_log)
    db.commit()

    return TemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        doc_category=template.doc_category,
        is_active=template.is_active,
        created_at=template.created_at
    )


@router.get("/", response_model=List[TemplateResponse])
async def list_templates(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    List all templates for the current tenant.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of templates
    """
    templates = db.query(Template).filter(
        Template.tenant_id == current_user.tenant_id
    ).order_by(Template.created_at.desc()).all()

    return [
        TemplateResponse(
            id=t.id,
            name=t.name,
            description=t.description,
            doc_category=t.doc_category,
            is_active=t.is_active,
            created_at=t.created_at
        )
        for t in templates
    ]


@router.get("/{template_id}/versions")
async def get_template_versions(
    template_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get all versions for a template.

    Args:
        template_id: Template ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of template versions

    Raises:
        HTTPException: If template not found
    """
    template = db.query(Template).filter(
        Template.id == template_id,
        Template.tenant_id == current_user.tenant_id
    ).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    versions = db.query(TemplateVersion).filter(
        TemplateVersion.template_id == template_id
    ).order_by(TemplateVersion.version_no.desc()).all()

    return [
        {
            "id": v.id,
            "template_id": v.template_id,
            "version_no": v.version_no,
            "signature_json": v.signature_json,
            "fields_json": v.fields_json,
            "rules_json": v.rules_json,
            "is_approved": v.is_approved,
            "created_at": v.created_at,
            "created_by": v.created_by
        }
        for v in versions
    ]


@router.post("/{template_id}/versions")
async def create_template_version(
    template_id: int,
    signature_json: dict,
    fields_json: dict,
    rules_json: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Create a new template version.

    Args:
        template_id: Template ID
        signature_json: Document signature configuration
        fields_json: Field extraction configuration
        rules_json: Validation rules
        current_user: Current authenticated user
        db: Database session

    Returns:
        Created template version

    Raises:
        HTTPException: If template not found
    """
    template = db.query(Template).filter(
        Template.id == template_id,
        Template.tenant_id == current_user.tenant_id
    ).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    # Get next version number
    max_version = db.query(TemplateVersion).filter(
        TemplateVersion.template_id == template_id
    ).count()

    # Create new version
    version = TemplateVersion(
        template_id=template_id,
        version_no=max_version + 1,
        signature_json=signature_json,
        fields_json=fields_json,
        rules_json=rules_json,
        created_by=current_user.id
    )
    db.add(version)
    db.commit()
    db.refresh(version)

    # Log the creation
    audit_log = AuditLog(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.id,
        action="template_version_create",
        entity_type="template_version",
        entity_id=version.id,
        metadata_json={"template_id": template_id, "version_no": version.version_no}
    )
    db.add(audit_log)
    db.commit()

    return {
        "id": version.id,
        "template_id": template_id,
        "version_no": version.version_no,
        "is_approved": version.is_approved,
        "created_at": version.created_at
    }


class ApplyTemplateRequest(BaseModel):
    """Apply template request model."""
    document_id: int


@router.post("/{template_id}/apply")
async def apply_template(
    template_id: int,
    request: ApplyTemplateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Force apply a template to a document.

    Args:
        template_id: Template ID
        document_id: Document ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Extraction result

    Raises:
        HTTPException: If template or document not found
    """
    from app.models.document import Document, OCRPage
    from app.services.template_service import field_extractor

    # Verify template exists and belongs to tenant
    template = db.query(Template).filter(
        Template.id == template_id,
        Template.tenant_id == current_user.tenant_id
    ).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    # Get latest approved version, or latest version if none approved
    latest_version = db.query(TemplateVersion).filter(
        TemplateVersion.template_id == template_id,
        TemplateVersion.is_approved == True
    ).order_by(TemplateVersion.version_no.desc()).first()

    if not latest_version:
        # Fall back to latest version
        latest_version = db.query(TemplateVersion).filter(
            TemplateVersion.template_id == template_id
        ).order_by(TemplateVersion.version_no.desc()).first()

    if not latest_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No template version found"
        )

    document_id = request.document_id

    # Verify document exists and belongs to tenant
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == current_user.tenant_id
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Check if document has OCR results
    if document.status != 'extracted':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document has not been OCR processed yet"
        )

    # Get OCR results for all pages
    ocr_pages = db.query(OCRPage).filter(
        OCRPage.document_id == document_id
    ).order_by(OCRPage.page_no).all()

    if not ocr_pages:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No OCR results found for document"
        )

    # Convert OCR pages to format expected by extractor
    import json
    from pathlib import Path
    from app.core.config import settings

    ocr_results = []
    for ocr_page in ocr_pages:
        # Load OCR data from JSON file
        json_path = Path(settings.STORAGE_PATH) / ocr_page.json_path
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                ocr_data = json.load(f)
        else:
            ocr_data = {}
        ocr_results.append(ocr_data)

    # Extract fields
    template_config = {
        'fields_json': latest_version.fields_json,
        'rules_json': latest_version.rules_json
    }

    extracted_fields = field_extractor.extract_fields(ocr_results, template_config)

    # Build result and confidence JSON from extracted fields
    result_json = {}
    confidence_json = {}
    for field_name, field_data in extracted_fields.items():
        result_json[field_name] = field_data.get('value')
        confidence_json[field_name] = field_data.get('confidence', 0.0)

    # Create extraction job
    from app.models.extraction import JobStatus
    extraction_job = ExtractionJob(
        tenant_id=current_user.tenant_id,
        document_id=document_id,
        status=JobStatus.COMPLETED,
        started_at=datetime.utcnow(),
        finished_at=datetime.utcnow()
    )
    db.add(extraction_job)
    db.flush()

    # Save extraction result
    extraction_result = ExtractionResult(
        document_id=document_id,
        template_id=template_id,
        template_version_id=latest_version.id,
        result_json=result_json,
        confidence_json=confidence_json
    )
    db.add(extraction_result)

    db.commit()
    db.refresh(extraction_job)
    db.refresh(extraction_result)

    # Log the extraction
    audit_log = AuditLog(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.id,
        action="template_apply",
        entity_type="extraction_result",
        entity_id=extraction_result.id,
        metadata_json={
            "template_id": template_id,
            "document_id": document_id,
            "field_count": len(extracted_fields)
        }
    )
    db.add(audit_log)
    db.commit()

    return {
        "extraction_result_id": extraction_result.id,
        "extraction_job_id": extraction_job.id,
        "template_id": template_id,
        "template_name": template.name,
        "document_id": document_id,
        "document_filename": document.filename,
        "fields_extracted": len(extracted_fields),
        "extracted_data": extracted_fields,
        "status": "completed"
    }


@router.get("/extractions/document/{document_id}")
async def get_document_extractions(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get all extraction results for a document.

    Args:
        document_id: Document ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of extraction results

    Raises:
        HTTPException: If document not found
    """
    from app.models.document import Document

    # Verify document exists and belongs to tenant
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == current_user.tenant_id
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Get extraction results for this document
    extraction_results = db.query(ExtractionResult).filter(
        ExtractionResult.document_id == document_id
    ).order_by(ExtractionResult.created_at.desc()).all()

    results = []
    for extraction_result in extraction_results:
        # Get template info
        template = None
        if extraction_result.template_id:
            template = db.query(Template).filter(
                Template.id == extraction_result.template_id
            ).first()

        # Build extracted_data from result_json and confidence_json
        extracted_data = {}
        result_json = extraction_result.result_json or {}
        confidence_json = extraction_result.confidence_json or {}

        for field_name, field_value in result_json.items():
            extracted_data[field_name] = {
                'value': field_value,
                'confidence': confidence_json.get(field_name, 0.0),
                'status': 'extracted'
            }

        results.append({
            "extraction_result_id": extraction_result.id,
            "template_id": template.id if template else None,
            "template_name": template.name if template else "Unknown",
            "template_version_id": extraction_result.template_version_id,
            "extracted_data": extracted_data,
            "created_at": extraction_result.created_at
        })

    return results

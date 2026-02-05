"""
Correction endpoints for submitting and managing user feedback on extractions.
These corrections are used to improve extraction accuracy over time.
"""

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from datetime import datetime, timedelta

from app.core.database import get_db
from app.api.dependencies.auth import get_current_active_user
from app.models.user import User
from app.models.document import Document
from app.models.template import Template, TemplateVersion
from app.models.extraction import ExtractionResult
from app.models.correction import ExtractionCorrection, FieldAbbreviation, TemplateAccuracy
from app.models.audit_log import AuditLog

router = APIRouter()


# ==================== Request/Response Models ====================

class CorrectionSubmit(BaseModel):
    """Model for submitting a single field correction."""
    document_id: int
    extraction_result_id: Optional[int] = None
    field_name: str
    field_label: Optional[str] = None
    field_type: Optional[str] = None
    original_value: Optional[str] = None
    original_confidence: Optional[float] = None
    extraction_method: Optional[str] = None
    corrected_value: str
    correction_note: Optional[str] = None


class BulkCorrectionSubmit(BaseModel):
    """Model for submitting multiple corrections at once."""
    document_id: int
    extraction_result_id: Optional[int] = None
    corrections: List[CorrectionSubmit]


class CorrectionResponse(BaseModel):
    """Response model for a correction."""
    id: int
    document_id: int
    field_name: str
    field_label: Optional[str]
    original_value: Optional[str]
    corrected_value: str
    is_processed: bool
    created_at: datetime


class AbbreviationCreate(BaseModel):
    """Model for creating a new abbreviation mapping."""
    abbreviation: str
    expanded_form: str
    field_type: Optional[str] = None
    doc_category: Optional[str] = None


class AbbreviationResponse(BaseModel):
    """Response model for an abbreviation."""
    id: int
    abbreviation: str
    expanded_form: str
    field_type: Optional[str]
    doc_category: Optional[str]
    source: str
    usage_count: int
    success_count: int
    is_active: bool


class AccuracyStatsResponse(BaseModel):
    """Response model for template accuracy statistics."""
    template_id: int
    template_name: str
    total_extractions: int
    total_corrections: int
    accuracy_rate: float
    avg_confidence: Optional[float]
    field_stats: dict


# ==================== Correction Endpoints ====================

@router.post("/submit", response_model=CorrectionResponse)
async def submit_correction(
    correction_data: CorrectionSubmit,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Submit a correction for an extracted field value.

    Args:
        correction_data: Correction details
        current_user: Current authenticated user
        db: Database session

    Returns:
        Created correction record
    """
    # Verify document exists and belongs to tenant
    document = db.query(Document).filter(
        Document.id == correction_data.document_id,
        Document.tenant_id == current_user.tenant_id
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Get template info from extraction result if available
    template_id = None
    template_version_id = None

    if correction_data.extraction_result_id:
        extraction_result = db.query(ExtractionResult).filter(
            ExtractionResult.id == correction_data.extraction_result_id,
            ExtractionResult.document_id == correction_data.document_id
        ).first()

        if extraction_result:
            template_id = extraction_result.template_id
            template_version_id = extraction_result.template_version_id

    # Create correction record
    correction = ExtractionCorrection(
        tenant_id=current_user.tenant_id,
        document_id=correction_data.document_id,
        template_id=template_id,
        template_version_id=template_version_id,
        extraction_result_id=correction_data.extraction_result_id,
        field_name=correction_data.field_name,
        field_label=correction_data.field_label,
        field_type=correction_data.field_type,
        original_value=correction_data.original_value,
        original_confidence=correction_data.original_confidence,
        extraction_method=correction_data.extraction_method,
        corrected_value=correction_data.corrected_value,
        correction_note=correction_data.correction_note,
        corrected_by=current_user.id
    )

    db.add(correction)

    # Log the correction
    audit_log = AuditLog(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.id,
        action="correction_submit",
        entity_type="extraction_correction",
        entity_id=0,  # Will update after commit
        metadata_json={
            "document_id": correction_data.document_id,
            "field_name": correction_data.field_name,
            "original_value": correction_data.original_value,
            "corrected_value": correction_data.corrected_value
        }
    )
    db.add(audit_log)

    db.commit()
    db.refresh(correction)

    # Update audit log with actual correction ID
    audit_log.entity_id = correction.id
    db.commit()

    return CorrectionResponse(
        id=correction.id,
        document_id=correction.document_id,
        field_name=correction.field_name,
        field_label=correction.field_label,
        original_value=correction.original_value,
        corrected_value=correction.corrected_value,
        is_processed=correction.is_processed,
        created_at=correction.created_at
    )


@router.post("/submit-bulk")
async def submit_bulk_corrections(
    bulk_data: BulkCorrectionSubmit,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Submit multiple corrections at once.

    Args:
        bulk_data: Bulk correction data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Summary of submitted corrections
    """
    # Verify document exists and belongs to tenant
    document = db.query(Document).filter(
        Document.id == bulk_data.document_id,
        Document.tenant_id == current_user.tenant_id
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Get template info from extraction result if available
    template_id = None
    template_version_id = None

    if bulk_data.extraction_result_id:
        extraction_result = db.query(ExtractionResult).filter(
            ExtractionResult.id == bulk_data.extraction_result_id,
            ExtractionResult.document_id == bulk_data.document_id
        ).first()

        if extraction_result:
            template_id = extraction_result.template_id
            template_version_id = extraction_result.template_version_id

    created_corrections = []

    for correction_data in bulk_data.corrections:
        correction = ExtractionCorrection(
            tenant_id=current_user.tenant_id,
            document_id=bulk_data.document_id,
            template_id=template_id,
            template_version_id=template_version_id,
            extraction_result_id=bulk_data.extraction_result_id,
            field_name=correction_data.field_name,
            field_label=correction_data.field_label,
            field_type=correction_data.field_type,
            original_value=correction_data.original_value,
            original_confidence=correction_data.original_confidence,
            extraction_method=correction_data.extraction_method,
            corrected_value=correction_data.corrected_value,
            correction_note=correction_data.correction_note,
            corrected_by=current_user.id
        )
        db.add(correction)
        created_corrections.append(correction)

    # Log bulk correction
    audit_log = AuditLog(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.id,
        action="correction_submit_bulk",
        entity_type="extraction_correction",
        entity_id=0,
        metadata_json={
            "document_id": bulk_data.document_id,
            "correction_count": len(created_corrections)
        }
    )
    db.add(audit_log)

    db.commit()

    return {
        "status": "success",
        "document_id": bulk_data.document_id,
        "corrections_submitted": len(created_corrections),
        "message": f"Successfully submitted {len(created_corrections)} corrections"
    }


@router.get("/document/{document_id}", response_model=List[CorrectionResponse])
async def get_document_corrections(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get all corrections for a specific document.

    Args:
        document_id: Document ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of corrections for the document
    """
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

    corrections = db.query(ExtractionCorrection).filter(
        ExtractionCorrection.document_id == document_id,
        ExtractionCorrection.tenant_id == current_user.tenant_id
    ).order_by(ExtractionCorrection.created_at.desc()).all()

    return [
        CorrectionResponse(
            id=c.id,
            document_id=c.document_id,
            field_name=c.field_name,
            field_label=c.field_label,
            original_value=c.original_value,
            corrected_value=c.corrected_value,
            is_processed=c.is_processed,
            created_at=c.created_at
        )
        for c in corrections
    ]


@router.get("/template/{template_id}/stats", response_model=AccuracyStatsResponse)
async def get_template_accuracy_stats(
    template_id: int,
    days: int = 30,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get accuracy statistics for a template based on corrections.

    Args:
        template_id: Template ID
        days: Number of days to look back (default 30)
        current_user: Current authenticated user
        db: Database session

    Returns:
        Accuracy statistics for the template
    """
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

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Count total extractions
    total_extractions = db.query(ExtractionResult).filter(
        ExtractionResult.template_id == template_id,
        ExtractionResult.created_at >= cutoff_date
    ).count()

    # Count total corrections
    total_corrections = db.query(ExtractionCorrection).filter(
        ExtractionCorrection.template_id == template_id,
        ExtractionCorrection.created_at >= cutoff_date
    ).count()

    # Calculate accuracy rate
    accuracy_rate = 0.0
    if total_extractions > 0:
        # Estimate accuracy based on corrections per extraction
        # Assuming each extraction has multiple fields
        accuracy_rate = max(0, 100 - (total_corrections / max(total_extractions, 1) * 10))

    # Calculate average confidence from extraction results
    avg_confidence_result = db.query(func.avg(ExtractionResult.confidence_json)).filter(
        ExtractionResult.template_id == template_id,
        ExtractionResult.created_at >= cutoff_date
    ).scalar()

    # Get field-level statistics
    field_corrections = db.query(
        ExtractionCorrection.field_name,
        func.count(ExtractionCorrection.id).label('correction_count')
    ).filter(
        ExtractionCorrection.template_id == template_id,
        ExtractionCorrection.created_at >= cutoff_date
    ).group_by(ExtractionCorrection.field_name).all()

    field_stats = {
        fc.field_name: {"corrections": fc.correction_count}
        for fc in field_corrections
    }

    return AccuracyStatsResponse(
        template_id=template_id,
        template_name=template.name,
        total_extractions=total_extractions,
        total_corrections=total_corrections,
        accuracy_rate=round(accuracy_rate, 2),
        avg_confidence=float(avg_confidence_result) if avg_confidence_result else None,
        field_stats=field_stats
    )


# ==================== Abbreviation Endpoints ====================

@router.get("/abbreviations", response_model=List[AbbreviationResponse])
async def list_abbreviations(
    include_global: bool = True,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    List all abbreviation mappings.

    Args:
        include_global: Include global abbreviations (default True)
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of abbreviation mappings
    """
    query = db.query(FieldAbbreviation).filter(FieldAbbreviation.is_active == True)

    if include_global:
        query = query.filter(
            (FieldAbbreviation.tenant_id == current_user.tenant_id) |
            (FieldAbbreviation.tenant_id == None)
        )
    else:
        query = query.filter(FieldAbbreviation.tenant_id == current_user.tenant_id)

    abbreviations = query.order_by(FieldAbbreviation.usage_count.desc()).all()

    return [
        AbbreviationResponse(
            id=a.id,
            abbreviation=a.abbreviation,
            expanded_form=a.expanded_form,
            field_type=a.field_type,
            doc_category=a.doc_category,
            source=a.source,
            usage_count=a.usage_count,
            success_count=a.success_count,
            is_active=a.is_active
        )
        for a in abbreviations
    ]


@router.post("/abbreviations", response_model=AbbreviationResponse)
async def create_abbreviation(
    abbr_data: AbbreviationCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Create a new abbreviation mapping.

    Args:
        abbr_data: Abbreviation data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Created abbreviation record
    """
    # Check if abbreviation already exists for this tenant
    existing = db.query(FieldAbbreviation).filter(
        FieldAbbreviation.abbreviation == abbr_data.abbreviation.lower(),
        FieldAbbreviation.tenant_id == current_user.tenant_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Abbreviation '{abbr_data.abbreviation}' already exists"
        )

    abbreviation = FieldAbbreviation(
        tenant_id=current_user.tenant_id,
        abbreviation=abbr_data.abbreviation.lower(),
        expanded_form=abbr_data.expanded_form.lower(),
        field_type=abbr_data.field_type,
        doc_category=abbr_data.doc_category,
        source="manual"
    )

    db.add(abbreviation)

    # Log the creation
    audit_log = AuditLog(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.id,
        action="abbreviation_create",
        entity_type="field_abbreviation",
        entity_id=0,
        metadata_json={
            "abbreviation": abbr_data.abbreviation,
            "expanded_form": abbr_data.expanded_form
        }
    )
    db.add(audit_log)

    db.commit()
    db.refresh(abbreviation)

    audit_log.entity_id = abbreviation.id
    db.commit()

    return AbbreviationResponse(
        id=abbreviation.id,
        abbreviation=abbreviation.abbreviation,
        expanded_form=abbreviation.expanded_form,
        field_type=abbreviation.field_type,
        doc_category=abbreviation.doc_category,
        source=abbreviation.source,
        usage_count=abbreviation.usage_count,
        success_count=abbreviation.success_count,
        is_active=abbreviation.is_active
    )


@router.delete("/abbreviations/{abbreviation_id}")
async def delete_abbreviation(
    abbreviation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Delete (deactivate) an abbreviation mapping.

    Args:
        abbreviation_id: Abbreviation ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Deletion confirmation
    """
    abbreviation = db.query(FieldAbbreviation).filter(
        FieldAbbreviation.id == abbreviation_id,
        FieldAbbreviation.tenant_id == current_user.tenant_id
    ).first()

    if not abbreviation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Abbreviation not found"
        )

    abbreviation.is_active = False

    # Log the deletion
    audit_log = AuditLog(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.id,
        action="abbreviation_delete",
        entity_type="field_abbreviation",
        entity_id=abbreviation_id,
        metadata_json={
            "abbreviation": abbreviation.abbreviation,
            "expanded_form": abbreviation.expanded_form
        }
    )
    db.add(audit_log)

    db.commit()

    return {"status": "success", "message": "Abbreviation deactivated"}


# ==================== Learning Trigger ====================

@router.post("/process-learning")
async def trigger_learning_process(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Trigger the learning process to apply corrections to improve extraction.

    This endpoint processes unprocessed corrections and:
    1. Updates abbreviation usage statistics
    2. Learns new abbreviation patterns
    3. Updates template accuracy metrics

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        Learning process summary
    """
    from app.services.learning_service import learning_service

    try:
        result = learning_service.process_corrections(db, current_user.tenant_id)

        # Log the learning process
        audit_log = AuditLog(
            tenant_id=current_user.tenant_id,
            actor_user_id=current_user.id,
            action="learning_process",
            entity_type="system",
            entity_id=0,
            metadata_json=result
        )
        db.add(audit_log)
        db.commit()

        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Learning process failed: {str(e)}"
        )

"""
Document endpoints for file upload, processing, and retrieval.
"""

from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Query, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
import structlog

logger = structlog.get_logger()

from app.core.database import get_db
from app.api.dependencies.auth import get_current_active_user, verify_api_key_header
from app.models.user import User
from app.models.document import Document, DocumentStatus, DocumentSource, DocumentFile, OCRPage, FileKind
from app.models.audit_log import AuditLog
from app.services.storage import storage_service
from app.services.ocr import ocr_service
import json
from pathlib import Path

router = APIRouter()


class DocumentUploadResponse(BaseModel):
    """Document upload response model."""
    document_id: int
    status: str
    message: str


class DocumentMetadata(BaseModel):
    """Document metadata model."""
    id: int
    filename: str
    mime_type: str
    page_count: Optional[int]
    status: str
    source: str
    created_at: datetime


@router.post("/", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    doc_category: Optional[str] = Form(default=None),
    template_id: Optional[int] = Form(default=None),
    language: str = Form(default="eng"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Upload a document for processing.

    Args:
        file: Document file to upload
        doc_category: Optional document category
        template_id: Optional template ID to apply
        language: OCR language (default: en)
        current_user: Current authenticated user
        db: Database session

    Returns:
        Document upload response with document ID and status

    Raises:
        HTTPException: If upload fails
    """
    # Validate file type
    allowed_types = [
        "application/pdf",
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/tiff"
    ]

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not supported: {file.content_type}"
        )

    # Create document record
    document = Document(
        tenant_id=current_user.tenant_id,
        filename=file.filename,
        mime_type=file.content_type,
        status=DocumentStatus.UPLOADED,
        source=DocumentSource.WEB_UI,
        created_by=current_user.id
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        # Save file to storage
        file_path, checksum = storage_service.save_upload(
            file_data=file.file,
            tenant_id=current_user.tenant_id,
            document_id=document.id,
            filename=file.filename or f"document_{document.id}"
        )

        # Create document_file record
        try:
            doc_file = DocumentFile(
                document_id=document.id,
                path=file_path,
                checksum=checksum,
                kind=FileKind.ORIGINAL
            )
            db.add(doc_file)
            db.commit()
        except Exception as df_error:
            logger.error("document_file_creation_error", error=str(df_error), error_type=type(df_error).__name__)
            raise

        # Log the upload
        audit_log = AuditLog(
            tenant_id=current_user.tenant_id,
            actor_user_id=current_user.id,
            action="document_upload",
            entity_type="document",
            entity_id=document.id,
            metadata_json={
                "filename": file.filename,
                "mime_type": file.content_type,
                "category": doc_category,
                "file_path": file_path
            }
        )
        db.add(audit_log)
        db.commit()

        # Trigger OCR processing (synchronous for development)
        try:
            document.status = DocumentStatus.PROCESSING
            db.commit()

            # Get full file path
            full_path = storage_service.get_full_path(file_path)

            # Process with OCR
            ocr_results = ocr_service.process_document(full_path, language=language)

            # Store OCR results in database
            for page_data in ocr_results.get("pages", []):
                # Save OCR JSON to file
                page_num = page_data.get("page_number", 1)
                json_filename = f"ocr_page_{page_num}.json"
                json_data = json.dumps(page_data, indent=2).encode('utf-8')

                from io import BytesIO
                json_buffer = BytesIO(json_data)

                ocr_json_path, _ = storage_service.save_processed(
                    file_data=json_buffer,
                    tenant_id=current_user.tenant_id,
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

            # Update document status and page count
            document.status = DocumentStatus.EXTRACTED
            document.page_count = ocr_results.get("page_count", 1)
            db.commit()

            logger.info(
                "document_processed",
                document_id=document.id,
                pages=document.page_count
            )

        except Exception as ocr_error:
            logger.error(
                "ocr_processing_error",
                document_id=document.id,
                error=str(ocr_error)
            )
            document.status = DocumentStatus.ERROR
            db.commit()

        return {
            "document_id": document.id,
            "status": document.status.value,
            "message": "Document uploaded successfully and queued for processing"
        }
    except Exception as e:
        # Update document status to error
        import traceback
        error_details = traceback.format_exc()
        logger.error(
            "document_upload_failed",
            error=str(e),
            error_type=type(e).__name__,
            traceback=error_details
        )
        document.status = DocumentStatus.ERROR
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save document: {str(e)}"
        )


@router.get("/", response_model=list[DocumentMetadata])
async def list_documents(
    status_filter: Optional[str] = Query(default=None, description="Filter by status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    List documents for current user's tenant.

    Args:
        status_filter: Optional status filter
        limit: Max documents to return
        offset: Pagination offset
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of document metadata
    """
    query = db.query(Document).filter(
        Document.tenant_id == current_user.tenant_id
    )

    if status_filter:
        try:
            status_enum = DocumentStatus(status_filter)
            query = query.filter(Document.status == status_enum)
        except ValueError:
            pass  # Invalid status, ignore filter

    documents = query.order_by(Document.created_at.desc()).offset(offset).limit(limit).all()

    return [
        DocumentMetadata(
            id=doc.id,
            filename=doc.filename,
            mime_type=doc.mime_type,
            page_count=doc.page_count,
            status=doc.status.value,
            source=doc.source.value,
            created_at=doc.created_at
        )
        for doc in documents
    ]


@router.get("/{document_id}", response_model=DocumentMetadata)
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get document metadata.

    Args:
        document_id: Document ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Document metadata

    Raises:
        HTTPException: If document not found or access denied
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == current_user.tenant_id
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    return DocumentMetadata(
        id=document.id,
        filename=document.filename,
        mime_type=document.mime_type,
        page_count=document.page_count,
        status=document.status.value,
        source=document.source.value,
        created_at=document.created_at
    )


@router.get("/{document_id}/result")
async def get_document_result(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get document extraction results.

    Args:
        document_id: Document ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Extraction results JSON

    Raises:
        HTTPException: If document not found or not yet processed
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == current_user.tenant_id
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    if document.status != DocumentStatus.EXTRACTED:
        return {
            "document_id": document_id,
            "status": document.status.value,
            "message": "Document not yet processed",
            "pages": []
        }

    # Fetch OCR results from database
    ocr_pages = db.query(OCRPage).filter(
        OCRPage.document_id == document_id
    ).order_by(OCRPage.page_no).all()

    pages_data = []
    full_text_parts = []

    for ocr_page in ocr_pages:
        # Read OCR JSON file
        try:
            full_json_path = storage_service.get_full_path(ocr_page.json_path)
            with open(full_json_path, 'r', encoding='utf-8') as f:
                page_data = json.load(f)
                pages_data.append(page_data)
                if page_data.get('text'):
                    full_text_parts.append(page_data['text'])
        except Exception as e:
            logger.error("ocr_json_read_error", page_id=ocr_page.id, error=str(e))
            pages_data.append({
                "page_number": ocr_page.page_no,
                "text": "[Error reading OCR data]",
                "confidence": 0.0
            })

    return {
        "document_id": document_id,
        "status": document.status.value,
        "page_count": document.page_count or len(pages_data),
        "pages": pages_data,
        "full_text": "\n\n".join(full_text_parts),
        "exports": {
            "searchable_pdf": f"/api/v1/documents/{document_id}/download?kind=searchable_pdf"
        }
    }


@router.get("/{document_id}/download")
async def download_document_file(
    document_id: int,
    kind: str = Query(..., description="File kind to download"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Download document file (searchable PDF, HTML, etc.).

    Args:
        document_id: Document ID
        kind: File kind (searchable_pdf, html, docx, json)
        current_user: Current authenticated user
        db: Database session

    Returns:
        File stream

    Raises:
        HTTPException: If document or file not found
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == current_user.tenant_id
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # TODO: Get file from storage and return stream
    # Log the download
    audit_log = AuditLog(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.id,
        action="document_download",
        entity_type="document",
        entity_id=document.id,
        metadata_json={"kind": kind}
    )
    db.add(audit_log)
    db.commit()

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="File download not yet implemented"
    )


@router.get("/{document_id}/pages/{page_num}/image")
async def get_page_image(
    document_id: int,
    page_num: int,
    dpi: int = Query(default=150, ge=72, le=300),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> StreamingResponse:
    """
    Render and return a document page as an image.

    Args:
        document_id: Document ID
        page_num: Page number (1-indexed)
        dpi: Image resolution (72-300, default 150)
        current_user: Current authenticated user
        db: Database session

    Returns:
        PNG image as streaming response
    """
    import fitz  # PyMuPDF
    from io import BytesIO

    # Get document
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == current_user.tenant_id
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Get document file
    doc_file = db.query(DocumentFile).filter(
        DocumentFile.document_id == document_id,
        DocumentFile.kind == FileKind.ORIGINAL
    ).first()

    if not doc_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document file not found"
        )

    # Validate page number
    if page_num < 1 or (document.page_count and page_num > document.page_count):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid page number. Document has {document.page_count} pages."
        )

    try:
        # Get full file path
        full_path = storage_service.get_full_path(doc_file.path)

        # Handle different file types
        if document.mime_type == "application/pdf":
            # Open PDF and render page
            pdf_doc = fitz.open(full_path)
            page = pdf_doc[page_num - 1]  # 0-indexed

            # Render at specified DPI
            zoom = dpi / 72
            matrix = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=matrix)

            # Convert to PNG bytes
            img_bytes = pix.tobytes("png")
            pdf_doc.close()

            return StreamingResponse(
                BytesIO(img_bytes),
                media_type="image/png",
                headers={
                    "Content-Disposition": f"inline; filename=page_{page_num}.png",
                    "Cache-Control": "public, max-age=3600"
                }
            )
        else:
            # For images, return the original file (page 1 only)
            if page_num != 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Image documents only have 1 page"
                )

            with open(full_path, "rb") as f:
                img_bytes = f.read()

            content_type = document.mime_type or "image/png"
            return StreamingResponse(
                BytesIO(img_bytes),
                media_type=content_type,
                headers={
                    "Content-Disposition": f"inline; filename={document.filename}",
                    "Cache-Control": "public, max-age=3600"
                }
            )

    except Exception as e:
        logger.error("page_image_error", document_id=document_id, page=page_num, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to render page image: {str(e)}"
        )


@router.get("/{document_id}/pages/{page_num}/ocr")
async def get_page_ocr_data(
    document_id: int,
    page_num: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get OCR text with word coordinates for a specific page.

    Args:
        document_id: Document ID
        page_num: Page number (1-indexed)
        current_user: Current authenticated user
        db: Database session

    Returns:
        OCR data with word coordinates
    """
    # Get document
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == current_user.tenant_id
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Get OCR page data
    ocr_page = db.query(OCRPage).filter(
        OCRPage.document_id == document_id,
        OCRPage.page_no == page_num
    ).first()

    if not ocr_page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"OCR data not found for page {page_num}"
        )

    try:
        # Read OCR JSON file
        full_json_path = storage_service.get_full_path(ocr_page.json_path)
        with open(full_json_path, 'r', encoding='utf-8') as f:
            page_data = json.load(f)

        return {
            "document_id": document_id,
            "page_number": page_num,
            "dpi": ocr_page.dpi,
            "engine": ocr_page.engine,
            "language": ocr_page.lang,
            "text": page_data.get("text", ""),
            "confidence": page_data.get("confidence", 0.0),
            "words": page_data.get("words_with_coords", []),
            "raw_words": page_data.get("words", [])
        }

    except Exception as e:
        logger.error("page_ocr_read_error", document_id=document_id, page=page_num, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read OCR data: {str(e)}"
        )


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Delete a document and all associated files.

    Args:
        document_id: Document ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If document not found
    """
    import os
    import shutil

    # Get document
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == current_user.tenant_id
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    try:
        # Get document directory path
        doc_dir = os.path.join(
            str(storage_service.backend.base_path),
            f"tenants/{current_user.tenant_id}/documents/{document_id}"
        )

        # Delete physical files
        if os.path.exists(doc_dir):
            shutil.rmtree(doc_dir)
            logger.info("document_files_deleted", document_id=document_id, path=doc_dir)

        # Delete OCR JSON files
        ocr_dir = os.path.join(
            str(storage_service.backend.base_path),
            f"tenants/{current_user.tenant_id}/processed/ocr_json/{document_id}"
        )
        if os.path.exists(ocr_dir):
            shutil.rmtree(ocr_dir)
            logger.info("ocr_files_deleted", document_id=document_id, path=ocr_dir)

        # Delete database records (cascading will handle related records)
        db.delete(document)

        # Log the deletion
        audit_log = AuditLog(
            tenant_id=current_user.tenant_id,
            actor_user_id=current_user.id,
            action="document_delete",
            entity_type="document",
            entity_id=document.id,
            metadata_json={"filename": document.filename}
        )
        db.add(audit_log)
        db.commit()

        logger.info("document_deleted", document_id=document_id, filename=document.filename)

        return {"message": "Document deleted successfully", "document_id": document_id}

    except Exception as e:
        db.rollback()
        logger.error("document_delete_error", document_id=document_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}"
        )


@router.post("/bulk-delete")
async def bulk_delete_documents(
    document_ids: list[int],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Delete multiple documents at once.

    Args:
        document_ids: List of document IDs to delete
        current_user: Current authenticated user
        db: Database session

    Returns:
        Success message with count of deleted documents
    """
    import os
    import shutil

    if not document_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No document IDs provided"
        )

    deleted_count = 0
    errors = []

    for document_id in document_ids:
        try:
            # Get document
            document = db.query(Document).filter(
                Document.id == document_id,
                Document.tenant_id == current_user.tenant_id
            ).first()

            if not document:
                errors.append(f"Document {document_id} not found")
                continue

            # Get document directory path
            doc_dir = os.path.join(
                str(storage_service.backend.base_path),
                f"tenants/{current_user.tenant_id}/documents/{document_id}"
            )

            # Delete physical files
            if os.path.exists(doc_dir):
                shutil.rmtree(doc_dir)
                logger.info("document_files_deleted", document_id=document_id, path=doc_dir)

            # Delete OCR JSON files
            ocr_dir = os.path.join(
                str(storage_service.backend.base_path),
                f"tenants/{current_user.tenant_id}/processed/ocr_json/{document_id}"
            )
            if os.path.exists(ocr_dir):
                shutil.rmtree(ocr_dir)
                logger.info("ocr_files_deleted", document_id=document_id, path=ocr_dir)

            # Delete database records
            db.delete(document)

            # Log the deletion
            audit_log = AuditLog(
                tenant_id=current_user.tenant_id,
                actor_user_id=current_user.id,
                action="document_delete",
                entity_type="document",
                entity_id=document.id,
                metadata_json={"filename": document.filename, "bulk_delete": True}
            )
            db.add(audit_log)

            deleted_count += 1
            logger.info("document_deleted", document_id=document_id, filename=document.filename)

        except Exception as e:
            logger.error("document_delete_error", document_id=document_id, error=str(e))
            errors.append(f"Document {document_id}: {str(e)}")

    # Commit all deletions
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to commit deletions: {str(e)}"
        )

    return {
        "message": f"Successfully deleted {deleted_count} document(s)",
        "deleted_count": deleted_count,
        "errors": errors if errors else None
    }

"""
Celery tasks for document processing - complete pipeline integration.
"""

import io
import json
from datetime import datetime
import structlog

from app.workers.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.document import Document, DocumentStatus, DocumentFile, FileKind, OCRPage
from app.models.extraction import ExtractionJob, JobStatus, ExtractionResult
from app.models.template import TemplateVersion
from app.services.storage import storage_service
from app.services.pdf_service import pdf_service
from app.services.image_service import image_preprocessor
from app.services.ocr_service import ocr_service
from app.services.layout_service import layout_analyzer
from app.services.pdf_generator import pdf_generator
from app.services.template_service import template_service, field_extractor
from app.services.validation_service import validation_service

logger = structlog.get_logger()


@celery_app.task(bind=True, name="process_document")
def process_document(self, document_id: int):
    """
    Main task to process a document through the complete OCR pipeline.

    Args:
        document_id: ID of the document to process

    Returns:
        Processing result
    """
    db = SessionLocal()
    document = None
    job = None

    try:
        logger.info("processing_document_started", document_id=document_id, task_id=self.request.id)

        # Get document
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            logger.error("document_not_found", document_id=document_id)
            return {"status": "error", "message": "Document not found"}

        # Update document status
        document.status = DocumentStatus.PROCESSING
        db.commit()

        # Create extraction job
        job = ExtractionJob(
            tenant_id=document.tenant_id,
            document_id=document_id,
            status=JobStatus.RUNNING,
            started_at=datetime.utcnow()
        )
        db.add(job)
        db.commit()

        # 1. Load file from storage
        original_file = db.query(DocumentFile).filter(
            DocumentFile.document_id == document_id,
            DocumentFile.kind == FileKind.ORIGINAL
        ).first()

        if not original_file:
            logger.warning("original_file_not_found_skipping_processing", document_id=document_id)
            document.status = DocumentStatus.NEEDS_TRAINING
            job.status = JobStatus.COMPLETED
            job.finished_at = datetime.utcnow()
            db.commit()
            return {"status": "success", "document_id": document_id, "message": "File pending"}

        file_path = storage_service.get_full_path(original_file.path)

        # 2. Process based on file type
        is_pdf = document.mime_type == "application/pdf"
        pages_data = []

        if is_pdf:
            # Check if PDF has text layer
            has_text = pdf_service.has_text_layer(file_path)
            page_count = pdf_service.get_page_count(file_path)

            if has_text:
                # Extract text directly from PDF
                pages_data = pdf_service.extract_text_with_positions(file_path)
            else:
                # Scanned PDF - need OCR
                import numpy as np
                for page_num in range(1, page_count + 1):
                    page_image = pdf_service.render_page_to_image(file_path, page_num)
                    img_array = np.array(page_image)
                    preprocessed = image_preprocessor.preprocess_for_ocr(img_array)
                    ocr_result = ocr_service.recognize(preprocessed)

                    pages_data.append({
                        "page_no": page_num,
                        "width": page_image.width,
                        "height": page_image.height,
                        "blocks": ocr_result.get('blocks', []),
                        "words": ocr_result.get('words', []),
                        "lines": ocr_result.get('lines', []),
                        "source": "ocr"
                    })

                    # Save OCR JSON
                    ocr_json_path, _ = storage_service.save_processed(
                        io.BytesIO(json.dumps(ocr_result).encode()),
                        document.tenant_id,
                        document_id,
                        f"page_{page_num}_ocr.json",
                        "ocr_json"
                    )

                    ocr_page = OCRPage(
                        document_id=document_id,
                        page_no=page_num,
                        engine=ocr_result.get('engine', 'unknown'),
                        lang="en",
                        dpi=300,
                        json_path=ocr_json_path
                    )
                    db.add(ocr_page)

            document.page_count = page_count

        else:
            # Image file
            from PIL import Image
            import numpy as np

            file_stream = storage_service.load(original_file.path)
            page_image = Image.open(file_stream)
            img_array = np.array(page_image)
            preprocessed = image_preprocessor.preprocess_for_ocr(img_array)
            ocr_result = ocr_service.recognize(preprocessed)

            pages_data = [{
                "page_no": 1,
                "width": page_image.width,
                "height": page_image.height,
                "blocks": ocr_result.get('blocks', []),
                "words": ocr_result.get('words', []),
                "lines": ocr_result.get('lines', []),
                "source": "ocr"
            }]

            document.page_count = 1

        db.commit()

        # Combine all pages OCR data
        combined_ocr = {"blocks": [], "words": [], "lines": []}
        for page in pages_data:
            combined_ocr["blocks"].extend(page.get("blocks", []))
            combined_ocr["words"].extend(page.get("words", []))
            combined_ocr["lines"].extend(page.get("lines", []))

        # Template matching
        doc_signature = template_service.compute_document_signature(
            combined_ocr, {}, len(pages_data)
        )

        templates = db.query(TemplateVersion).join(
            TemplateVersion.template
        ).filter(
            TemplateVersion.is_active == True,
            TemplateVersion.is_approved == True
        ).all()

        template_sigs = [
            {"template_version_id": t.id, "signature": t.signature_json}
            for t in templates
        ]

        matches = template_service.match_templates(doc_signature, template_sigs)

        if matches:
            best_template_id, confidence = matches[0]
            template_version = db.query(TemplateVersion).filter(
                TemplateVersion.id == best_template_id
            ).first()

            if template_version:
                extracted_fields = field_extractor.extract_fields(
                    combined_ocr,
                    {
                        "fields_json": template_version.fields_json,
                        "rules_json": template_version.rules_json
                    }
                )

                extraction_result = ExtractionResult(
                    document_id=document_id,
                    template_id=template_version.template_id,
                    template_version_id=template_version.id,
                    result_json=extracted_fields,
                    confidence_json={"overall": confidence}
                )
                db.add(extraction_result)
                document.status = DocumentStatus.EXTRACTED
            else:
                document.status = DocumentStatus.NEEDS_TRAINING
        else:
            document.status = DocumentStatus.NEEDS_TRAINING

        job.status = JobStatus.COMPLETED
        job.finished_at = datetime.utcnow()
        db.commit()

        logger.info("processing_document_completed", document_id=document_id)
        return {"status": "success", "document_id": document_id}

    except Exception as e:
        logger.error("processing_document_failed", document_id=document_id, error=str(e))

        if document:
            document.status = DocumentStatus.ERROR
            db.commit()

        if job:
            job.status = JobStatus.FAILED
            job.error_json = {"error": str(e)}
            job.finished_at = datetime.utcnow()
            db.commit()

        raise

    finally:
        db.close()

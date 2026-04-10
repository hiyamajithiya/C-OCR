"""
Celery tasks for document processing - complete pipeline integration.
Migrated from app/workers/document_tasks.py: SQLAlchemy -> Django ORM.
"""

import io
import json
from datetime import datetime
import structlog

from cocr.celery import app as celery_app

logger = structlog.get_logger()


@celery_app.task(bind=True, name="process_document")
def process_document(self, document_id: int):
    import django
    django.setup()

    from documents.models import Document, DocumentFile, OCRPage
    from extractions.models import ExtractionJob, ExtractionResult
    from templates_app.models import TemplateVersion
    from services.storage import storage_service
    from services.pdf_service import pdf_service
    from services.image_service import image_preprocessor
    from services.ocr_service import ocr_service
    from services.template_service import template_service, field_extractor

    document = None
    job = None

    try:
        logger.info("processing_document_started", document_id=document_id, task_id=self.request.id)

        document = Document.objects.filter(id=document_id).first()
        if not document:
            logger.error("document_not_found", document_id=document_id)
            return {"status": "error", "message": "Document not found"}

        document.status = "processing"
        document.save()

        job = ExtractionJob.objects.create(
            tenant_id=document.tenant_id,
            document_id=document_id,
            status="running",
            started_at=datetime.utcnow(),
        )

        original_file = DocumentFile.objects.filter(
            document_id=document_id, kind="original"
        ).first()

        if not original_file:
            logger.warning("original_file_not_found_skipping_processing", document_id=document_id)
            document.status = "needs_training"
            document.save()
            job.status = "completed"
            job.finished_at = datetime.utcnow()
            job.save()
            return {"status": "success", "document_id": document_id, "message": "File pending"}

        file_path = storage_service.get_full_path(original_file.path)

        is_pdf = document.mime_type == "application/pdf"
        pages_data = []

        if is_pdf:
            has_text = pdf_service.has_text_layer(file_path)
            page_count = pdf_service.get_page_count(file_path)

            if has_text:
                pages_data = pdf_service.extract_text_with_positions(file_path)
            else:
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
                        "blocks": ocr_result.get("blocks", []),
                        "words": ocr_result.get("words", []),
                        "lines": ocr_result.get("lines", []),
                        "source": "ocr",
                    })

                    ocr_json_path, _ = storage_service.save_processed(
                        io.BytesIO(json.dumps(ocr_result).encode()),
                        document.tenant_id,
                        document_id,
                        f"page_{page_num}_ocr.json",
                        "ocr_json",
                    )

                    OCRPage.objects.create(
                        document_id=document_id,
                        page_no=page_num,
                        engine=ocr_result.get("engine", "unknown"),
                        lang="en",
                        dpi=300,
                        json_path=ocr_json_path,
                    )

            document.page_count = page_count
        else:
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
                "blocks": ocr_result.get("blocks", []),
                "words": ocr_result.get("words", []),
                "lines": ocr_result.get("lines", []),
                "source": "ocr",
            }]

            document.page_count = 1

        document.save()

        combined_ocr = {"blocks": [], "words": [], "lines": []}
        for page in pages_data:
            combined_ocr["blocks"].extend(page.get("blocks", []))
            combined_ocr["words"].extend(page.get("words", []))
            combined_ocr["lines"].extend(page.get("lines", []))

        doc_signature = template_service.compute_document_signature(combined_ocr, {}, len(pages_data))

        templates = TemplateVersion.objects.select_related("template").filter(
            is_active=True, is_approved=True
        )

        template_sigs = [
            {"template_version_id": t.id, "signature": t.signature_json}
            for t in templates
        ]

        matches = template_service.match_templates(doc_signature, template_sigs)

        if matches:
            best_template_id, confidence = matches[0]
            template_version = TemplateVersion.objects.filter(id=best_template_id).first()

            if template_version:
                extracted_fields = field_extractor.extract_fields(
                    combined_ocr,
                    {
                        "fields_json": template_version.fields_json,
                        "rules_json": template_version.rules_json,
                    },
                )

                ExtractionResult.objects.create(
                    document_id=document_id,
                    template_id=template_version.template_id,
                    template_version_id=template_version.id,
                    result_json=extracted_fields,
                    confidence_json={"overall": confidence},
                )
                document.status = "extracted"
            else:
                document.status = "needs_training"
        else:
            document.status = "needs_training"

        job.status = "completed"
        job.finished_at = datetime.utcnow()
        job.save()
        document.save()

        logger.info("processing_document_completed", document_id=document_id)
        return {"status": "success", "document_id": document_id}

    except Exception as e:
        logger.error("processing_document_failed", document_id=document_id, error=str(e))

        if document:
            document.status = "error"
            document.save()

        if job:
            job.status = "failed"
            job.error_json = {"error": str(e)}
            job.finished_at = datetime.utcnow()
            job.save()

        raise

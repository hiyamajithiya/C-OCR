"""
Celery tasks for OCR processing.
"""

import structlog
from app.workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(bind=True, name="run_ocr_on_page")
def run_ocr_on_page(self, document_id: int, page_no: int, image_path: str):
    """
    Run OCR on a single page.

    Args:
        document_id: Document ID
        page_no: Page number
        image_path: Path to page image

    Returns:
        OCR result
    """
    logger.info("ocr_task_started", document_id=document_id, page_no=page_no)

    # TODO: Implement OCR processing
    # 1. Load image
    # 2. Pre-process image (deskew, denoise, etc.)
    # 3. Run PaddleOCR (or Tesseract as fallback)
    # 4. Extract words, lines, blocks with bounding boxes
    # 5. Store OCR results as JSON

    logger.info("ocr_task_completed", document_id=document_id, page_no=page_no)

    return {"status": "success", "page_no": page_no}

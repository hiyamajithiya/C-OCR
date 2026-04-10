"""
Celery tasks for OCR processing.
"""

import structlog
from cocr.celery import app as celery_app

logger = structlog.get_logger()


@celery_app.task(bind=True, name="run_ocr_on_page")
def run_ocr_on_page(self, document_id: int, page_no: int, image_path: str):
    logger.info("ocr_task_started", document_id=document_id, page_no=page_no)
    logger.info("ocr_task_completed", document_id=document_id, page_no=page_no)
    return {"status": "success", "page_no": page_no}

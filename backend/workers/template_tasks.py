"""
Celery tasks for template matching and field extraction.
"""

import structlog
from cocr.celery import app as celery_app

logger = structlog.get_logger()


@celery_app.task(bind=True, name="match_template")
def match_template(self, document_id: int):
    logger.info("template_matching_started", document_id=document_id)
    logger.info("template_matching_completed", document_id=document_id)
    return {"status": "success", "template_id": None, "confidence": 0.0}


@celery_app.task(bind=True, name="extract_fields")
def extract_fields(self, document_id: int, template_version_id: int):
    logger.info("field_extraction_started", document_id=document_id, template_version_id=template_version_id)
    logger.info("field_extraction_completed", document_id=document_id)
    return {"status": "success", "fields": {}}

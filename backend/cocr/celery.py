"""
Celery configuration for C-OCR project.
"""

import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cocr.settings")

app = Celery("c_ocr_worker")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks(["workers"])

"""
Document, DocumentFile, OCRPage models.
"""

from datetime import datetime
from django.db import models


DOCUMENT_STATUS_CHOICES = [
    ("uploaded", "Uploaded"),
    ("processing", "Processing"),
    ("extracted", "Extracted"),
    ("needs_training", "Needs Training"),
    ("error", "Error"),
]

DOCUMENT_SOURCE_CHOICES = [
    ("web_ui", "Web UI"),
    ("api", "API"),
    ("batch", "Batch"),
]

FILE_KIND_CHOICES = [
    ("original", "Original"),
    ("page_image", "Page Image"),
    ("searchable_pdf", "Searchable PDF"),
    ("html", "HTML"),
    ("docx", "DOCX"),
    ("json", "JSON"),
]


class Document(models.Model):
    tenant = models.ForeignKey("accounts.Tenant", on_delete=models.CASCADE, related_name="documents")
    filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=100)
    page_count = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=DOCUMENT_STATUS_CHOICES, default="uploaded")
    source = models.CharField(max_length=20, choices=DOCUMENT_SOURCE_CHOICES, default="web_ui")
    created_at = models.DateTimeField(default=datetime.utcnow)
    created_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="created_documents", db_column="created_by")
    updated_at = models.DateTimeField(default=datetime.utcnow)

    class Meta:
        db_table = "documents"

    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Document({self.id}, {self.filename})"


class DocumentFile(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="files")
    kind = models.CharField(max_length=20, choices=FILE_KIND_CHOICES)
    path = models.CharField(max_length=500)
    checksum = models.CharField(max_length=64, null=True, blank=True)
    created_at = models.DateTimeField(default=datetime.utcnow)

    class Meta:
        db_table = "document_files"

    def __str__(self):
        return f"DocumentFile({self.id}, {self.kind})"


class OCRPage(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="ocr_pages")
    page_no = models.IntegerField()
    engine = models.CharField(max_length=50)
    lang = models.CharField(max_length=10, default="en")
    dpi = models.IntegerField(default=300)
    json_path = models.CharField(max_length=500)
    created_at = models.DateTimeField(default=datetime.utcnow)

    class Meta:
        db_table = "ocr_pages"

    def __str__(self):
        return f"OCRPage({self.id}, doc={self.document_id}, page={self.page_no})"

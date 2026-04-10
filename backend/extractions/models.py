"""
ExtractionJob and ExtractionResult models.
"""

from datetime import datetime
from django.db import models


JOB_STATUS_CHOICES = [
    ("pending", "Pending"),
    ("running", "Running"),
    ("completed", "Completed"),
    ("failed", "Failed"),
    ("cancelled", "Cancelled"),
]


class ExtractionJob(models.Model):
    tenant = models.ForeignKey("accounts.Tenant", on_delete=models.CASCADE, related_name="extraction_jobs")
    document = models.ForeignKey("documents.Document", on_delete=models.CASCADE, related_name="extraction_jobs")
    status = models.CharField(max_length=20, choices=JOB_STATUS_CHOICES, default="pending")
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    error_json = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(default=datetime.utcnow)

    class Meta:
        db_table = "extraction_jobs"

    def __str__(self):
        return f"ExtractionJob({self.id}, doc={self.document_id}, {self.status})"


class ExtractionResult(models.Model):
    document = models.ForeignKey("documents.Document", on_delete=models.CASCADE, related_name="extraction_results")
    template = models.ForeignKey("templates_app.Template", on_delete=models.SET_NULL, null=True, blank=True, related_name="extraction_results")
    template_version = models.ForeignKey("templates_app.TemplateVersion", on_delete=models.SET_NULL, null=True, blank=True, related_name="extraction_results")
    result_json = models.JSONField()
    confidence_json = models.JSONField()
    created_at = models.DateTimeField(default=datetime.utcnow)

    class Meta:
        db_table = "extraction_results"

    def __str__(self):
        return f"ExtractionResult({self.id}, doc={self.document_id})"

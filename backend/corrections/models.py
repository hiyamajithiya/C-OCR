"""
ExtractionCorrection, FieldAbbreviation, TemplateAccuracy models.
"""

from datetime import datetime
from django.db import models


class ExtractionCorrection(models.Model):
    tenant = models.ForeignKey("accounts.Tenant", on_delete=models.CASCADE, related_name="extraction_corrections")
    document = models.ForeignKey("documents.Document", on_delete=models.CASCADE, related_name="extraction_corrections")
    template = models.ForeignKey("templates_app.Template", on_delete=models.SET_NULL, null=True, blank=True, related_name="extraction_corrections")
    template_version = models.ForeignKey("templates_app.TemplateVersion", on_delete=models.SET_NULL, null=True, blank=True, related_name="extraction_corrections")
    extraction_result = models.ForeignKey("extractions.ExtractionResult", on_delete=models.SET_NULL, null=True, blank=True, related_name="corrections")
    field_name = models.CharField(max_length=255)
    field_label = models.CharField(max_length=255, null=True, blank=True)
    field_type = models.CharField(max_length=50, null=True, blank=True)
    original_value = models.TextField(null=True, blank=True)
    original_confidence = models.FloatField(null=True, blank=True)
    extraction_method = models.CharField(max_length=50, null=True, blank=True)
    corrected_value = models.TextField()
    correction_note = models.TextField(null=True, blank=True)
    is_processed = models.BooleanField(default=False)
    learned_pattern = models.JSONField(null=True, blank=True)
    corrected_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="corrections", db_column="corrected_by")
    created_at = models.DateTimeField(default=datetime.utcnow)

    class Meta:
        db_table = "extraction_corrections"

    def __str__(self):
        return f"ExtractionCorrection({self.id}, {self.field_name})"


class FieldAbbreviation(models.Model):
    tenant = models.ForeignKey("accounts.Tenant", on_delete=models.CASCADE, null=True, blank=True, related_name="field_abbreviations")
    abbreviation = models.CharField(max_length=50)
    expanded_form = models.CharField(max_length=255)
    field_type = models.CharField(max_length=50, null=True, blank=True)
    doc_category = models.CharField(max_length=100, null=True, blank=True)
    source = models.CharField(max_length=50, default="manual")
    usage_count = models.IntegerField(default=0)
    success_count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=datetime.utcnow)
    updated_at = models.DateTimeField(default=datetime.utcnow)

    class Meta:
        db_table = "field_abbreviations"

    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"FieldAbbreviation({self.id}, {self.abbreviation})"


class TemplateAccuracy(models.Model):
    tenant = models.ForeignKey("accounts.Tenant", on_delete=models.CASCADE, related_name="template_accuracy")
    template = models.ForeignKey("templates_app.Template", on_delete=models.CASCADE, related_name="accuracy_records")
    template_version = models.ForeignKey("templates_app.TemplateVersion", on_delete=models.SET_NULL, null=True, blank=True, related_name="accuracy_records")
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    total_extractions = models.IntegerField(default=0)
    total_corrections = models.IntegerField(default=0)
    accuracy_rate = models.FloatField(null=True, blank=True)
    avg_confidence = models.FloatField(null=True, blank=True)
    field_metrics_json = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(default=datetime.utcnow)
    updated_at = models.DateTimeField(default=datetime.utcnow)

    class Meta:
        db_table = "template_accuracy"

    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"TemplateAccuracy({self.id}, template={self.template_id})"


class MLModel(models.Model):
    """Trained ML model for per-field confidence improvement."""

    template = models.ForeignKey(
        "templates_app.Template", on_delete=models.CASCADE, related_name="ml_models"
    )
    field_name = models.CharField(max_length=255)
    model_path = models.CharField(max_length=500)
    version = models.IntegerField(default=1)
    training_samples = models.IntegerField(default=0)
    accuracy_score = models.FloatField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=datetime.utcnow)

    class Meta:
        db_table = "ml_models"
        unique_together = [("template", "field_name", "version")]

    def __str__(self):
        return f"MLModel({self.id}, {self.field_name}, v{self.version})"

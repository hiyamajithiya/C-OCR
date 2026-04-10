"""
Template and TemplateVersion models.
"""

from datetime import datetime
from django.db import models


class Template(models.Model):
    tenant = models.ForeignKey("accounts.Tenant", on_delete=models.CASCADE, related_name="templates")
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    doc_category = models.CharField(max_length=100, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=datetime.utcnow)
    updated_at = models.DateTimeField(default=datetime.utcnow)

    class Meta:
        db_table = "templates"

    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Template({self.id}, {self.name})"


class TemplateVersion(models.Model):
    template = models.ForeignKey(Template, on_delete=models.CASCADE, related_name="versions")
    version_no = models.IntegerField()
    signature_json = models.JSONField()
    fields_json = models.JSONField()
    rules_json = models.JSONField()
    is_active = models.BooleanField(default=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=datetime.utcnow)
    created_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="created_templates", db_column="created_by")

    class Meta:
        db_table = "template_versions"

    def __str__(self):
        return f"TemplateVersion({self.id}, template={self.template_id}, v{self.version_no})"

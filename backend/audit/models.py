"""
AuditLog model.
"""

from datetime import datetime
from django.db import models


class AuditLog(models.Model):
    tenant = models.ForeignKey("accounts.Tenant", on_delete=models.CASCADE, related_name="audit_logs")
    actor_user = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs")
    actor_api_key = models.ForeignKey("api_keys.APIKey", on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs")
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=100, null=True, blank=True)
    entity_id = models.IntegerField(null=True, blank=True)
    ip = models.CharField(max_length=50, null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    metadata_json = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(default=datetime.utcnow)

    class Meta:
        db_table = "audit_logs"

    def __str__(self):
        return f"AuditLog({self.id}, {self.action})"

"""
APIKey, APIKeyUsage, APIKeyDailyStats models.
"""

from datetime import datetime
from django.db import models


class APIKeyTemplate(models.Model):
    api_key = models.ForeignKey("APIKey", on_delete=models.CASCADE)
    template = models.ForeignKey("templates_app.Template", on_delete=models.CASCADE)

    class Meta:
        db_table = "api_key_templates"
        unique_together = [("api_key", "template")]


class APIKey(models.Model):
    tenant = models.ForeignKey("accounts.Tenant", on_delete=models.CASCADE, related_name="api_keys")
    key_hash = models.CharField(max_length=255, unique=True)
    key_prefix = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    scopes = models.JSONField(default=list)
    rate_limit = models.IntegerField(default=60)
    daily_quota = models.IntegerField(default=1000)
    is_active = models.BooleanField(default=True)
    restrict_to_templates = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=datetime.utcnow)
    last_used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    allowed_templates = models.ManyToManyField(
        "templates_app.Template",
        through=APIKeyTemplate,
        related_name="api_keys_allowed",
        blank=True,
    )

    class Meta:
        db_table = "api_keys"

    def __str__(self):
        return f"APIKey({self.id}, {self.name})"


class APIKeyUsage(models.Model):
    api_key = models.ForeignKey(APIKey, on_delete=models.CASCADE, related_name="usage_records")
    tenant = models.ForeignKey("accounts.Tenant", on_delete=models.CASCADE, related_name="api_key_usage")
    endpoint = models.CharField(max_length=255)
    method = models.CharField(max_length=10)
    status_code = models.IntegerField(null=True, blank=True)
    template = models.ForeignKey("templates_app.Template", on_delete=models.SET_NULL, null=True, blank=True, related_name="api_key_usage")
    document = models.ForeignKey("documents.Document", on_delete=models.SET_NULL, null=True, blank=True, related_name="api_key_usage")
    ip_address = models.CharField(max_length=45, null=True, blank=True)
    user_agent = models.CharField(max_length=500, null=True, blank=True)
    response_time_ms = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=datetime.utcnow)

    class Meta:
        db_table = "api_key_usage"
        indexes = [
            models.Index(fields=["api_key", "created_at"], name="ix_apikeyusage_key_date"),
            models.Index(fields=["tenant", "created_at"], name="ix_apikeyusage_tenant_date"),
        ]

    def __str__(self):
        return f"APIKeyUsage({self.id}, key={self.api_key_id})"


class APIKeyDailyStats(models.Model):
    api_key = models.ForeignKey(APIKey, on_delete=models.CASCADE, related_name="daily_stats")
    tenant = models.ForeignKey("accounts.Tenant", on_delete=models.CASCADE, related_name="api_key_daily_stats")
    date = models.DateTimeField()
    total_requests = models.IntegerField(default=0)
    successful_requests = models.IntegerField(default=0)
    failed_requests = models.IntegerField(default=0)
    documents_accessed = models.IntegerField(default=0)
    templates_accessed = models.IntegerField(default=0)
    extractions_performed = models.IntegerField(default=0)
    avg_response_time_ms = models.IntegerField(null=True, blank=True)
    max_response_time_ms = models.IntegerField(null=True, blank=True)
    quota_used = models.IntegerField(default=0)
    quota_limit = models.IntegerField(default=1000)
    rate_limit_hits = models.IntegerField(default=0)

    class Meta:
        db_table = "api_key_daily_stats"
        indexes = [
            models.Index(fields=["api_key", "date"], name="ix_apikeyds_key_date"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["api_key", "date"], name="uq_apikeyds_key_date"),
        ]

    def __str__(self):
        return f"APIKeyDailyStats(key={self.api_key_id}, date={self.date})"

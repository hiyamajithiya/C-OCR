"""
Minimal serializers for the audit app.
Most responses are built inline as dicts.
"""

from rest_framework import serializers
from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = [
            "id", "tenant_id", "actor_user_id", "actor_api_key_id", "action",
            "entity_type", "entity_id", "ip", "user_agent", "metadata_json", "created_at",
        ]
        read_only_fields = fields

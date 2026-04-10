"""
Minimal serializers for the api_keys app.
Most responses are built inline as dicts.
"""

from rest_framework import serializers
from .models import APIKey


class APIKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = APIKey
        fields = [
            "id", "name", "key_prefix", "scopes", "rate_limit", "daily_quota",
            "is_active", "restrict_to_templates", "created_at", "last_used_at", "expires_at",
        ]
        read_only_fields = fields

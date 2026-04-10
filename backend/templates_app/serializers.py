"""
Minimal serializers for the templates_app.
Most responses are built inline as dicts.
"""

from rest_framework import serializers
from .models import Template, TemplateVersion


class TemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Template
        fields = ["id", "name", "description", "doc_category", "is_active", "created_at"]
        read_only_fields = fields


class TemplateVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplateVersion
        fields = [
            "id", "template_id", "version_no", "signature_json", "fields_json",
            "rules_json", "is_active", "is_approved", "created_at", "created_by_id",
        ]
        read_only_fields = fields

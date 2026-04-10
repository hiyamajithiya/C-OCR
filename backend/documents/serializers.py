"""
Minimal serializers for the documents app.
Most responses are built inline as dicts.
"""

from rest_framework import serializers
from .models import Document


class DocumentMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ["id", "filename", "mime_type", "page_count", "status", "source", "created_at"]
        read_only_fields = fields

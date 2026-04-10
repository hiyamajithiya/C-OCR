"""
Minimal serializers for the corrections app.
Most responses are built inline as dicts.
"""

from rest_framework import serializers
from .models import ExtractionCorrection, FieldAbbreviation


class ExtractionCorrectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtractionCorrection
        fields = [
            "id", "document_id", "template_id", "template_version_id",
            "extraction_result_id", "field_name", "field_label", "field_type",
            "original_value", "original_confidence", "extraction_method",
            "corrected_value", "correction_note", "is_processed",
            "corrected_by_id", "created_at",
        ]
        read_only_fields = fields


class FieldAbbreviationSerializer(serializers.ModelSerializer):
    class Meta:
        model = FieldAbbreviation
        fields = [
            "id", "abbreviation", "expanded_form", "field_type",
            "doc_category", "source", "usage_count", "success_count",
            "is_active", "created_at",
        ]
        read_only_fields = fields

"""
Corrections views — DRF APIView replacements for FastAPI endpoints.
"""

from datetime import datetime, timedelta
from django.conf import settings as django_settings
from django.db.models import Count, Avg, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from core.authentication import JWTBearerAuthentication, APIKeyAuthentication
from core.permissions import IsActiveUser, IsAdminUser, IsReviewerOrAdmin, AllowAny, IsAPIKeyAuthenticated

from .models import ExtractionCorrection, FieldAbbreviation, TemplateAccuracy, MLModel
from audit.models import AuditLog


def _serialize_correction(c):
    return {
        "id": c.id,
        "tenant_id": c.tenant_id,
        "document_id": c.document_id,
        "template_id": c.template_id,
        "template_version_id": c.template_version_id,
        "extraction_result_id": c.extraction_result_id,
        "field_name": c.field_name,
        "field_label": c.field_label,
        "field_type": c.field_type,
        "original_value": c.original_value,
        "original_confidence": c.original_confidence,
        "extraction_method": c.extraction_method,
        "corrected_value": c.corrected_value,
        "correction_note": c.correction_note,
        "is_processed": c.is_processed,
        "corrected_by_id": c.corrected_by_id,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def _serialize_abbreviation(a):
    return {
        "id": a.id,
        "tenant_id": a.tenant_id,
        "abbreviation": a.abbreviation,
        "expanded_form": a.expanded_form,
        "field_type": a.field_type,
        "doc_category": a.doc_category,
        "source": a.source,
        "usage_count": a.usage_count,
        "success_count": a.success_count,
        "is_active": a.is_active,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }


def _derive_template_ids(extraction_result_id, request_data):
    """
    Return (template_id, template_version_id) for a correction.
    Prefers explicit values from request, otherwise looks them up via
    the linked ExtractionResult so every correction is trainable.
    """
    template_id = request_data.get("template_id")
    template_version_id = request_data.get("template_version_id")

    if (not template_id or not template_version_id) and extraction_result_id:
        from extractions.models import ExtractionResult
        try:
            er = ExtractionResult.objects.only(
                "id", "template_id", "template_version_id"
            ).get(id=extraction_result_id)
            if not template_id:
                template_id = er.template_id
            if not template_version_id:
                template_version_id = er.template_version_id
        except ExtractionResult.DoesNotExist:
            pass

    return template_id, template_version_id


class SubmitCorrectionView(APIView):
    authentication_classes = [JWTBearerAuthentication]
    permission_classes = [IsActiveUser]

    def post(self, request):
        """Submit a single correction."""
        document_id = request.data.get("document_id")
        if not document_id:
            return Response({"detail": "document_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        field_name = request.data.get("field_name")
        corrected_value = request.data.get("corrected_value")
        if not field_name or corrected_value is None:
            return Response(
                {"detail": "field_name and corrected_value are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from documents.models import Document
        try:
            document = Document.objects.get(id=document_id, tenant=request.user.tenant)
        except Document.DoesNotExist:
            return Response({"detail": "Document not found"}, status=status.HTTP_404_NOT_FOUND)

        extraction_result_id = request.data.get("extraction_result_id")
        template_id, template_version_id = _derive_template_ids(extraction_result_id, request.data)

        correction = ExtractionCorrection.objects.create(
            tenant=request.user.tenant,
            document=document,
            template_id=template_id,
            template_version_id=template_version_id,
            extraction_result_id=extraction_result_id,
            field_name=field_name,
            field_label=request.data.get("field_label"),
            field_type=request.data.get("field_type"),
            original_value=request.data.get("original_value"),
            original_confidence=request.data.get("original_confidence"),
            extraction_method=request.data.get("extraction_method"),
            corrected_value=corrected_value,
            correction_note=request.data.get("correction_note"),
            corrected_by=request.user,
        )

        AuditLog.objects.create(
            tenant=request.user.tenant,
            actor_user=request.user,
            action="correction_submit",
            entity_type="extraction_correction",
            entity_id=correction.id,
            ip=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        return Response(_serialize_correction(correction), status=status.HTTP_201_CREATED)


class BulkCorrectionView(APIView):
    authentication_classes = [JWTBearerAuthentication]
    permission_classes = [IsActiveUser]

    def post(self, request):
        """Submit multiple corrections at once."""
        document_id = request.data.get("document_id")
        if not document_id:
            return Response({"detail": "document_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        corrections_data = request.data.get("corrections", [])
        if not corrections_data:
            return Response({"detail": "corrections list is required"}, status=status.HTTP_400_BAD_REQUEST)

        from documents.models import Document
        try:
            document = Document.objects.get(id=document_id, tenant=request.user.tenant)
        except Document.DoesNotExist:
            return Response({"detail": "Document not found"}, status=status.HTTP_404_NOT_FOUND)

        extraction_result_id = request.data.get("extraction_result_id")
        template_id, template_version_id = _derive_template_ids(extraction_result_id, request.data)
        created = []

        for item in corrections_data:
            # Per-item overrides are still honored
            item_template_id = item.get("template_id", template_id)
            item_template_version_id = item.get("template_version_id", template_version_id)
            item_er_id = item.get("extraction_result_id", extraction_result_id)

            if (not item_template_id or not item_template_version_id) and item_er_id != extraction_result_id:
                item_template_id, item_template_version_id = _derive_template_ids(item_er_id, item)

            correction = ExtractionCorrection.objects.create(
                tenant=request.user.tenant,
                document=document,
                template_id=item_template_id,
                template_version_id=item_template_version_id,
                extraction_result_id=item_er_id,
                field_name=item.get("field_name"),
                field_label=item.get("field_label"),
                field_type=item.get("field_type"),
                original_value=item.get("original_value"),
                original_confidence=item.get("original_confidence"),
                extraction_method=item.get("extraction_method"),
                corrected_value=item.get("corrected_value"),
                correction_note=item.get("correction_note"),
                corrected_by=request.user,
            )
            created.append(correction)

        AuditLog.objects.create(
            tenant=request.user.tenant,
            actor_user=request.user,
            action="correction_submit_bulk",
            entity_type="extraction_correction",
            entity_id=created[0].id if created else None,
            ip=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            metadata_json={"count": len(created), "document_id": document_id},
        )

        return Response(
            [_serialize_correction(c) for c in created],
            status=status.HTTP_201_CREATED,
        )


class DocumentCorrectionsView(APIView):
    authentication_classes = [JWTBearerAuthentication]
    permission_classes = [IsActiveUser]

    def get(self, request, document_id):
        """List corrections for a document."""
        from documents.models import Document
        try:
            document = Document.objects.get(id=document_id, tenant=request.user.tenant)
        except Document.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        corrections = ExtractionCorrection.objects.filter(
            document=document
        ).order_by("-created_at")

        return Response([_serialize_correction(c) for c in corrections])


class TemplateAccuracyView(APIView):
    authentication_classes = [JWTBearerAuthentication]
    permission_classes = [IsActiveUser]

    def get(self, request, template_id):
        """Get accuracy stats for a template."""
        from templates_app.models import Template

        try:
            template = Template.objects.get(id=template_id, tenant=request.user.tenant)
        except Template.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        days = int(request.query_params.get("days", 30))
        since = datetime.utcnow() - timedelta(days=days)

        # Query accuracy records
        accuracy_records = TemplateAccuracy.objects.filter(
            template=template, period_start__gte=since
        )

        total_extractions = sum(r.total_extractions for r in accuracy_records)
        total_corrections_count = sum(r.total_corrections for r in accuracy_records)
        avg_confidence_vals = [r.avg_confidence for r in accuracy_records if r.avg_confidence is not None]
        avg_confidence = sum(avg_confidence_vals) / len(avg_confidence_vals) if avg_confidence_vals else None

        accuracy_rate = (
            (1 - total_corrections_count / total_extractions) * 100
            if total_extractions > 0
            else None
        )

        # Field-level stats from corrections
        field_stats = (
            ExtractionCorrection.objects.filter(template=template, created_at__gte=since)
            .values("field_name")
            .annotate(
                correction_count=Count("id"),
                avg_original_confidence=Avg("original_confidence"),
            )
            .order_by("-correction_count")
        )

        return Response({
            "template_id": template.id,
            "template_name": template.name,
            "total_extractions": total_extractions,
            "total_corrections": total_corrections_count,
            "accuracy_rate": accuracy_rate,
            "avg_confidence": avg_confidence,
            "field_stats": list(field_stats),
        })


class AbbreviationListCreateView(APIView):
    authentication_classes = [JWTBearerAuthentication]
    permission_classes = [IsActiveUser]

    def get(self, request):
        """List abbreviations."""
        include_global = request.query_params.get("include_global", "true").lower() == "true"

        if include_global:
            qs = FieldAbbreviation.objects.filter(
                Q(tenant=request.user.tenant) | Q(tenant__isnull=True),
                is_active=True,
            )
        else:
            qs = FieldAbbreviation.objects.filter(
                tenant=request.user.tenant,
                is_active=True,
            )

        return Response([_serialize_abbreviation(a) for a in qs.order_by("abbreviation")])

    def post(self, request):
        """Create an abbreviation."""
        abbreviation_text = request.data.get("abbreviation")
        expanded_form = request.data.get("expanded_form")
        if not abbreviation_text or not expanded_form:
            return Response(
                {"detail": "abbreviation and expanded_form are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        abbr = FieldAbbreviation.objects.create(
            tenant=request.user.tenant,
            abbreviation=abbreviation_text,
            expanded_form=expanded_form,
            field_type=request.data.get("field_type"),
            doc_category=request.data.get("doc_category"),
            source="manual",
        )

        AuditLog.objects.create(
            tenant=request.user.tenant,
            actor_user=request.user,
            action="abbreviation_create",
            entity_type="field_abbreviation",
            entity_id=abbr.id,
            ip=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        return Response(_serialize_abbreviation(abbr), status=status.HTTP_201_CREATED)


class AbbreviationDeleteView(APIView):
    authentication_classes = [JWTBearerAuthentication]
    permission_classes = [IsActiveUser]

    def delete(self, request, abbreviation_id):
        """Deactivate an abbreviation."""
        try:
            abbr = FieldAbbreviation.objects.get(
                id=abbreviation_id, tenant=request.user.tenant
            )
        except FieldAbbreviation.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        abbr.is_active = False
        abbr.save()

        AuditLog.objects.create(
            tenant=request.user.tenant,
            actor_user=request.user,
            action="abbreviation_delete",
            entity_type="field_abbreviation",
            entity_id=abbr.id,
            ip=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        return Response({"detail": "Abbreviation deactivated"})


class ProcessLearningView(APIView):
    authentication_classes = [JWTBearerAuthentication]
    permission_classes = [IsActiveUser]

    def post(self, request):
        """Trigger ML learning process for templates with sufficient corrections."""
        from services.learning_service import learning_service
        from services.ml_training_service import ml_training_service

        AuditLog.objects.create(
            tenant=request.user.tenant,
            actor_user=request.user,
            action="learning_process",
            entity_type="learning",
            ip=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        # First, process and mark all pending corrections so history no longer stays pending.
        learning_summary = learning_service.process_corrections(request.user.tenant_id)

        # Then train ML models for template+field combos with sufficient corrections.
        min_corrections = getattr(django_settings, "ML_MIN_CORRECTIONS", 5)
        field_groups = (
            ExtractionCorrection.objects.filter(
                tenant=request.user.tenant,
                template__isnull=False,
            )
            .values("template_id", "field_name")
            .annotate(correction_count=Count("id"))
            .filter(correction_count__gte=min_corrections)
        )

        training_results = []
        for group in field_groups:
            template_id = group["template_id"]
            field_name = group["field_name"]

            result = ml_training_service.train_field_model(template_id, field_name)
            result["template_id"] = template_id
            result["field_name"] = field_name
            training_results.append(result)

        return Response({
            "status": "completed",
            "processed_count": learning_summary.get("processed_count", 0),
            "abbreviations_learned": learning_summary.get("abbreviations_learned", 0),
            "training_models_count": len(training_results),
            "training_results": training_results,
        })


class TemplateTrainingStatusView(APIView):
    """
    GET /api/v1/corrections/template/<template_id>/training-status

    Returns per-field correction counts + active ML model metadata for
    the given template. Powers the UI "ML Model Trained" badges.
    """

    authentication_classes = [JWTBearerAuthentication]
    permission_classes = [IsActiveUser]

    def get(self, request, template_id):
        from templates_app.models import Template, TemplateVersion

        try:
            template = Template.objects.get(id=template_id, tenant=request.user.tenant)
        except Template.DoesNotExist:
            return Response({"detail": "Template not found"}, status=status.HTTP_404_NOT_FOUND)

        min_corrections = getattr(django_settings, "ML_MIN_CORRECTIONS", 5)

        # Field definitions come from the most recent template version
        latest_version = (
            TemplateVersion.objects.filter(template=template)
            .order_by("-version_no")
            .first()
        )
        field_defs = []
        if latest_version and isinstance(latest_version.fields_json, dict):
            field_defs = latest_version.fields_json.get("fields", []) or []

        # Aggregate correction counts per field
        correction_counts = {
            row["field_name"]: {
                "total": row["total"],
                "unprocessed": row["unprocessed"],
            }
            for row in (
                ExtractionCorrection.objects.filter(
                    tenant=request.user.tenant, template=template
                )
                .values("field_name")
                .annotate(
                    total=Count("id"),
                    unprocessed=Count("id", filter=Q(is_processed=False)),
                )
            )
        }

        # Active ML models per field
        active_models = {
            model.field_name: model
            for model in MLModel.objects.filter(
                template=template, is_active=True
            ).order_by("-version")
        }

        fields_status = []
        seen_field_names = set()

        # Prefer template-defined fields so the UI order matches the template
        for field_def in field_defs:
            field_name = field_def.get("name")
            if not field_name or field_name in seen_field_names:
                continue
            seen_field_names.add(field_name)

            counts = correction_counts.get(field_name, {"total": 0, "unprocessed": 0})
            model = active_models.get(field_name)
            fields_status.append(
                {
                    "field_name": field_name,
                    "field_label": field_def.get("label", field_name),
                    "total_corrections": counts["total"],
                    "unprocessed_corrections": counts["unprocessed"],
                    "ready_to_train": counts["total"] >= min_corrections,
                    "model_active": bool(model),
                    "model_version": model.version if model else None,
                    "accuracy_score": model.accuracy_score if model else None,
                    "training_samples": model.training_samples if model else 0,
                }
            )

        # Include any fields that exist as corrections but were removed from the template
        for field_name, counts in correction_counts.items():
            if field_name in seen_field_names:
                continue
            model = active_models.get(field_name)
            fields_status.append(
                {
                    "field_name": field_name,
                    "field_label": field_name,
                    "total_corrections": counts["total"],
                    "unprocessed_corrections": counts["unprocessed"],
                    "ready_to_train": counts["total"] >= min_corrections,
                    "model_active": bool(model),
                    "model_version": model.version if model else None,
                    "accuracy_score": model.accuracy_score if model else None,
                    "training_samples": model.training_samples if model else 0,
                }
            )

        trained_count = sum(1 for f in fields_status if f["model_active"])

        return Response(
            {
                "template_id": template.id,
                "template_name": template.name,
                "min_corrections": min_corrections,
                "total_fields": len(fields_status),
                "trained_fields": trained_count,
                "fields": fields_status,
            }
        )

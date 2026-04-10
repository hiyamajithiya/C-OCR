"""
External API views — DRF APIView endpoints for API-key-authenticated access.
"""

from datetime import datetime, timedelta
from django.db.models import Count, Avg, Max
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from core.authentication import JWTBearerAuthentication, APIKeyAuthentication
from core.permissions import IsActiveUser, IsAdminUser, IsReviewerOrAdmin, AllowAny, IsAPIKeyAuthenticated

from templates_app.models import Template, TemplateVersion
from documents.models import Document, DocumentFile
from extractions.models import ExtractionResult
from api_keys.models import APIKeyUsage, APIKeyDailyStats
from audit.models import AuditLog


class ExternalTemplateListView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAPIKeyAuthenticated]

    def get(self, request):
        """List templates accessible to the API key."""
        api_key = request.api_key
        tenant = request.tenant

        qs = Template.objects.filter(tenant=tenant, is_active=True)
        if api_key.restrict_to_templates:
            qs = qs.filter(api_keys_allowed=api_key)

        data = [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "doc_category": t.doc_category,
                "is_active": t.is_active,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in qs.order_by("-created_at")
        ]
        return Response(data)


class ExternalDocumentUploadView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAPIKeyAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        """Upload a document via API key."""
        tenant = request.tenant
        api_key = request.api_key

        file = request.FILES.get("file")
        if not file:
            return Response({"detail": "file is required"}, status=status.HTTP_400_BAD_REQUEST)

        template_id = request.data.get("template_id")
        language = request.data.get("language", "en")

        document = Document.objects.create(
            tenant=tenant,
            filename=file.name,
            mime_type=file.content_type or "application/octet-stream",
            status="uploaded",
            source="api",
        )

        # Save file
        from django.conf import settings as django_settings
        import os

        upload_dir = os.path.join(
            getattr(django_settings, "MEDIA_ROOT", "storage"),
            "documents",
            str(tenant.id),
        )
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, f"{document.id}_{file.name}")

        with open(file_path, "wb") as dest:
            for chunk in file.chunks():
                dest.write(chunk)

        DocumentFile.objects.create(
            document=document,
            kind="original",
            path=file_path,
        )

        AuditLog.objects.create(
            tenant=tenant,
            actor_api_key=api_key,
            action="document_upload_api",
            entity_type="document",
            entity_id=document.id,
            ip=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            metadata_json={"template_id": template_id, "language": language},
        )

        return Response(
            {
                "id": document.id,
                "filename": document.filename,
                "mime_type": document.mime_type,
                "status": document.status,
                "source": document.source,
                "created_at": document.created_at.isoformat() if document.created_at else None,
            },
            status=status.HTTP_201_CREATED,
        )


class ExternalDocumentDetailView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAPIKeyAuthenticated]

    def get(self, request, document_id):
        """Get document metadata."""
        tenant = request.tenant

        try:
            document = Document.objects.get(id=document_id, tenant=tenant)
        except Document.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "id": document.id,
            "filename": document.filename,
            "mime_type": document.mime_type,
            "page_count": document.page_count,
            "status": document.status,
            "source": document.source,
            "created_at": document.created_at.isoformat() if document.created_at else None,
            "updated_at": document.updated_at.isoformat() if document.updated_at else None,
        })


class ExternalExtractionView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAPIKeyAuthenticated]

    def get(self, request, document_id):
        """Get extraction results for a document."""
        tenant = request.tenant

        try:
            document = Document.objects.get(id=document_id, tenant=tenant)
        except Document.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        results = ExtractionResult.objects.filter(document=document).select_related(
            "template", "template_version"
        ).order_by("-created_at")

        data = [
            {
                "id": r.id,
                "document_id": r.document_id,
                "template_id": r.template_id,
                "template_name": r.template.name if r.template else None,
                "template_version_id": r.template_version_id,
                "version_no": r.template_version.version_no if r.template_version else None,
                "result_json": r.result_json,
                "confidence_json": r.confidence_json,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in results
        ]
        return Response(data)


class ExternalExtractView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAPIKeyAuthenticated]

    def post(self, request, document_id):
        """Apply a template to a document."""
        tenant = request.tenant
        api_key = request.api_key

        template_id = request.data.get("template_id")
        if not template_id:
            return Response({"detail": "template_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            document = Document.objects.get(id=document_id, tenant=tenant)
        except Document.DoesNotExist:
            return Response({"detail": "Document not found"}, status=status.HTTP_404_NOT_FOUND)

        # Check template access
        qs = Template.objects.filter(id=template_id, tenant=tenant, is_active=True)
        if api_key.restrict_to_templates:
            qs = qs.filter(api_keys_allowed=api_key)

        try:
            template = qs.get()
        except Template.DoesNotExist:
            return Response({"detail": "Template not found or not accessible"}, status=status.HTTP_404_NOT_FOUND)

        # Get active version
        version = TemplateVersion.objects.filter(
            template=template, is_active=True
        ).order_by("-version_no").first()
        if not version:
            return Response({"detail": "No active template version"}, status=status.HTTP_400_BAD_REQUEST)

        # Extract
        try:
            from services.template_service import TemplateService, FieldExtractor

            template_service = TemplateService()
            ocr_data = template_service.read_ocr_data(document)
            extractor = FieldExtractor(version.fields_json, version.rules_json)
            extracted = extractor.extract(ocr_data)
        except Exception as e:
            return Response(
                {"detail": f"Extraction failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        result = ExtractionResult.objects.create(
            document=document,
            template=template,
            template_version=version,
            result_json=extracted.get("fields", {}),
            confidence_json=extracted.get("confidence", {}),
        )

        AuditLog.objects.create(
            tenant=tenant,
            actor_api_key=api_key,
            action="template_apply",
            entity_type="extraction_result",
            entity_id=result.id,
            ip=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            metadata_json={"template_id": template.id, "document_id": document.id},
        )

        return Response({
            "id": result.id,
            "document_id": result.document_id,
            "template_id": result.template_id,
            "template_version_id": result.template_version_id,
            "result_json": result.result_json,
            "confidence_json": result.confidence_json,
            "created_at": result.created_at.isoformat() if result.created_at else None,
        })


class ExternalUsageStatsView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAPIKeyAuthenticated]

    def get(self, request):
        """Get API key usage stats."""
        api_key = request.api_key

        days = min(int(request.query_params.get("days", 30)), 90)
        since = datetime.utcnow() - timedelta(days=days)

        daily_stats = APIKeyDailyStats.objects.filter(
            api_key=api_key, date__gte=since
        ).order_by("date")

        usage_count = APIKeyUsage.objects.filter(
            api_key=api_key, created_at__gte=since
        ).count()

        data = {
            "api_key_id": api_key.id,
            "api_key_name": api_key.name,
            "period_days": days,
            "total_requests": usage_count,
            "daily_stats": [
                {
                    "date": s.date.isoformat() if s.date else None,
                    "total_requests": s.total_requests,
                    "successful_requests": s.successful_requests,
                    "failed_requests": s.failed_requests,
                    "documents_accessed": s.documents_accessed,
                    "extractions_performed": s.extractions_performed,
                    "avg_response_time_ms": s.avg_response_time_ms,
                    "quota_used": s.quota_used,
                    "quota_limit": s.quota_limit,
                }
                for s in daily_stats
            ],
        }
        return Response(data)

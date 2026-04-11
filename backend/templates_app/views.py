"""
Template views — DRF APIView replacements for FastAPI endpoints.
"""

from django.db.models import Max
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from core.authentication import JWTBearerAuthentication, APIKeyAuthentication
from core.permissions import IsActiveUser, IsAdminUser, IsReviewerOrAdmin, AllowAny, IsAPIKeyAuthenticated

from .models import Template, TemplateVersion
from audit.models import AuditLog
from extractions.models import ExtractionResult


class TemplateListCreateView(APIView):
    authentication_classes = [JWTBearerAuthentication]
    permission_classes = [IsActiveUser]

    def get(self, request):
        """List templates for the current user's tenant."""
        templates = Template.objects.filter(tenant=request.user.tenant).order_by("-created_at")
        data = [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "doc_category": t.doc_category,
                "is_active": t.is_active,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in templates
        ]
        return Response(data)

    def post(self, request):
        """Create a new template."""
        name = request.data.get("name")
        if not name:
            return Response({"detail": "name is required"}, status=status.HTTP_400_BAD_REQUEST)

        template = Template.objects.create(
            tenant=request.user.tenant,
            name=name,
            description=request.data.get("description"),
            doc_category=request.data.get("doc_category"),
        )

        AuditLog.objects.create(
            tenant=request.user.tenant,
            actor_user=request.user,
            action="template_create",
            entity_type="template",
            entity_id=template.id,
            ip=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        return Response(
            {
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "doc_category": template.doc_category,
                "is_active": template.is_active,
                "created_at": template.created_at.isoformat() if template.created_at else None,
            },
            status=status.HTTP_201_CREATED,
        )


class TemplateVersionListCreateView(APIView):
    authentication_classes = [JWTBearerAuthentication]
    permission_classes = [IsActiveUser]

    def _serialize_version(self, v):
        return {
            "id": v.id,
            "template_id": v.template_id,
            "version_no": v.version_no,
            "signature_json": v.signature_json,
            "fields_json": v.fields_json,
            "rules_json": v.rules_json,
            "is_active": v.is_active,
            "is_approved": v.is_approved,
            "created_at": v.created_at.isoformat() if v.created_at else None,
            "created_by_id": v.created_by_id,
        }

    def get(self, request, template_id):
        """List versions for a template."""
        try:
            template = Template.objects.get(id=template_id, tenant=request.user.tenant)
        except Template.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        versions = TemplateVersion.objects.filter(template=template).order_by("-version_no")
        return Response([self._serialize_version(v) for v in versions])

    def post(self, request, template_id):
        """Create a new template version."""
        try:
            template = Template.objects.get(id=template_id, tenant=request.user.tenant)
        except Template.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        max_version = TemplateVersion.objects.filter(template=template).aggregate(
            max_v=Max("version_no")
        )["max_v"] or 0

        version = TemplateVersion.objects.create(
            template=template,
            version_no=max_version + 1,
            signature_json=request.data.get("signature_json", {}),
            fields_json=request.data.get("fields_json", {}),
            rules_json=request.data.get("rules_json", {}),
            created_by=request.user,
        )

        AuditLog.objects.create(
            tenant=request.user.tenant,
            actor_user=request.user,
            action="template_version_create",
            entity_type="template_version",
            entity_id=version.id,
            ip=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        return Response(self._serialize_version(version), status=status.HTTP_201_CREATED)


class ApplyTemplateView(APIView):
    authentication_classes = [JWTBearerAuthentication]
    permission_classes = [IsActiveUser]

    def post(self, request, template_id):
        """Apply a template to a document."""
        from documents.models import Document
        from services.template_service import TemplateService, FieldExtractor

        document_id = request.data.get("document_id")
        if not document_id:
            return Response({"detail": "document_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            template = Template.objects.get(id=template_id, tenant=request.user.tenant)
        except Template.DoesNotExist:
            return Response({"detail": "Template not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            document = Document.objects.get(id=document_id, tenant=request.user.tenant)
        except Document.DoesNotExist:
            return Response({"detail": "Document not found"}, status=status.HTTP_404_NOT_FOUND)

        # Get active version
        version = TemplateVersion.objects.filter(
            template=template, is_active=True
        ).order_by("-version_no").first()
        if not version:
            return Response({"detail": "No active template version"}, status=status.HTTP_400_BAD_REQUEST)

        # Read OCR data and extract fields
        try:
            template_service = TemplateService()
            ocr_data = template_service.read_ocr_data(document)
            extractor = FieldExtractor(version.fields_json, version.rules_json)
            extracted = extractor.extract(ocr_data)
        except Exception as e:
            return Response({"detail": f"Extraction failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Save extraction result
        result = ExtractionResult.objects.create(
            document=document,
            template=template,
            template_version=version,
            result_json=extracted.get("fields", {}),
            confidence_json=extracted.get("confidence", {}),
        )

        AuditLog.objects.create(
            tenant=request.user.tenant,
            actor_user=request.user,
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


class DocumentExtractionsView(APIView):
    authentication_classes = [JWTBearerAuthentication]
    permission_classes = [IsActiveUser]

    def get(self, request, document_id):
        """Get all extraction results for a document."""
        from documents.models import Document

        try:
            document = Document.objects.get(id=document_id, tenant=request.user.tenant)
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


class TemplateDeleteView(APIView):
    authentication_classes = [JWTBearerAuthentication]
    permission_classes = [IsActiveUser]

    def delete(self, request, template_id):
        """Delete a template and its versions for the current tenant."""
        try:
            template = Template.objects.get(id=template_id, tenant=request.user.tenant)
        except Template.DoesNotExist:
            return Response({"detail": "Template not found"}, status=status.HTTP_404_NOT_FOUND)

        template_name = template.name
        template.delete()

        AuditLog.objects.create(
            tenant=request.user.tenant,
            actor_user=request.user,
            action="template_delete",
            entity_type="template",
            entity_id=template_id,
            ip=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            metadata_json={"name": template_name},
        )

        return Response(status=status.HTTP_204_NO_CONTENT)

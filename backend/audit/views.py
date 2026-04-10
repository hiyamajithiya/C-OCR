"""
Audit log views — DRF APIView replacements for FastAPI endpoints.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from core.authentication import JWTBearerAuthentication, APIKeyAuthentication
from core.permissions import IsActiveUser, IsAdminUser, IsReviewerOrAdmin, AllowAny, IsAPIKeyAuthenticated

from .models import AuditLog


def _serialize_log(log):
    return {
        "id": log.id,
        "tenant_id": log.tenant_id,
        "actor_user_id": log.actor_user_id,
        "actor_api_key_id": log.actor_api_key_id,
        "action": log.action,
        "entity_type": log.entity_type,
        "entity_id": log.entity_id,
        "ip": log.ip,
        "user_agent": log.user_agent,
        "metadata_json": log.metadata_json,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


class AuditLogListView(APIView):
    authentication_classes = [JWTBearerAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request):
        """List audit logs for the current tenant."""
        qs = AuditLog.objects.filter(tenant=request.user.tenant)

        action = request.query_params.get("action")
        if action:
            qs = qs.filter(action=action)

        entity_type = request.query_params.get("entity_type")
        if entity_type:
            qs = qs.filter(entity_type=entity_type)

        limit = min(int(request.query_params.get("limit", 50)), 100)
        offset = max(int(request.query_params.get("offset", 0)), 0)

        qs = qs.order_by("-created_at")[offset:offset + limit]

        return Response([_serialize_log(log) for log in qs])


class AuditLogDetailView(APIView):
    authentication_classes = [JWTBearerAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request, log_id):
        """Get a single audit log entry."""
        try:
            log = AuditLog.objects.get(id=log_id, tenant=request.user.tenant)
        except AuditLog.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response(_serialize_log(log))

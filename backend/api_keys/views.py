"""
API Key views — DRF APIView replacements for FastAPI endpoints.
"""

from datetime import datetime, timedelta
from django.db.models import Count, Avg, Sum
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from core.authentication import JWTBearerAuthentication, APIKeyAuthentication
from core.permissions import IsActiveUser, IsAdminUser, IsReviewerOrAdmin, AllowAny, IsAPIKeyAuthenticated
from core.security import generate_api_key, hash_api_key, get_api_key_prefix

from .models import APIKey, APIKeyUsage, APIKeyDailyStats
from audit.models import AuditLog


def _serialize_key(key):
    return {
        "id": key.id,
        "name": key.name,
        "key_prefix": key.key_prefix,
        "scopes": key.scopes,
        "rate_limit": key.rate_limit,
        "daily_quota": key.daily_quota,
        "is_active": key.is_active,
        "restrict_to_templates": key.restrict_to_templates,
        "created_at": key.created_at.isoformat() if key.created_at else None,
        "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
        "expires_at": key.expires_at.isoformat() if key.expires_at else None,
    }


class APIKeyListCreateView(APIView):
    authentication_classes = [JWTBearerAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request):
        """List API keys for tenant."""
        keys = APIKey.objects.filter(tenant=request.user.tenant).order_by("-created_at")
        return Response([_serialize_key(k) for k in keys])

    def post(self, request):
        """Create a new API key."""
        name = request.data.get("name")
        if not name:
            return Response({"detail": "name is required"}, status=status.HTTP_400_BAD_REQUEST)

        raw_key = generate_api_key()
        key_hash = hash_api_key(raw_key)
        key_prefix = get_api_key_prefix(raw_key)

        api_key = APIKey.objects.create(
            tenant=request.user.tenant,
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=name,
            scopes=request.data.get("scopes", []),
            rate_limit=request.data.get("rate_limit", 60),
            daily_quota=request.data.get("daily_quota", 1000),
            restrict_to_templates=request.data.get("restrict_to_templates", False),
            expires_at=request.data.get("expires_at"),
        )

        # Handle template restrictions
        template_ids = request.data.get("template_ids", [])
        if template_ids:
            from templates_app.models import Template
            templates = Template.objects.filter(id__in=template_ids, tenant=request.user.tenant)
            api_key.allowed_templates.set(templates)

        AuditLog.objects.create(
            tenant=request.user.tenant,
            actor_user=request.user,
            action="api_key_create",
            entity_type="api_key",
            entity_id=api_key.id,
            ip=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        data = _serialize_key(api_key)
        data["raw_key"] = raw_key
        return Response(data, status=status.HTTP_201_CREATED)


class APIKeyWithStatsView(APIView):
    authentication_classes = [JWTBearerAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request):
        """List API keys with usage stats."""
        keys = APIKey.objects.filter(tenant=request.user.tenant).order_by("-created_at")
        since = datetime.utcnow() - timedelta(days=30)

        result = []
        for key in keys:
            key_data = _serialize_key(key)
            # Basic inline stats
            stats = APIKeyDailyStats.objects.filter(
                api_key=key, date__gte=since
            ).aggregate(
                total_requests=Sum("total_requests"),
                successful_requests=Sum("successful_requests"),
                failed_requests=Sum("failed_requests"),
            )
            key_data["stats"] = {
                "total_requests": stats["total_requests"] or 0,
                "successful_requests": stats["successful_requests"] or 0,
                "failed_requests": stats["failed_requests"] or 0,
            }
            result.append(key_data)

        return Response(result)


class APIKeyStatsView(APIView):
    authentication_classes = [JWTBearerAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request, key_id):
        """Get usage stats for a specific API key."""
        try:
            api_key = APIKey.objects.get(id=key_id, tenant=request.user.tenant)
        except APIKey.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        days = int(request.query_params.get("days", 30))
        since = datetime.utcnow() - timedelta(days=days)

        daily_stats = APIKeyDailyStats.objects.filter(
            api_key=api_key, date__gte=since
        ).order_by("date")

        data = {
            "api_key_id": api_key.id,
            "api_key_name": api_key.name,
            "daily_stats": [
                {
                    "date": s.date.isoformat() if s.date else None,
                    "total_requests": s.total_requests,
                    "successful_requests": s.successful_requests,
                    "failed_requests": s.failed_requests,
                    "documents_accessed": s.documents_accessed,
                    "templates_accessed": s.templates_accessed,
                    "extractions_performed": s.extractions_performed,
                    "avg_response_time_ms": s.avg_response_time_ms,
                    "quota_used": s.quota_used,
                    "quota_limit": s.quota_limit,
                    "rate_limit_hits": s.rate_limit_hits,
                }
                for s in daily_stats
            ],
        }
        return Response(data)


class APIKeyUpdateStatsView(APIView):
    authentication_classes = [JWTBearerAuthentication]
    permission_classes = [IsAdminUser]

    def post(self, request, key_id):
        """Trigger daily stats update for a key."""
        try:
            api_key = APIKey.objects.get(id=key_id, tenant=request.user.tenant)
        except APIKey.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        # Basic stats computation from usage records
        today = datetime.utcnow().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())

        usage_qs = APIKeyUsage.objects.filter(
            api_key=api_key,
            created_at__gte=today_start,
            created_at__lte=today_end,
        )
        agg = usage_qs.aggregate(
            total=Count("id"),
            avg_response=Avg("response_time_ms"),
        )

        successful = usage_qs.filter(status_code__gte=200, status_code__lt=400).count()

        stats, _ = APIKeyDailyStats.objects.update_or_create(
            api_key=api_key,
            date=today_start,
            defaults={
                "tenant": api_key.tenant,
                "total_requests": agg["total"] or 0,
                "successful_requests": successful,
                "failed_requests": (agg["total"] or 0) - successful,
                "avg_response_time_ms": int(agg["avg_response"] or 0),
                "quota_used": agg["total"] or 0,
                "quota_limit": api_key.daily_quota,
            },
        )

        return Response({"status": "updated", "date": today.isoformat()})


class APIKeyTemplatesView(APIView):
    authentication_classes = [JWTBearerAuthentication]
    permission_classes = [IsAdminUser]

    def put(self, request, key_id):
        """Update template restrictions for an API key."""
        try:
            api_key = APIKey.objects.get(id=key_id, tenant=request.user.tenant)
        except APIKey.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        template_ids = request.data.get("template_ids", [])
        from templates_app.models import Template
        templates = Template.objects.filter(id__in=template_ids, tenant=request.user.tenant)
        api_key.allowed_templates.clear()
        api_key.allowed_templates.set(templates)

        return Response({
            "api_key_id": api_key.id,
            "template_ids": list(templates.values_list("id", flat=True)),
        })


class APIKeyRevokeView(APIView):
    authentication_classes = [JWTBearerAuthentication]
    permission_classes = [IsAdminUser]

    def delete(self, request, key_id):
        """Deactivate (revoke) an API key."""
        try:
            api_key = APIKey.objects.get(id=key_id, tenant=request.user.tenant)
        except APIKey.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        api_key.is_active = False
        api_key.save()

        AuditLog.objects.create(
            tenant=request.user.tenant,
            actor_user=request.user,
            action="api_key_revoke",
            entity_type="api_key",
            entity_id=api_key.id,
            ip=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        return Response({"detail": "API key revoked"}, status=status.HTTP_200_OK)

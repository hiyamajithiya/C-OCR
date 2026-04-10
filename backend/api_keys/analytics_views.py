"""
Admin-only analytics dashboard endpoints.
"""

from datetime import datetime, timedelta

from django.db.models import Count, Sum, Avg, Q, F
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authentication import JWTBearerAuthentication
from core.permissions import IsAdminUser

from documents.models import Document
from entities.models import Entity, DocumentCharge
from api_keys.models import APIKeyUsage


class AnalyticsOverviewView(APIView):
    """GET /api/v1/analytics/overview -- high-level platform stats."""

    authentication_classes = [JWTBearerAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request):
        now = datetime.utcnow()
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_end = this_month_start - timedelta(seconds=1)
        last_month_start = last_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        total_documents = Document.objects.count()
        total_entities = Entity.objects.count()
        active_entities = Entity.objects.filter(status__in=["active", "trial"]).count()

        total_revenue = (
            DocumentCharge.objects.exclude(status="pending").aggregate(
                total=Sum("charge_amount")
            )["total"]
            or 0
        )

        api_calls_this_month = APIKeyUsage.objects.filter(
            created_at__gte=this_month_start
        ).count()

        api_calls_last_month = APIKeyUsage.objects.filter(
            created_at__gte=last_month_start,
            created_at__lt=this_month_start,
        ).count()

        return Response({
            "total_documents": total_documents,
            "total_entities": total_entities,
            "active_entities": active_entities,
            "total_revenue": float(total_revenue),
            "api_calls_this_month": api_calls_this_month,
            "api_calls_last_month": api_calls_last_month,
        })


class AnalyticsUsageView(APIView):
    """GET /api/v1/analytics/usage?period=daily&days=30 -- time-series usage."""

    authentication_classes = [JWTBearerAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request):
        period = request.query_params.get("period", "daily")
        days = int(request.query_params.get("days", 30))
        start_date = datetime.utcnow() - timedelta(days=days)

        trunc_fn = {
            "daily": TruncDate,
            "weekly": TruncWeek,
            "monthly": TruncMonth,
        }.get(period, TruncDate)

        # Document counts by date
        doc_qs = (
            Document.objects.filter(created_at__gte=start_date)
            .annotate(date=trunc_fn("created_at"))
            .values("date")
            .annotate(document_count=Count("id"))
            .order_by("date")
        )

        # API calls by date
        api_qs = (
            APIKeyUsage.objects.filter(created_at__gte=start_date)
            .annotate(date=trunc_fn("created_at"))
            .values("date")
            .annotate(api_calls=Count("id"))
            .order_by("date")
        )

        # Revenue by date
        rev_qs = (
            DocumentCharge.objects.filter(created_at__gte=start_date)
            .exclude(status="pending")
            .annotate(date=trunc_fn("created_at"))
            .values("date")
            .annotate(revenue=Sum("charge_amount"))
            .order_by("date")
        )

        # Merge all three into a single list keyed by date
        merged = {}
        for row in doc_qs:
            d = str(row["date"])
            merged.setdefault(d, {"date": d, "document_count": 0, "api_calls": 0, "revenue": 0})
            merged[d]["document_count"] = row["document_count"]

        for row in api_qs:
            d = str(row["date"])
            merged.setdefault(d, {"date": d, "document_count": 0, "api_calls": 0, "revenue": 0})
            merged[d]["api_calls"] = row["api_calls"]

        for row in rev_qs:
            d = str(row["date"])
            merged.setdefault(d, {"date": d, "document_count": 0, "api_calls": 0, "revenue": 0})
            merged[d]["revenue"] = float(row["revenue"])

        data = sorted(merged.values(), key=lambda x: x["date"])
        return Response(data)


class AnalyticsTopEntitiesView(APIView):
    """GET /api/v1/analytics/top-entities?limit=10 -- top entities by document count."""

    authentication_classes = [JWTBearerAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request):
        limit = int(request.query_params.get("limit", 10))

        # Entities with document counts via DocumentCharge
        entities = (
            Entity.objects.annotate(
                document_count=Count("charges__document", distinct=True),
                revenue=Sum("charges__charge_amount"),
            )
            .order_by("-document_count")[:limit]
        )

        data = [
            {
                "entity_id": e.id,
                "entity_name": e.name,
                "document_count": e.document_count,
                "revenue": float(e.revenue) if e.revenue else 0,
            }
            for e in entities
        ]

        return Response(data)


class AnalyticsRevenueView(APIView):
    """GET /api/v1/analytics/revenue?period=monthly -- revenue trends."""

    authentication_classes = [JWTBearerAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request):
        period = request.query_params.get("period", "monthly")
        months = int(request.query_params.get("months", 12))
        start_date = datetime.utcnow() - timedelta(days=months * 30)

        trunc_fn = TruncMonth if period == "monthly" else TruncDate

        rev_qs = (
            DocumentCharge.objects.filter(created_at__gte=start_date)
            .exclude(status="pending")
            .annotate(date=trunc_fn("created_at"))
            .values("date")
            .annotate(
                revenue=Sum("charge_amount"),
                document_count=Count("id"),
            )
            .order_by("date")
        )

        data = [
            {
                "date": str(row["date"]),
                "revenue": float(row["revenue"]),
                "document_count": row["document_count"],
            }
            for row in rev_qs
        ]

        return Response(data)


class AnalyticsEndpointsView(APIView):
    """GET /api/v1/analytics/endpoints -- most-used API endpoints."""

    authentication_classes = [JWTBearerAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request):
        days = int(request.query_params.get("days", 30))
        start_date = datetime.utcnow() - timedelta(days=days)

        endpoints = (
            APIKeyUsage.objects.filter(created_at__gte=start_date)
            .values("endpoint")
            .annotate(
                count=Count("id"),
                avg_response_time_ms=Avg("response_time_ms"),
            )
            .order_by("-count")[:20]
        )

        data = [
            {
                "endpoint": row["endpoint"],
                "count": row["count"],
                "avg_response_time_ms": (
                    round(row["avg_response_time_ms"], 2)
                    if row["avg_response_time_ms"] is not None
                    else None
                ),
            }
            for row in endpoints
        ]

        return Response(data)


class AnalyticsErrorsView(APIView):
    """GET /api/v1/analytics/errors -- daily error rate trends."""

    authentication_classes = [JWTBearerAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request):
        days = int(request.query_params.get("days", 30))
        start_date = datetime.utcnow() - timedelta(days=days)

        errors = (
            APIKeyUsage.objects.filter(
                created_at__gte=start_date,
                status_code__gte=400,
            )
            .annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(
                error_count=Count("id"),
                client_errors=Count("id", filter=Q(status_code__gte=400, status_code__lt=500)),
                server_errors=Count("id", filter=Q(status_code__gte=500)),
            )
            .order_by("date")
        )

        data = [
            {
                "date": str(row["date"]),
                "error_count": row["error_count"],
                "client_errors": row["client_errors"],
                "server_errors": row["server_errors"],
            }
            for row in errors
        ]

        return Response(data)

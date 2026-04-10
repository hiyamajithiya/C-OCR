"""
Admin-only entity management views.
"""

from datetime import datetime, timedelta, date
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, Count, Q, F

from core.authentication import JWTBearerAuthentication
from core.permissions import IsAdminUser
from core.security import get_password_hash

from accounts.models import Tenant
from audit.models import AuditLog
from api_keys.models import APIKey
from documents.models import Document

from entities.models import (
    Entity,
    EntityUser,
    DocumentCharge,
    Invoice,
    InvoiceLineItem,
)
from entities.serializers import (
    EntityCreateSerializer,
    EntityUpdateSerializer,
    EntityResponseSerializer,
    EntityUserCreateSerializer,
    InvoiceResponseSerializer,
    DocumentChargeResponseSerializer,
)


# ---------------------------------------------------------------------------
# Admin Entity CRUD
# ---------------------------------------------------------------------------


class EntityListCreateView(APIView):
    authentication_classes = [JWTBearerAuthentication]
    permission_classes = [IsAdminUser]

    def post(self, request):
        """Create entity + auto-create Tenant."""
        serializer = EntityCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Auto-create tenant
        tenant = Tenant.objects.create(name=data["name"])

        entity = Entity.objects.create(
            tenant=tenant,
            name=data["name"],
            contact_name=data["contact_name"],
            contact_email=data["contact_email"],
            contact_phone=data.get("contact_phone", ""),
            address=data.get("address", ""),
            gst_number=data.get("gst_number", ""),
            subscription_tier=data.get("subscription_tier", "free"),
            per_document_rate=data.get("per_document_rate", 2.00),
            monthly_document_limit=data.get("monthly_document_limit", 100),
            billing_cycle_start=date.today(),
        )

        AuditLog.objects.create(
            tenant=tenant,
            actor_user=request.user,
            action="entity_create",
            entity_type="Entity",
            entity_id=entity.id,
            ip=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            metadata_json={"entity_name": entity.name},
        )

        return Response(EntityResponseSerializer.serialize(entity), status=status.HTTP_201_CREATED)

    def get(self, request):
        """List all entities with basic usage stats."""
        entities = Entity.objects.select_related("tenant").all()
        results = []
        for entity in entities:
            data = EntityResponseSerializer.serialize(entity)
            total_charges = (
                DocumentCharge.objects.filter(entity=entity)
                .aggregate(total=Sum("charge_amount"))["total"]
            ) or 0
            data["total_charges"] = float(total_charges)
            results.append(data)
        return Response(results)


class EntityDetailUpdateView(APIView):
    authentication_classes = [JWTBearerAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request, entity_id):
        """Entity detail with full usage summary."""
        try:
            entity = Entity.objects.select_related("tenant").get(id=entity_id)
        except Entity.DoesNotExist:
            return Response({"detail": "Entity not found"}, status=status.HTTP_404_NOT_FOUND)

        data = EntityResponseSerializer.serialize(entity)

        # Aggregate stats
        total_documents = Document.objects.filter(tenant=entity.tenant).count()
        total_revenue = (
            DocumentCharge.objects.filter(entity=entity)
            .aggregate(total=Sum("charge_amount"))["total"]
        ) or 0
        active_api_keys = APIKey.objects.filter(tenant=entity.tenant, is_active=True).count()

        data["total_documents"] = total_documents
        data["total_revenue"] = float(total_revenue)
        data["active_api_keys"] = active_api_keys

        return Response(data)

    def patch(self, request, entity_id):
        """Update entity fields."""
        try:
            entity = Entity.objects.get(id=entity_id)
        except Entity.DoesNotExist:
            return Response({"detail": "Entity not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = EntityUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        for field, value in serializer.validated_data.items():
            setattr(entity, field, value)
        entity.save()

        AuditLog.objects.create(
            tenant=entity.tenant,
            actor_user=request.user,
            action="entity_update",
            entity_type="Entity",
            entity_id=entity.id,
            ip=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            metadata_json={"updated_fields": list(serializer.validated_data.keys())},
        )

        return Response(EntityResponseSerializer.serialize(entity))


class EntitySuspendView(APIView):
    authentication_classes = [JWTBearerAuthentication]
    permission_classes = [IsAdminUser]

    def post(self, request, entity_id):
        """Suspend entity and deactivate all API keys."""
        try:
            entity = Entity.objects.get(id=entity_id)
        except Entity.DoesNotExist:
            return Response({"detail": "Entity not found"}, status=status.HTTP_404_NOT_FOUND)

        entity.status = "suspended"
        entity.save()

        # Deactivate all API keys for this entity's tenant
        APIKey.objects.filter(tenant=entity.tenant).update(is_active=False)

        AuditLog.objects.create(
            tenant=entity.tenant,
            actor_user=request.user,
            action="entity_suspend",
            entity_type="Entity",
            entity_id=entity.id,
            ip=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            metadata_json={"entity_name": entity.name},
        )

        return Response({"detail": "Entity suspended", "entity": EntityResponseSerializer.serialize(entity)})


class EntityUsageView(APIView):
    authentication_classes = [JWTBearerAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request, entity_id):
        """Detailed usage report."""
        try:
            entity = Entity.objects.get(id=entity_id)
        except Entity.DoesNotExist:
            return Response({"detail": "Entity not found"}, status=status.HTTP_404_NOT_FOUND)

        period = request.query_params.get("period", "monthly")
        days = int(request.query_params.get("days", 30))
        since = datetime.utcnow() - timedelta(days=days)

        # Daily document counts
        daily_documents = (
            Document.objects.filter(tenant=entity.tenant, created_at__gte=since)
            .extra(select={"day": "DATE(created_at)"})
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )

        # Daily charges
        daily_charges = (
            DocumentCharge.objects.filter(entity=entity, created_at__gte=since)
            .extra(select={"day": "DATE(created_at)"})
            .values("day")
            .annotate(total=Sum("charge_amount"), count=Count("id"))
            .order_by("day")
        )

        # API calls per day
        from api_keys.models import APIKeyUsage

        daily_api_calls = (
            APIKeyUsage.objects.filter(tenant=entity.tenant, created_at__gte=since)
            .extra(select={"day": "DATE(created_at)"})
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )

        return Response({
            "entity_id": entity.id,
            "entity_name": entity.name,
            "period": period,
            "days": days,
            "daily_documents": [
                {"date": str(d["day"]), "count": d["count"]}
                for d in daily_documents
            ],
            "daily_charges": [
                {"date": str(d["day"]), "total": float(d["total"]), "count": d["count"]}
                for d in daily_charges
            ],
            "daily_api_calls": [
                {"date": str(d["day"]), "count": d["count"]}
                for d in daily_api_calls
            ],
        })


class EntityUserCreateView(APIView):
    authentication_classes = [JWTBearerAuthentication]
    permission_classes = [IsAdminUser]

    def post(self, request, entity_id):
        """Create portal user for entity."""
        try:
            entity = Entity.objects.get(id=entity_id)
        except Entity.DoesNotExist:
            return Response({"detail": "Entity not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = EntityUserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Check if email already exists
        if EntityUser.objects.filter(email=data["email"]).exists():
            return Response(
                {"detail": "A user with this email already exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = EntityUser.objects.create(
            entity=entity,
            name=data["name"],
            email=data["email"],
            password_hash=get_password_hash(data["password"]),
        )

        return Response(
            {
                "id": user.id,
                "entity_id": user.entity_id,
                "name": user.name,
                "email": user.email,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            },
            status=status.HTTP_201_CREATED,
        )


class EntityInvoiceListView(APIView):
    authentication_classes = [JWTBearerAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request, entity_id):
        """List invoices for entity."""
        try:
            entity = Entity.objects.get(id=entity_id)
        except Entity.DoesNotExist:
            return Response({"detail": "Entity not found"}, status=status.HTTP_404_NOT_FOUND)

        invoices = Invoice.objects.filter(entity=entity).order_by("-created_at")
        return Response([InvoiceResponseSerializer.serialize(inv) for inv in invoices])


class GenerateInvoiceView(APIView):
    authentication_classes = [JWTBearerAuthentication]
    permission_classes = [IsAdminUser]

    def post(self, request, entity_id):
        """Generate invoice for a period."""
        try:
            entity = Entity.objects.get(id=entity_id)
        except Entity.DoesNotExist:
            return Response({"detail": "Entity not found"}, status=status.HTTP_404_NOT_FOUND)

        period_start_str = request.query_params.get("period_start")
        period_end_str = request.query_params.get("period_end")

        if not period_start_str or not period_end_str:
            return Response(
                {"detail": "period_start and period_end query params required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            period_start = date.fromisoformat(period_start_str)
            period_end = date.fromisoformat(period_end_str)
        except ValueError:
            return Response(
                {"detail": "Invalid date format. Use ISO format (YYYY-MM-DD)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Aggregate charges for the period
        charges = DocumentCharge.objects.filter(
            entity=entity,
            created_at__date__gte=period_start,
            created_at__date__lte=period_end,
        )
        agg = charges.aggregate(
            total_amount=Sum("charge_amount"),
            total_documents=Count("id"),
        )
        total_amount = agg["total_amount"] or 0
        total_documents = agg["total_documents"] or 0

        # Generate invoice number
        seq = Invoice.objects.filter(entity=entity).count() + 1
        invoice_number = f"INV-{entity.id}-{datetime.utcnow().strftime('%Y%m%d')}-{seq}"

        invoice = Invoice.objects.create(
            entity=entity,
            invoice_number=invoice_number,
            period_start=period_start,
            period_end=period_end,
            total_documents=total_documents,
            total_amount=total_amount,
            currency=entity.currency,
            status="draft",
            due_date=period_end + timedelta(days=30),
        )

        # Create line item
        InvoiceLineItem.objects.create(
            invoice=invoice,
            description=f"Document processing ({period_start} to {period_end})",
            quantity=total_documents,
            unit_price=entity.per_document_rate,
            amount=total_amount,
        )

        # Mark charges as invoiced
        charges.update(status="invoiced")

        return Response(InvoiceResponseSerializer.serialize(invoice), status=status.HTTP_201_CREATED)

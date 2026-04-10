"""
Entity self-service portal views.
"""

from datetime import datetime, timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.parsers import FormParser, MultiPartParser, JSONParser
from django.db.models import Sum, Count

from core.security import (
    create_access_token,
    verify_password,
    get_password_hash,
    decode_access_token,
    generate_api_key,
    hash_api_key,
    get_api_key_prefix,
)
from core.permissions import AllowAny

from api_keys.models import APIKey
from documents.models import Document

from entities.models import (
    Entity,
    EntityUser,
    DocumentCharge,
    Invoice,
    WebhookEvent,
)
from entities.serializers import (
    InvoiceResponseSerializer,
    DocumentChargeResponseSerializer,
)


# ---------------------------------------------------------------------------
# Authentication for entity portal users
# ---------------------------------------------------------------------------


class EntityUserAuthentication(BaseAuthentication):
    """Authenticate entity portal users via Bearer JWT with type=entity_user."""

    def authenticate(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            return None

        token = auth_header[7:]
        payload = decode_access_token(token)
        if payload is None:
            raise AuthenticationFailed("Invalid authentication credentials")

        if payload.get("type") != "entity_user":
            raise AuthenticationFailed("Invalid token type")

        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise AuthenticationFailed("Invalid authentication credentials")

        try:
            user_id = int(user_id_str)
        except (ValueError, TypeError):
            raise AuthenticationFailed("Invalid authentication credentials")

        try:
            entity_user = EntityUser.objects.select_related("entity").get(id=user_id)
        except EntityUser.DoesNotExist:
            raise AuthenticationFailed("User not found")

        if not entity_user.is_active:
            raise AuthenticationFailed("Inactive user")

        return (entity_user, token)

    def authenticate_header(self, request):
        return "Bearer"


# ---------------------------------------------------------------------------
# Portal Views
# ---------------------------------------------------------------------------


class PortalLoginView(APIView):
    """Entity user login."""
    authentication_classes = []
    permission_classes = [AllowAny]
    parser_classes = [FormParser, MultiPartParser, JSONParser]

    def post(self, request):
        email = request.data.get("email") or request.data.get("username")
        password = request.data.get("password")

        if not email or not password:
            return Response(
                {"detail": "Email and password are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = EntityUser.objects.select_related("entity").get(email=email)
        except EntityUser.DoesNotExist:
            return Response(
                {"detail": "Invalid email or password"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Response(
                {"detail": "Account is inactive"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not verify_password(password, user.password_hash):
            return Response(
                {"detail": "Invalid email or password"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Update last login
        user.last_login_at = datetime.utcnow()
        EntityUser.objects.filter(id=user.id).update(last_login_at=user.last_login_at)

        # Create JWT
        token = create_access_token(
            data={
                "sub": str(user.id),
                "type": "entity_user",
                "entity_id": user.entity_id,
            }
        )

        return Response({
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "entity_name": user.entity.name,
            },
        })


class PortalDashboardView(APIView):
    """Usage summary for entity portal."""
    authentication_classes = [EntityUserAuthentication]
    permission_classes = []

    def get(self, request):
        entity_user = request.user
        entity = entity_user.entity

        # Charges this month
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        charges_this_month = (
            DocumentCharge.objects.filter(entity=entity, created_at__gte=month_start)
            .aggregate(total=Sum("charge_amount"))["total"]
        ) or 0

        return Response({
            "entity_name": entity.name,
            "subscription_tier": entity.subscription_tier,
            "documents_used": entity.documents_used_this_month,
            "monthly_limit": entity.monthly_document_limit,
            "charges_this_month": float(charges_this_month),
        })


class PortalUsageView(APIView):
    """Usage breakdown for entity portal."""
    authentication_classes = [EntityUserAuthentication]
    permission_classes = []

    def get(self, request):
        entity_user = request.user
        entity = entity_user.entity

        period = request.query_params.get("period", "monthly")
        since = datetime.utcnow() - timedelta(days=30)

        daily_documents = (
            Document.objects.filter(tenant=entity.tenant, created_at__gte=since)
            .extra(select={"day": "DATE(created_at)"})
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )

        return Response({
            "entity_name": entity.name,
            "period": period,
            "daily_documents": [
                {"date": str(d["day"]), "count": d["count"]}
                for d in daily_documents
            ],
        })


class PortalAPIKeyListCreateView(APIView):
    """List and create API keys for entity."""
    authentication_classes = [EntityUserAuthentication]
    permission_classes = []

    def get(self, request):
        """List entity's API keys (without hash)."""
        entity_user = request.user
        entity = entity_user.entity

        keys = APIKey.objects.filter(tenant=entity.tenant).order_by("-created_at")
        results = []
        for key in keys:
            results.append({
                "id": key.id,
                "name": key.name,
                "key_prefix": key.key_prefix,
                "scopes": key.scopes,
                "rate_limit": key.rate_limit,
                "daily_quota": key.daily_quota,
                "is_active": key.is_active,
                "created_at": key.created_at.isoformat() if key.created_at else None,
                "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
                "expires_at": key.expires_at.isoformat() if key.expires_at else None,
            })
        return Response(results)

    def post(self, request):
        """Create new API key."""
        entity_user = request.user
        entity = entity_user.entity

        # Check max_api_keys limit
        current_count = APIKey.objects.filter(tenant=entity.tenant, is_active=True).count()
        if current_count >= entity.max_api_keys:
            return Response(
                {"detail": f"Maximum API key limit ({entity.max_api_keys}) reached"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        name = request.data.get("name", "Portal Key")

        raw_key = generate_api_key()
        key_hash_value = hash_api_key(raw_key)
        key_prefix = get_api_key_prefix(raw_key)

        api_key = APIKey.objects.create(
            tenant=entity.tenant,
            key_hash=key_hash_value,
            key_prefix=key_prefix,
            name=name,
            scopes=request.data.get("scopes", []),
            rate_limit=request.data.get("rate_limit", 60),
            daily_quota=request.data.get("daily_quota", 1000),
        )

        return Response(
            {
                "id": api_key.id,
                "name": api_key.name,
                "key_prefix": api_key.key_prefix,
                "raw_key": raw_key,
                "scopes": api_key.scopes,
                "rate_limit": api_key.rate_limit,
                "daily_quota": api_key.daily_quota,
                "is_active": api_key.is_active,
                "created_at": api_key.created_at.isoformat() if api_key.created_at else None,
            },
            status=status.HTTP_201_CREATED,
        )


class PortalAPIKeyRevokeView(APIView):
    """Revoke an API key."""
    authentication_classes = [EntityUserAuthentication]
    permission_classes = []

    def delete(self, request, key_id):
        entity_user = request.user
        entity = entity_user.entity

        try:
            api_key = APIKey.objects.get(id=key_id, tenant=entity.tenant)
        except APIKey.DoesNotExist:
            return Response({"detail": "API key not found"}, status=status.HTTP_404_NOT_FOUND)

        api_key.is_active = False
        api_key.save()

        return Response({"detail": "API key revoked"})


class PortalDocumentListView(APIView):
    """Document processing history for entity."""
    authentication_classes = [EntityUserAuthentication]
    permission_classes = []

    def get(self, request):
        entity_user = request.user
        entity = entity_user.entity

        documents = (
            Document.objects.filter(tenant=entity.tenant)
            .order_by("-created_at")[:100]
        )

        results = []
        for doc in documents:
            # Get charges for this document
            charges = DocumentCharge.objects.filter(document=doc)
            charge_data = [DocumentChargeResponseSerializer.serialize(c) for c in charges]

            results.append({
                "id": doc.id,
                "filename": doc.filename,
                "mime_type": doc.mime_type,
                "status": doc.status,
                "page_count": doc.page_count,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "charges": charge_data,
            })

        return Response(results)


class PortalBillingView(APIView):
    """Billing and invoice history for entity."""
    authentication_classes = [EntityUserAuthentication]
    permission_classes = []

    def get(self, request):
        entity_user = request.user
        entity = entity_user.entity

        # Invoices
        invoices = Invoice.objects.filter(entity=entity).order_by("-created_at")
        invoice_data = [InvoiceResponseSerializer.serialize(inv) for inv in invoices]

        # Current month charges summary
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current_month_agg = (
            DocumentCharge.objects.filter(entity=entity, created_at__gte=month_start)
            .aggregate(
                total_amount=Sum("charge_amount"),
                total_documents=Count("id"),
            )
        )

        return Response({
            "invoices": invoice_data,
            "current_month": {
                "total_amount": float(current_month_agg["total_amount"] or 0),
                "total_documents": current_month_agg["total_documents"] or 0,
                "period_start": month_start.date().isoformat(),
            },
        })


# ---------------------------------------------------------------------------
# Webhook management views
# ---------------------------------------------------------------------------


class PortalWebhookListView(APIView):
    """GET /api/v1/portal/webhooks -- list webhook events."""
    authentication_classes = [EntityUserAuthentication]
    permission_classes = []

    def get(self, request):
        entity = request.user.entity
        events = WebhookEvent.objects.filter(entity=entity).order_by("-created_at")[:50]
        return Response([
            {
                "id": e.id,
                "event_type": e.event_type,
                "payload": e.payload,
                "status": e.status,
                "attempts": e.attempts,
                "last_attempt_at": e.last_attempt_at.isoformat() if e.last_attempt_at else None,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ])


class PortalWebhookTestView(APIView):
    """POST /api/v1/portal/webhooks/test -- send test webhook."""
    authentication_classes = [EntityUserAuthentication]
    permission_classes = []

    def post(self, request):
        entity = request.user.entity
        from services.webhook_service import webhook_service
        result = webhook_service.send_test_webhook(entity)
        return Response(result)

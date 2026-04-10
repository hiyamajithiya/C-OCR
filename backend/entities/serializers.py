"""
Serializers for entities app.
"""

from rest_framework import serializers


class EntityCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    contact_name = serializers.CharField(max_length=255)
    contact_email = serializers.EmailField()
    contact_phone = serializers.CharField(max_length=20, required=False, default="")
    address = serializers.CharField(required=False, default="")
    gst_number = serializers.CharField(max_length=20, required=False, default="")
    subscription_tier = serializers.ChoiceField(
        choices=["free", "starter", "pro", "enterprise"], default="free"
    )
    per_document_rate = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, default=2.00
    )
    monthly_document_limit = serializers.IntegerField(required=False, default=100)


class EntityUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    contact_name = serializers.CharField(max_length=255, required=False)
    contact_email = serializers.EmailField(required=False)
    contact_phone = serializers.CharField(max_length=20, required=False)
    address = serializers.CharField(required=False)
    gst_number = serializers.CharField(max_length=20, required=False)
    subscription_tier = serializers.ChoiceField(
        choices=["free", "starter", "pro", "enterprise"], required=False
    )
    per_document_rate = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )
    monthly_document_limit = serializers.IntegerField(required=False)
    status = serializers.ChoiceField(
        choices=["active", "suspended", "trial", "inactive"], required=False
    )
    ip_whitelist = serializers.ListField(child=serializers.CharField(), required=False)
    max_api_keys = serializers.IntegerField(required=False)
    webhook_url = serializers.URLField(max_length=500, required=False)
    webhook_secret = serializers.CharField(max_length=255, required=False)
    webhook_enabled = serializers.BooleanField(required=False)
    is_active = serializers.BooleanField(required=False)
    currency = serializers.CharField(max_length=3, required=False)


class EntityResponseSerializer:
    """Serialize an Entity model instance to dict."""

    @staticmethod
    def serialize(entity):
        return {
            "id": entity.id,
            "tenant_id": entity.tenant_id,
            "name": entity.name,
            "contact_name": entity.contact_name,
            "contact_email": entity.contact_email,
            "contact_phone": entity.contact_phone,
            "address": entity.address,
            "gst_number": entity.gst_number,
            "status": entity.status,
            "subscription_tier": entity.subscription_tier,
            "per_document_rate": float(entity.per_document_rate),
            "currency": entity.currency,
            "monthly_document_limit": entity.monthly_document_limit,
            "documents_used_this_month": entity.documents_used_this_month,
            "billing_cycle_start": entity.billing_cycle_start.isoformat() if entity.billing_cycle_start else None,
            "trial_expires_at": entity.trial_expires_at.isoformat() if entity.trial_expires_at else None,
            "ip_whitelist": entity.ip_whitelist,
            "max_api_keys": entity.max_api_keys,
            "webhook_url": entity.webhook_url,
            "webhook_secret": entity.webhook_secret,
            "webhook_enabled": entity.webhook_enabled,
            "is_active": entity.is_active,
            "created_at": entity.created_at.isoformat() if entity.created_at else None,
            "updated_at": entity.updated_at.isoformat() if entity.updated_at else None,
        }


class EntityUserCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8)


class InvoiceResponseSerializer:
    """Serialize an Invoice model instance to dict."""

    @staticmethod
    def serialize(invoice):
        return {
            "id": invoice.id,
            "entity_id": invoice.entity_id,
            "invoice_number": invoice.invoice_number,
            "period_start": invoice.period_start.isoformat() if invoice.period_start else None,
            "period_end": invoice.period_end.isoformat() if invoice.period_end else None,
            "total_documents": invoice.total_documents,
            "total_amount": float(invoice.total_amount),
            "currency": invoice.currency,
            "status": invoice.status,
            "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
            "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None,
            "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
        }


class DocumentChargeResponseSerializer:
    """Serialize a DocumentCharge model instance to dict."""

    @staticmethod
    def serialize(charge):
        return {
            "id": charge.id,
            "entity_id": charge.entity_id,
            "document_id": charge.document_id,
            "charge_amount": float(charge.charge_amount),
            "currency": charge.currency,
            "status": charge.status,
            "created_at": charge.created_at.isoformat() if charge.created_at else None,
        }

"""
Entity, EntityUser, billing, and webhook models for commercial IDP API.
"""

from datetime import datetime
from django.db import models


ENTITY_STATUS_CHOICES = [
    ("active", "Active"),
    ("suspended", "Suspended"),
    ("trial", "Trial"),
    ("inactive", "Inactive"),
]

SUBSCRIPTION_TIER_CHOICES = [
    ("free", "Free"),
    ("starter", "Starter"),
    ("pro", "Professional"),
    ("enterprise", "Enterprise"),
]

CHARGE_STATUS_CHOICES = [
    ("pending", "Pending"),
    ("invoiced", "Invoiced"),
    ("paid", "Paid"),
]

INVOICE_STATUS_CHOICES = [
    ("draft", "Draft"),
    ("sent", "Sent"),
    ("paid", "Paid"),
    ("overdue", "Overdue"),
]

WEBHOOK_STATUS_CHOICES = [
    ("pending", "Pending"),
    ("delivered", "Delivered"),
    ("failed", "Failed"),
]


class Entity(models.Model):
    """Organization/company consuming the IDP API."""

    tenant = models.OneToOneField(
        "accounts.Tenant", on_delete=models.CASCADE, related_name="entity"
    )
    name = models.CharField(max_length=255)
    contact_name = models.CharField(max_length=255)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20, blank=True, default="")
    address = models.TextField(blank=True, default="")
    gst_number = models.CharField(max_length=20, blank=True, default="")

    # Subscription
    status = models.CharField(max_length=20, choices=ENTITY_STATUS_CHOICES, default="trial")
    subscription_tier = models.CharField(max_length=20, choices=SUBSCRIPTION_TIER_CHOICES, default="free")
    per_document_rate = models.DecimalField(max_digits=10, decimal_places=2, default=2.00)
    currency = models.CharField(max_length=3, default="INR")
    monthly_document_limit = models.IntegerField(default=100)
    documents_used_this_month = models.IntegerField(default=0)
    billing_cycle_start = models.DateField(null=True, blank=True)
    trial_expires_at = models.DateTimeField(null=True, blank=True)

    # Security
    ip_whitelist = models.JSONField(default=list, blank=True)
    max_api_keys = models.IntegerField(default=5)

    # Webhooks
    webhook_url = models.URLField(max_length=500, blank=True, default="")
    webhook_secret = models.CharField(max_length=255, blank=True, default="")
    webhook_enabled = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=datetime.utcnow)
    updated_at = models.DateTimeField(default=datetime.utcnow)

    class Meta:
        db_table = "entities"
        verbose_name_plural = "entities"

    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Entity({self.id}, {self.name})"


class EntityUser(models.Model):
    """User account for entity self-service portal."""

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name="users")
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    password_hash = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=datetime.utcnow)

    class Meta:
        db_table = "entity_users"

    def __str__(self):
        return f"EntityUser({self.id}, {self.email})"


class DocumentCharge(models.Model):
    """Per-document charge record."""

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name="charges")
    document = models.ForeignKey(
        "documents.Document", on_delete=models.SET_NULL, null=True, related_name="charges"
    )
    api_key = models.ForeignKey(
        "api_keys.APIKey", on_delete=models.SET_NULL, null=True, related_name="charges"
    )
    charge_amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="INR")
    status = models.CharField(max_length=20, choices=CHARGE_STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(default=datetime.utcnow)

    class Meta:
        db_table = "document_charges"

    def __str__(self):
        return f"DocumentCharge({self.id}, entity={self.entity_id}, amount={self.charge_amount})"


class Invoice(models.Model):
    """Monthly invoice for an entity."""

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name="invoices")
    invoice_number = models.CharField(max_length=50, unique=True)
    period_start = models.DateField()
    period_end = models.DateField()
    total_documents = models.IntegerField(default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="INR")
    status = models.CharField(max_length=20, choices=INVOICE_STATUS_CHOICES, default="draft")
    due_date = models.DateField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=datetime.utcnow)

    class Meta:
        db_table = "invoices"

    def __str__(self):
        return f"Invoice({self.invoice_number}, {self.entity.name})"


class InvoiceLineItem(models.Model):
    """Line item on an invoice."""

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="line_items")
    description = models.CharField(max_length=500)
    quantity = models.IntegerField(default=0)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "invoice_line_items"

    def __str__(self):
        return f"InvoiceLineItem({self.id}, {self.description})"


class WebhookEvent(models.Model):
    """Webhook event to be delivered to an entity."""

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name="webhook_events")
    event_type = models.CharField(max_length=50)
    payload = models.JSONField()
    status = models.CharField(max_length=20, choices=WEBHOOK_STATUS_CHOICES, default="pending")
    attempts = models.IntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=datetime.utcnow)

    class Meta:
        db_table = "webhook_events"

    def __str__(self):
        return f"WebhookEvent({self.id}, {self.event_type})"


class WebhookDelivery(models.Model):
    """Record of a webhook delivery attempt."""

    event = models.ForeignKey(WebhookEvent, on_delete=models.CASCADE, related_name="deliveries")
    response_status = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True, default="")
    duration_ms = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=datetime.utcnow)

    class Meta:
        db_table = "webhook_deliveries"

    def __str__(self):
        return f"WebhookDelivery({self.id}, status={self.response_status})"

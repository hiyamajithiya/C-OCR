"""
Webhook Service — dispatches and delivers webhook events to entities.
"""

import hmac
import hashlib
import json
import time
import uuid
from datetime import datetime

import httpx
import structlog
from django.conf import settings

logger = structlog.get_logger()


class WebhookService:
    """Dispatches webhook events and handles delivery with signature verification."""

    def dispatch_event(self, entity, event_type, payload):
        """
        Create a WebhookEvent if the entity has webhooks enabled.

        Returns the WebhookEvent or None.
        """
        from entities.models import WebhookEvent

        if not entity.webhook_enabled or not entity.webhook_url:
            return None

        event = WebhookEvent.objects.create(
            entity=entity,
            event_type=event_type,
            payload=payload,
            status="pending",
        )

        # Attempt delivery (synchronous for now; use Celery task for async)
        try:
            from workers.webhook_tasks import deliver_webhook_task
            deliver_webhook_task.delay(event.id)
        except Exception:
            # Celery not available — deliver synchronously
            self.deliver_webhook(event.id)

        return event

    def deliver_webhook(self, event_id):
        """
        Deliver a webhook event to the entity's configured URL.

        Returns True on success, False on failure.
        """
        from entities.models import WebhookEvent, WebhookDelivery

        try:
            event = WebhookEvent.objects.select_related("entity").get(id=event_id)
        except WebhookEvent.DoesNotExist:
            logger.error("webhook_event_not_found", event_id=event_id)
            return False

        entity = event.entity

        if not entity.webhook_url:
            logger.warning("webhook_no_url", entity_id=entity.id, event_id=event_id)
            event.status = "failed"
            event.save(update_fields=["status"])
            return False

        # Build payload
        request_id = str(uuid.uuid4())
        envelope = {
            "event_id": event.id,
            "event_type": event.event_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": request_id,
            "data": event.payload,
        }
        payload_bytes = json.dumps(envelope, default=str).encode("utf-8")

        # Generate HMAC signature
        secret = entity.webhook_secret or ""
        signature = hmac.new(
            secret.encode("utf-8"),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": f"sha256={signature}",
            "X-Webhook-Event": event.event_type,
            "X-Request-ID": request_id,
        }

        # Deliver
        event.attempts += 1
        event.last_attempt_at = datetime.utcnow()

        start = time.monotonic()
        response_status = None
        response_body = ""
        success = False

        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(entity.webhook_url, content=payload_bytes, headers=headers)
            response_status = resp.status_code
            response_body = resp.text[:2000]  # truncate large responses
            success = 200 <= resp.status_code < 300
        except Exception as exc:
            response_body = str(exc)[:2000]
            logger.warning(
                "webhook_delivery_error",
                event_id=event_id,
                error=str(exc),
            )

        duration_ms = int((time.monotonic() - start) * 1000)

        # Record delivery attempt
        WebhookDelivery.objects.create(
            event=event,
            response_status=response_status,
            response_body=response_body,
            duration_ms=duration_ms,
        )

        # Update event status
        event.status = "delivered" if success else "failed"
        event.save(update_fields=["status", "attempts", "last_attempt_at"])

        logger.info(
            "webhook_delivered" if success else "webhook_delivery_failed",
            event_id=event_id,
            entity_id=entity.id,
            status_code=response_status,
            duration_ms=duration_ms,
        )

        return success

    def send_test_webhook(self, entity):
        """
        Send a test webhook event to verify the entity's configuration.

        Returns a dict with delivery results.
        """
        from entities.models import WebhookEvent

        if not entity.webhook_url:
            return {
                "success": False,
                "error": "No webhook URL configured",
            }

        test_payload = {
            "message": "This is a test webhook from NexOCR",
            "entity_id": entity.id,
            "entity_name": entity.name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        event = WebhookEvent.objects.create(
            entity=entity,
            event_type="test",
            payload=test_payload,
            status="pending",
        )

        success = self.deliver_webhook(event.id)

        # Reload to get latest delivery info
        event.refresh_from_db()
        delivery = event.deliveries.order_by("-created_at").first()

        return {
            "success": success,
            "event_id": event.id,
            "status": event.status,
            "response_status": delivery.response_status if delivery else None,
            "duration_ms": delivery.duration_ms if delivery else None,
        }


webhook_service = WebhookService()

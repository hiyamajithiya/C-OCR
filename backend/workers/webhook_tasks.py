"""
Celery tasks for asynchronous webhook delivery.
"""

from cocr.celery import app as celery_app


@celery_app.task(bind=True, name="deliver_webhook", max_retries=3)
def deliver_webhook_task(self, event_id):
    """Deliver a webhook event with exponential back-off retries."""
    from services.webhook_service import webhook_service

    try:
        success = webhook_service.deliver_webhook(event_id)
        if not success:
            self.retry(countdown=60 * (2 ** self.request.retries))
    except Exception as exc:
        self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

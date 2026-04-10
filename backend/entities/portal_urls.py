"""
Entity self-service portal URL routes.
"""

from django.urls import path

from entities.portal_views import (
    PortalLoginView,
    PortalDashboardView,
    PortalUsageView,
    PortalAPIKeyListCreateView,
    PortalAPIKeyRevokeView,
    PortalDocumentListView,
    PortalBillingView,
    PortalWebhookListView,
    PortalWebhookTestView,
)

urlpatterns = [
    path("login", PortalLoginView.as_view()),
    path("dashboard", PortalDashboardView.as_view()),
    path("usage", PortalUsageView.as_view()),
    path("api-keys", PortalAPIKeyListCreateView.as_view()),
    path("api-keys/<int:key_id>", PortalAPIKeyRevokeView.as_view()),
    path("documents", PortalDocumentListView.as_view()),
    path("billing", PortalBillingView.as_view()),
    path("webhooks", PortalWebhookListView.as_view()),
    path("webhooks/test", PortalWebhookTestView.as_view()),
]

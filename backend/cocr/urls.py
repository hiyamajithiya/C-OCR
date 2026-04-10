"""
URL configuration for C-OCR project.
Maps all API endpoints to match the original FastAPI routing.
"""

from django.urls import path, include
from django.http import JsonResponse
from django.conf import settings


def root_view(request):
    return JsonResponse({
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "description": settings.DESCRIPTION,
        "docs": "/api/docs",
    })


def health_view(request):
    return JsonResponse({"status": "healthy"})


urlpatterns = [
    path("", root_view),
    path("health", health_view),
    path("api/v1/auth/", include("accounts.urls_auth")),
    path("api/v1/users/", include("accounts.urls_users")),
    path("api/v1/documents/", include("documents.urls")),
    path("api/v1/templates/", include("templates_app.urls")),
    path("api/v1/api-keys/", include("api_keys.urls")),
    path("api/v1/audit-logs/", include("audit.urls")),
    path("api/v1/corrections/", include("corrections.urls")),
    path("api/v1/external/", include("external_api.urls")),
    path("api/v1/entities/", include("entities.urls")),
    path("api/v1/portal/", include("entities.portal_urls")),
    path("api/v1/analytics/", include("api_keys.analytics_urls")),
]

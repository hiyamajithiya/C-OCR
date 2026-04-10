from django.urls import path
from .views import (
    ExternalTemplateListView,
    ExternalDocumentUploadView,
    ExternalDocumentDetailView,
    ExternalExtractionView,
    ExternalExtractView,
    ExternalUsageStatsView,
)

urlpatterns = [
    path("templates", ExternalTemplateListView.as_view()),
    path("documents/upload", ExternalDocumentUploadView.as_view()),
    path("documents/<int:document_id>", ExternalDocumentDetailView.as_view()),
    path("documents/<int:document_id>/extraction", ExternalExtractionView.as_view()),
    path("documents/<int:document_id>/extract", ExternalExtractView.as_view()),
    path("usage/stats", ExternalUsageStatsView.as_view()),
]

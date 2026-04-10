from django.urls import path
from .views import (
    DocumentListCreateView,
    BulkDeleteView,
    DocumentDetailView,
    DocumentResultView,
    DocumentDownloadView,
    PageImageView,
    PageOCRView,
)

urlpatterns = [
    path("", DocumentListCreateView.as_view()),
    path("bulk-delete", BulkDeleteView.as_view()),
    path("<int:document_id>", DocumentDetailView.as_view()),
    path("<int:document_id>/result", DocumentResultView.as_view()),
    path("<int:document_id>/download", DocumentDownloadView.as_view()),
    path("<int:document_id>/pages/<int:page_num>/image", PageImageView.as_view()),
    path("<int:document_id>/pages/<int:page_num>/ocr", PageOCRView.as_view()),
]
